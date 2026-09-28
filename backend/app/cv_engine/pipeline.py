"""
Stage 4-6 -- Chart recognition, structured output, orchestration.

Design note (documented in docs/cv_pipeline.md): a classical OpenCV + OCR pipeline
was chosen over a heavyweight pretrained detector (YOLO/ViT) because financial
chart/report screenshots are largely TEXT- and LINE-based (axis labels, legends,
numeric callouts) rather than natural-scene objects -- classical edge/contour/OCR
methods are more precise here, run instantly on a laptop CPU, and their behaviour
is fully explainable, which matters for an auditable Treasury tool. This mirrors
section 20's own guidance: "If a simpler CV method works better, prefer it."
"""
from __future__ import annotations

import cv2
import numpy as np

from app.cv_engine.edges import detect_chart_region, detect_lines, draw_regions
from app.cv_engine.ocr import (
    OcrWord, detect_asset_class, extract_dates, extract_fx_pair_mentions, extract_numbers,
    extract_tenor_mentions, run_ocr,
)
from app.cv_engine.preprocessing import assess_image_quality, preprocess, to_base64_png

CHART_KEYWORDS = {
    "yield_curve": ["yield", "curve", "tenor", "maturity", "10y", "2y", "5y", "gsec", "g-sec"],
    "fx_chart": ["usd/inr", "usdinr", "eur/inr", "gbp/inr", "eur/usd", "fx", "spot"],
    "report": ["report", "summary", "statement", "balance", "revenue"],
}


def classify_chart_type(raw_text: str) -> str:
    text = raw_text.lower()
    scores = {k: sum(1 for kw in kws if kw in text) for k, kws in CHART_KEYWORDS.items()}
    best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_type if best_score > 0 else "unknown"


def _nearest_number_to(word: OcrWord, numbers: list[tuple[str, OcrWord]], max_dist: int = 250) -> tuple[str, OcrWord] | None:
    """Associate a label (tenor/FX pair) with a nearby numeric OCR token using geometry,
    not just "closest in any direction": in a table or ticker, the value for a row sits on
    the SAME row, to the RIGHT of the label -- searching in any direction lets a wrong
    row's number be closer than the correct one once a page has several rows of numbers.

    Same-row + rightward candidates are preferred; if none exist (e.g. a value stacked
    below a chart-point label rather than a table), fall back to nearest in any direction
    so this still works for non-tabular layouts.
    """
    row_tolerance = max(word.h, 12) * 1.5

    def same_row_and_right(nw: OcrWord) -> bool:
        return abs((nw.y + nw.h / 2) - (word.y + word.h / 2)) <= row_tolerance and nw.x > word.x

    same_row = [(t, nw) for t, nw in numbers if same_row_and_right(nw)]
    pool = same_row if same_row else numbers

    best = None
    best_dist = max_dist
    for text, nw in pool:
        dist = abs(nw.x - word.x) + abs(nw.y - word.y)
        if dist < best_dist:
            best_dist = dist
            best = (text, nw)
    return best


# Heuristic plausibility bound for an extracted yield (%). Indian G-Sec yields have
# historically run roughly 5-9%; 25% is a generous sanity ceiling covering stressed-EM
# scenarios, not a hard business rule -- values outside it are FLAGGED for manual review,
# never silently rejected (section 12: "do not reject unusual values, flag them").
PLAUSIBLE_YIELD_PCT = (0.0, 25.0)


def _check_plausibility(metric: str, unit: str, value: float) -> str | None:
    if metric == "yield" or unit == "pct":
        lo, hi = PLAUSIBLE_YIELD_PCT
        if not (lo <= value <= hi):
            return f"{value}% is outside the plausible yield range ({lo}-{hi}%) -- please verify."
    return None


def _parse_value(text: str) -> tuple[float | None, str]:
    is_pct = text.endswith("%")
    cleaned = text.replace(",", "").replace("%", "")
    try:
        val = float(cleaned)
    except ValueError:
        return None, "unitless"
    return val, ("pct" if is_pct else "level")


def run_pipeline(image_bytes: bytes, original_filename: str) -> dict:
    warnings: list[str] = []
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image -- unsupported or corrupt file")

    # Stage 0: image quality assessment -- on the ORIGINAL upload, before our own resize,
    # so resolution/blur/contrast reflect what the user actually provided.
    image_quality = assess_image_quality(img_bgr)
    # Surfaced separately in the API response as a dedicated "image_quality" block (verdict +
    # reasons + recommendation) rather than folded into the generic warnings list below.

    # Stage 1: preprocessing
    stages_img = preprocess(img_bgr)

    # Stage 2: structural/feature processing (edges, lines, chart region)
    edges = cv2.Canny(stages_img["normalized"], 50, 150)
    lines = detect_lines(edges)
    region = detect_chart_region(stages_img["normalized"])
    regions_overlay = draw_regions(stages_img["original"], [region] if region else [], lines)

    # Stage 3: OCR
    ocr_result = run_ocr(stages_img["normalized"])
    if not ocr_result.available and ocr_result.warning:
        warnings.append(ocr_result.warning)

    # Stage 4: chart recognition
    chart_type = classify_chart_type(ocr_result.raw_text)

    # Stage 5/6: structured field extraction (label mention -> nearest number, by geometry)
    numbers = extract_numbers(ocr_result.words)
    tenor_mentions = extract_tenor_mentions(ocr_result.words)
    fx_mentions = extract_fx_pair_mentions(ocr_result.words)
    asset_class = detect_asset_class(ocr_result.words)
    dates = extract_dates(ocr_result.words)

    # Tag each mention with what kind of label it actually is, so metric/unit come from
    # that -- not from the whole-image chart_type guess -- which keeps a tenor from
    # silently becoming an FX field (or vice versa) if chart_type is misclassified.
    # "G-SEC"/"GSEC" asset-class mentions are deliberately excluded (see detect_asset_class
    # above): that text describes the DOCUMENT, not a row with its own numeric value, so it
    # must never be paired with a nearby number as if it were an instrument.
    instruments = [(t, w, "tenor") for t, w in tenor_mentions] + [(t, w, "fx_pair") for t, w in fx_mentions]

    fields = []
    used_numbers = set()
    for inst_text, inst_word, kind in instruments:
        nearest = _nearest_number_to(inst_word, [n for n in numbers if id(n[1]) not in used_numbers])
        if nearest is None:
            continue
        text, num_word = nearest
        used_numbers.add(id(num_word))
        value, _parsed_unit = _parse_value(text)
        if value is None:
            continue
        confidence = min(inst_word.conf, num_word.conf)
        if kind == "tenor":
            field_metric = "yield"
            # Yields are always a percentage in this domain -- force it rather than relying
            # on OCR having captured a literal '%' glyph next to the number (it often drops
            # thin punctuation), which previously mislabeled the unit as "level".
            field_unit = "pct"
        else:
            field_metric = "spot"
            field_unit = "INR per unit"
        flag_reason = _check_plausibility(field_metric, field_unit, value)
        fields.append({
            "instrument": inst_text,
            "metric": field_metric,
            "value": value,
            "unit": field_unit,
            "confidence": round(confidence, 3),
            "source_region": [num_word.x, num_word.y, num_word.w, num_word.h],
            "flagged": flag_reason is not None,
            "flag_reason": flag_reason,
        })

    # Deduplicate: the same tenor/pair can legitimately appear twice in one image (e.g. a
    # chart axis label plus an accompanying data-table row), each independently pairing
    # with a nearby number -- keep only the highest-confidence occurrence per (instrument,
    # metric). Fixed here at the structured-extraction layer, not hidden in the UI.
    deduped: dict[tuple[str | None, str], dict] = {}
    for f in fields:
        key = (f["instrument"], f["metric"])
        if key not in deduped or f["confidence"] > deduped[key]["confidence"]:
            deduped[key] = f
    fields = list(deduped.values())

    if not fields and numbers:
        # Fall back: surface raw numbers found even without a matched instrument label,
        # flagged with low confidence so the user knows to verify manually.
        for text, num_word in numbers[:5]:
            value, unit = _parse_value(text)
            if value is None:
                continue
            fields.append({
                "instrument": None,
                "metric": "unlabeled_value",
                "value": value,
                "unit": unit,
                "confidence": round(min(num_word.conf, 0.5), 3),
                "source_region": [num_word.x, num_word.y, num_word.w, num_word.h],
                "flagged": False,
                "flag_reason": None,
            })
        warnings.append("Could not confidently associate numeric values with an instrument label -- please verify.")

    if not ocr_result.words:
        warnings.append("No text detected by OCR -- image may be too low-resolution or non-textual.")

    mean_conf = round(float(np.mean([f["confidence"] for f in fields])), 3) if fields else 0.0
    if mean_conf < 0.5 and fields:
        warnings.append("Mean extraction confidence is low (<0.5) -- manual review strongly recommended.")

    return {
        "image_quality": image_quality,
        "stages": {
            "original": to_base64_png(stages_img["original"]),
            "grayscale": to_base64_png(stages_img["grayscale"]),
            "denoised": to_base64_png(stages_img["denoised"]),
            "normalized": to_base64_png(stages_img["normalized"]),
            "thresholded": to_base64_png(stages_img["thresholded"]),
            "edges": to_base64_png(edges),
            "regions": to_base64_png(regions_overlay),
        },
        "chart_type": chart_type,
        "asset_class": asset_class,
        "ocr_text_raw": ocr_result.raw_text,
        "detected_dates": [d[0] for d in dates],
        "fields": fields,
        "mean_confidence": mean_conf,
        "warnings": warnings,
        "ocr_available": ocr_result.available,
    }
