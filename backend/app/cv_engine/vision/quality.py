"""
Feature 5 -- Image quality analyzer. Every number is computed from the pixels; thresholds are
heuristics (documented below), so "poor" means "likely to hurt OCR/extraction", not a standard.

Measures: resolution, blur (variance of Laplacian), noise (Immerkaer fast sigma estimate),
contrast (std + percentile range), skew (projection-profile deskew search), 90-degree rotation
(row-vs-column profile variance), JPEG blocking (8x8 boundary vs interior gradient ratio),
uneven illumination (low-frequency background spread), text readability (connected-component
character height + optional Tesseract confidence).
"""
from __future__ import annotations

import cv2
import numpy as np

from app.cv_engine.preprocessing import to_base64_png

# (warn, poor) thresholds. For "higher is worse" metrics warn<poor; for "lower is worse" warn>poor.
T = {
    "min_side_px": (480, 240), "blur_laplacian_var": (120.0, 40.0), "noise_sigma": (4.0, 9.0), "contrast_std": (45.0, 25.0),
    "skew_deg": (0.8, 2.5), "blockiness": (1.12, 1.3), "illumination_spread": (0.12, 0.25), "char_height_px": (11, 7),
}


def _status(name: str, v: float) -> str:
    warn, poor = T[name]
    if warn < poor:   # higher is worse
        return "poor" if v >= poor else "warn" if v >= warn else "ok"
    return "poor" if v <= poor else "warn" if v <= warn else "ok"


def _gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def estimate_noise_sigma(gray: np.ndarray) -> float:
    """Immerkaer (1996) fast noise variance estimation: response to a Laplacian-difference mask."""
    h, w = gray.shape
    if h < 3 or w < 3:
        return 0.0
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float64)
    conv = cv2.filter2D(gray.astype(np.float64), -1, k)[1:-1, 1:-1]
    return float(np.sqrt(np.pi / 2) / (6.0 * (w - 2) * (h - 2)) * np.abs(conv).sum())


def _binary_ink(gray: np.ndarray) -> np.ndarray:
    """Foreground = the minority luminance class (works for dark-on-light AND light-on-dark screens)."""
    _, b = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return (255 - b) if (b > 0).mean() > 0.5 else b


def estimate_skew(gray: np.ndarray, max_angle: float = 12.0, step: float = 0.25) -> float:
    """Projection-profile search: the rotation that makes row sums most 'peaky' is the deskew angle."""
    scale = 500.0 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    ink = _binary_ink(small)
    if ink.sum() < 200:
        return 0.0
    h, w = ink.shape
    best, best_ang = -1.0, 0.0
    for ang in np.arange(-max_angle, max_angle + step, step):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        prof = cv2.warpAffine(ink, m, (w, h), flags=cv2.INTER_NEAREST).sum(axis=1).astype(np.float64)
        score = float(np.var(np.diff(prof)))
        if score > best:
            best, best_ang = score, float(ang)
    return -best_ang   # angle the content is rotated BY (deskew = rotate back by this)


def detect_rotation_90(gray: np.ndarray) -> bool:
    scale = 400.0 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    ink = _binary_ink(small).astype(np.float64)
    if ink.sum() < 200:
        return False
    return float(np.var(np.diff(ink.sum(axis=0)))) > 2.5 * float(np.var(np.diff(ink.sum(axis=1))))


def blockiness(gray: np.ndarray) -> float:
    """JPEG 8x8 blocking: mean |horizontal gradient| on block boundaries / on interior columns."""
    g = gray.astype(np.float32)
    if g.shape[1] < 32:
        return 1.0
    dx = np.abs(np.diff(g, axis=1)).mean(axis=0)
    cols = np.arange(dx.size)
    on, off = dx[cols % 8 == 7], dx[cols % 8 != 7]
    return float(on.mean() / max(off.mean(), 1e-6))


def illumination_spread(gray: np.ndarray) -> float:
    small = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    bg = cv2.GaussianBlur(cv2.morphologyEx(small, cv2.MORPH_CLOSE if small.mean() > 127 else cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)), (0, 0), 3)
    return float((np.percentile(bg, 95) - np.percentile(bg, 5)) / max(1.0, bg.mean()))


def char_height(gray: np.ndarray) -> float | None:
    ink = _binary_ink(gray)
    n, _, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    hs = [s[cv2.CC_STAT_HEIGHT] for s in stats[1:] if 3 <= s[cv2.CC_STAT_HEIGHT] <= 60 and 2 <= s[cv2.CC_STAT_WIDTH] <= 60 and s[cv2.CC_STAT_AREA] >= 6]
    return float(np.median(hs)) if len(hs) >= 8 else None


def ocr_readability(gray: np.ndarray) -> dict | None:
    from app.cv_engine.ocr import run_ocr
    res = run_ocr(gray if max(gray.shape) <= 1400 else cv2.resize(gray, None, fx=1400 / max(gray.shape), fy=1400 / max(gray.shape)))
    if not res.available:
        return None
    if not res.words:
        return {"words": 0, "mean_word_confidence": 0.0, "low_confidence_share": 1.0}
    c = np.array([w.conf for w in res.words])
    return {"words": int(len(c)), "mean_word_confidence": round(float(c.mean()), 3), "low_confidence_share": round(float((c < 0.6).mean()), 3)}


def measure(img: np.ndarray, with_ocr: bool = False) -> dict:
    gray = _gray(img)
    h, w = gray.shape
    ch = char_height(gray)
    m = {
        "width": w, "height": h, "megapixels": round(w * h / 1e6, 3), "min_side_px": int(min(h, w)),
        "blur_laplacian_var": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
        "noise_sigma": round(estimate_noise_sigma(gray), 2),
        "contrast_std": round(float(gray.std()), 2),
        "contrast_p1_p99_range": int(np.percentile(gray, 99) - np.percentile(gray, 1)),
        "skew_deg": round(estimate_skew(gray), 2), "rotated_90": bool(detect_rotation_90(gray)),
        "blockiness": round(blockiness(gray), 3), "illumination_spread": round(illumination_spread(gray), 3),
        "char_height_px": None if ch is None else round(ch, 1),
    }
    if with_ocr:
        m["ocr"] = ocr_readability(gray)
    return m


def assess(img: np.ndarray, with_ocr: bool = False) -> dict:
    """Measurements + per-metric status + recommended preprocessing operations."""
    m = measure(img, with_ocr)
    # Blur/noise interact: a noisy image has inflated Laplacian variance, so blur is only judged on low-noise images.
    checks = {
        "resolution": ("min_side_px", _status("min_side_px", m["min_side_px"]), f"smaller side {m['min_side_px']}px"),
        "blur": ("blur_laplacian_var", _status("blur_laplacian_var", m["blur_laplacian_var"]) if m["noise_sigma"] < 9 else "unknown",
                 f"Laplacian variance {m['blur_laplacian_var']}"),
        "noise": ("noise_sigma", _status("noise_sigma", m["noise_sigma"]), f"sigma ~{m['noise_sigma']}"),
        "contrast": ("contrast_std", _status("contrast_std", m["contrast_std"]), f"std {m['contrast_std']}"),
        "skew": ("skew_deg", _status("skew_deg", abs(m["skew_deg"])), f"{m['skew_deg']} deg"),
        "compression": ("blockiness", _status("blockiness", m["blockiness"]), f"8x8 block ratio {m['blockiness']}"),
        "illumination": ("illumination_spread", _status("illumination_spread", m["illumination_spread"]), f"background spread {m['illumination_spread']}"),
    }
    if m["char_height_px"] is not None:
        checks["text_size"] = ("char_height_px", _status("char_height_px", m["char_height_px"]), f"median character height {m['char_height_px']}px")
    if m["rotated_90"]:
        checks["rotation"] = ("rotated_90", "poor", "text appears rotated by 90 degrees")
    items = [{"check": k, "metric": v[0], "status": v[1], "detail": v[2]} for k, v in checks.items()]
    sub = {"ok": 1.0, "warn": 0.5, "unknown": 0.75, "poor": 0.0}
    score = round(100 * float(np.mean([sub[i["status"]] for i in items])), 1)
    recs = []
    st = {i["check"]: i["status"] for i in items}
    if st.get("rotation") == "poor":
        recs.append({"op": "rotate90", "why": "text runs vertically", "params": {}})
    if st["skew"] != "ok":
        recs.append({"op": "deskew", "why": f"content tilted ~{m['skew_deg']} deg", "params": {"angle": m["skew_deg"]}})
    if st["resolution"] != "ok" or st.get("text_size", "ok") != "ok":
        recs.append({"op": "upscale", "why": "small image/text", "params": {"factor": 2 if m["min_side_px"] < 480 or (m["char_height_px"] or 99) < 11 else 1}})
    if st["noise"] != "ok":
        recs.append({"op": "denoise", "why": "sensor/compression noise", "params": {"h": 8 if st["noise"] == "warn" else 14}})
    if st["compression"] != "ok":
        recs.append({"op": "deblock", "why": "JPEG blocking", "params": {}})
    if st["illumination"] != "ok":
        recs.append({"op": "flatten_illumination", "why": "uneven background", "params": {}})
    if st["contrast"] != "ok":
        recs.append({"op": "clahe", "why": "low contrast", "params": {"clip": 2.5}})
    if st["blur"] in ("warn", "poor"):
        recs.append({"op": "sharpen", "why": "soft edges", "params": {"amount": 0.8}})
    verdict = "poor" if any(i["status"] == "poor" for i in items) else "fair" if any(i["status"] == "warn" for i in items) else "good"
    return {"measurements": m, "checks": items, "quality_score": score, "verdict": verdict, "recommendations": recs,
            "score_note": "quality_score = mean of per-check sub-scores (ok=1, warn=0.5, unknown=0.75, poor=0); thresholds are heuristics, not a standard."}


def apply_operations(img: np.ndarray, recs: list[dict]) -> tuple[np.ndarray, list[str]]:
    out, applied = img.copy(), []
    order = ["rotate90", "deskew", "upscale", "deblock", "denoise", "flatten_illumination", "clahe", "sharpen"]
    for op in sorted(recs, key=lambda r: order.index(r["op"]) if r["op"] in order else 99):
        name, p = op["op"], op.get("params", {})
        if name == "rotate90":
            out = cv2.rotate(out, cv2.ROTATE_90_CLOCKWISE)
        elif name == "deskew" and abs(p.get("angle", 0)) > 0.2:
            h, w = out.shape[:2]
            mat = cv2.getRotationMatrix2D((w / 2, h / 2), -p["angle"], 1.0)
            bg = tuple(int(v) for v in np.median(out.reshape(-1, out.shape[-1] if out.ndim == 3 else 1), axis=0)) if out.ndim == 3 else int(np.median(out))
            out = cv2.warpAffine(out, mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=bg)
        elif name == "upscale" and p.get("factor", 1) > 1:
            out = cv2.resize(out, None, fx=p["factor"], fy=p["factor"], interpolation=cv2.INTER_CUBIC)
        elif name == "deblock":
            out = cv2.bilateralFilter(out, 5, 30, 5)
        elif name == "denoise":
            out = cv2.fastNlMeansDenoisingColored(out, None, p.get("h", 8), p.get("h", 8), 5, 15) if out.ndim == 3 else cv2.fastNlMeansDenoising(out, None, p.get("h", 8))
        elif name == "flatten_illumination":
            g = out.astype(np.float32)
            bg = cv2.GaussianBlur(g, (0, 0), max(out.shape[:2]) / 12)
            out = np.clip(g / np.maximum(bg, 1.0) * float(bg.mean()), 0, 255).astype(np.uint8)
        elif name == "clahe":
            lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB) if out.ndim == 3 else None
            cl = cv2.createCLAHE(clipLimit=p.get("clip", 2.5), tileGridSize=(8, 8))
            if lab is not None:
                lab[..., 0] = cl.apply(lab[..., 0])
                out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                out = cl.apply(out)
        elif name == "sharpen":
            blur = cv2.GaussianBlur(out, (0, 0), 1.2)
            out = cv2.addWeighted(out, 1 + p.get("amount", 0.8), blur, -p.get("amount", 0.8), 0)
        else:
            continue
        applied.append(name)
    return out, applied


def analyze(img: np.ndarray, with_ocr: bool = True) -> dict:
    before = assess(img, with_ocr)
    enhanced, applied = apply_operations(img, before["recommendations"])
    after = assess(enhanced, with_ocr) if applied else before
    cmp_keys = ["blur_laplacian_var", "noise_sigma", "contrast_std", "skew_deg", "blockiness", "illumination_spread", "min_side_px", "char_height_px"]
    return {"before": before, "after": after, "applied_operations": applied,
            "comparison": [{"metric": k, "before": before["measurements"].get(k), "after": after["measurements"].get(k)} for k in cmp_keys],
            "images": {"before": to_base64_png(img), "after": to_base64_png(enhanced)},
            "caveat": "Enhancement can improve OCR legibility but cannot recover information that was never captured; after-metrics are re-measured, not assumed."}
