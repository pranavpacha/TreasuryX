"""
Feature 4 -- Market screenshot change detection.

  1. Registration  : SIFT keypoints + Lowe ratio test + RANSAC homography (B -> A frame).
  2. Pixel change  : SSIM map (Gaussian-window structural similarity, implemented here) + absolute difference.
  3. Regions       : thresholded change mask -> morphology -> connected components -> boxes.
  4. Region typing : OCR each changed region in A and B (numbers differ -> value change), coloured-pixel
                     test (chart line change), otherwise a generic visual change.
  5. Values by LABEL: the existing OCR extraction pipeline is run on both screens and compared by
                     instrument label (10Y, USD/INR ...), NOT by position -- so a re-laid-out screen
                     is not mistaken for a market-value change.
  6. Verdict       : layout shift (registration transform) vs value change are reported separately.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.cv_engine import ocr as ocr_mod
from app.cv_engine.preprocessing import to_base64_png

MAX_DIM = 1100


def _fit(img: np.ndarray, max_dim: int = MAX_DIM) -> np.ndarray:
    h, w = img.shape[:2]
    s = min(1.0, max_dim / max(h, w))
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else img


def ssim_map(a: np.ndarray, b: np.ndarray, win: int = 7, sigma: float = 1.5) -> np.ndarray:
    """Structural similarity index map for two same-size 8-bit grayscale images (Wang et al., 2004)."""
    a, b = a.astype(np.float64), b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (win, win), sigma)  # noqa: E731
    mu_a, mu_b = g(a), g(b)
    saa, sbb, sab = g(a * a) - mu_a ** 2, g(b * b) - mu_b ** 2, g(a * b) - mu_a * mu_b
    return ((2 * mu_a * mu_b + c1) * (2 * sab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (saa + sbb + c2))


def register(gray_a: np.ndarray, gray_b: np.ndarray) -> dict:
    """Estimate homography mapping B onto A. Returns H (or None) plus transparent diagnostics."""
    sift = cv2.SIFT_create(nfeatures=3000)
    ka, da = sift.detectAndCompute(gray_a, None)
    kb, db = sift.detectAndCompute(gray_b, None)
    info = {"keypoints_a": len(ka), "keypoints_b": len(kb), "good_matches": 0, "inliers": 0, "inlier_ratio": 0.0, "H": None, "ok": False, "matches": [], "kp": (ka, kb)}
    if da is None or db is None or len(ka) < 8 or len(kb) < 8:
        info["reason"] = "too few keypoints (little texture to register on)"
        return info
    knn = cv2.BFMatcher().knnMatch(db, da, k=2)
    good = [m for m, n in (p for p in knn if len(p) == 2) if m.distance < 0.75 * n.distance]
    info["good_matches"] = len(good)
    if len(good) < 10:
        info["reason"] = f"only {len(good)} confident matches (need >= 10)"
        return info
    src = np.float32([kb[m.trainIdx if False else m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([ka[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if H is None:
        info["reason"] = "RANSAC could not fit a homography"
        return info
    n_in = int(inl.sum())
    info.update(inliers=n_in, inlier_ratio=round(n_in / len(good), 3), H=H, matches=[m for m, k in zip(good, inl.ravel()) if k])
    A = H[:2, :2]
    info["transform"] = {
        "translation_px": [round(float(H[0, 2]), 2), round(float(H[1, 2]), 2)],
        "scale": round(float(np.sqrt(abs(np.linalg.det(A)))), 4),
        "rotation_deg": round(float(np.degrees(np.arctan2(H[1, 0], H[0, 0]))), 3),
        "perspective": round(float(abs(H[2, 0]) + abs(H[2, 1])), 6),
    }
    info["ok"] = n_in >= 12 and info["inlier_ratio"] >= 0.3
    if not info["ok"]:
        info["reason"] = f"registration unreliable ({n_in} inliers, ratio {info['inlier_ratio']})"
    return info


def _numbers(text: str) -> list[float]:
    import re
    out = []
    for t in re.findall(r"-?\d[\d,]*\.?\d*", text):
        try:
            out.append(float(t.replace(",", "")))
        except ValueError:
            pass
    return out


def _ocr_text(crop: np.ndarray) -> str:
    if not ocr_mod._TESSERACT_IMPORT_OK or crop.size == 0:
        return ""
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if g.mean() < 127:
        g = 255 - g
    s = max(1.0, 90.0 / max(1, g.shape[0]))
    g = cv2.copyMakeBorder(cv2.resize(g, None, fx=min(s, 4), fy=min(s, 4), interpolation=cv2.INTER_CUBIC), 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
    try:
        return " ".join(ocr_mod.pytesseract.image_to_string(g, config="--psm 7").split())
    except Exception:  # noqa: BLE001
        return ""


def _extract_fields(img: np.ndarray) -> dict[str, dict]:
    from app.cv_engine.pipeline import run_pipeline
    ok, buf = cv2.imencode(".png", img)
    r = run_pipeline(buf.tobytes(), "compare.png")
    return {f"{f['instrument']}|{f['metric']}": f for f in r["fields"] if f.get("instrument")}


def compare(img_a: np.ndarray, img_b: np.ndarray, with_ocr: bool = True) -> dict:
    a, b = _fit(img_a), _fit(img_b)
    ga, gb = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    ha, wa = ga.shape
    reg = register(ga, gb)
    notes: list[str] = []
    same_size = (a.shape == b.shape)
    layout = {"registered": bool(reg["ok"]), "keypoints_a": reg["keypoints_a"], "keypoints_b": reg["keypoints_b"], "good_matches": reg["good_matches"],
              "inliers": reg["inliers"], "inlier_ratio": reg["inlier_ratio"], "transform": reg.get("transform"), "reason": reg.get("reason"), "size_a": [wa, ha], "size_b": [b.shape[1], b.shape[0]]}
    valid = np.full((ha, wa), 255, np.uint8)
    if reg["ok"]:
        t = reg["transform"]
        shifted = max(abs(t["translation_px"][0]) / wa, abs(t["translation_px"][1]) / ha) > 0.01 or abs(t["scale"] - 1) > 0.015 or abs(t["rotation_deg"]) > 0.5 or t["perspective"] > 1e-4
        b_al = cv2.warpPerspective(b, reg["H"], (wa, ha), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        valid = cv2.warpPerspective(np.full(gb.shape, 255, np.uint8), reg["H"], (wa, ha))
        layout["layout_shift"] = bool(shifted)
        if shifted:
            notes.append("Screen B is shifted/scaled/rotated relative to A; it was warped into A's frame before comparing, so this offset is NOT counted as a content change.")
    else:
        layout["layout_shift"] = not same_size
        if same_size:
            b_al = b
            notes.append(f"Could not register the screens ({reg.get('reason')}); same dimensions, so they were compared directly assuming identical layout.")
        else:
            b_al = cv2.resize(b, (wa, ha), interpolation=cv2.INTER_AREA)
            notes.append(f"Could not register the screens ({reg.get('reason')}) and sizes differ -- B was stretched to A. Region-level differences are unreliable; treat this as a layout/structure change.")
    gba = cv2.cvtColor(b_al, cv2.COLOR_BGR2GRAY)
    ssim = ssim_map(ga, gba)
    ssim_valid = ssim[valid > 0]
    diff = cv2.absdiff(ga, gba)
    changed = ((ssim < 0.75) & (diff > 28) & (valid > 0)).astype(np.uint8) * 255
    changed = cv2.morphologyEx(changed, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)))
    changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(changed, connectivity=8)
    min_area = max(30, int(0.0002 * ha * wa))
    comps = sorted([stats[i] for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_area], key=lambda s: -s[cv2.CC_STAT_AREA])[:25]
    regions = []
    for c in comps:
        x, y, w, h, _ar = [int(v) for v in c]
        pad = 3
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(wa, x + w + pad), min(ha, y + h + pad)
        ca, cb = a[y0:y1, x0:x1], b_al[y0:y1, x0:x1]
        sat_a = float(((cv2.cvtColor(ca, cv2.COLOR_BGR2HSV)[..., 1] > 80)).mean())
        sat_b = float(((cv2.cvtColor(cb, cv2.COLOR_BGR2HSV)[..., 1] > 80)).mean())
        reg_d = {"bbox": [x, y, w, h], "area_share_pct": round(100 * w * h / (ha * wa), 3), "mean_abs_diff": round(float(diff[y:y + h, x:x + w].mean()), 1),
                 "min_ssim": round(float(ssim[y:y + h, x:x + w].min()), 3)}
        text_a = text_b = ""
        if with_ocr and h <= 0.2 * ha and w <= 0.6 * wa:
            text_a, text_b = _ocr_text(ca), _ocr_text(cb)
        na, nb = _numbers(text_a), _numbers(text_b)
        if text_a or text_b:
            reg_d.update(text_a=text_a, text_b=text_b)
        if na and nb and na != nb:
            reg_d["kind"] = "value_change"
        elif (text_a or text_b) and text_a != text_b:
            reg_d["kind"] = "label_change"
        elif max(sat_a, sat_b) > 0.01 and abs(sat_a - sat_b) > 0.003:
            reg_d["kind"] = "chart_line_change"
        else:
            reg_d["kind"] = "visual_change"
        regions.append(reg_d)

    fields_a = fields_b = {}
    value_changes: list[dict] = []
    appeared, disappeared = [], []
    ocr_ok = with_ocr and ocr_mod._TESSERACT_IMPORT_OK
    if ocr_ok:
        fields_a, fields_b = _extract_fields(a), _extract_fields(b)
        for key in sorted(set(fields_a) | set(fields_b)):
            fa, fb = fields_a.get(key), fields_b.get(key)
            inst, metric = key.split("|")
            if fa and fb:
                if abs(fa["value"] - fb["value"]) > 1e-9:
                    d = round(fb["value"] - fa["value"], 6)
                    value_changes.append({"instrument": inst, "metric": metric, "unit": fa["unit"], "value_a": fa["value"], "value_b": fb["value"], "delta": d,
                                          "delta_bps": round(d * 100, 1) if fa["unit"] == "pct" else None,
                                          "confidence": round(min(fa["confidence"], fb["confidence"]), 3), "flagged": bool(fa["flagged"] or fb["flagged"]),
                                          "note": "OCR confidence is a text-recognition score, not a value-accuracy measure."})
            elif fb:
                appeared.append({"instrument": inst, "metric": metric, "value_b": fb["value"]})
            else:
                disappeared.append({"instrument": inst, "metric": metric, "value_a": fa["value"]})
    elif with_ocr:
        notes.append("Tesseract OCR is not available: only pixel/region differences are reported, no label-keyed value comparison.")

    mean_ssim = float(ssim_valid.mean()) if ssim_valid.size else 0.0
    changed_pct = round(100 * float((changed > 0).mean()), 3)
    has_layout = bool(layout.get("layout_shift"))
    has_values = bool(value_changes) or any(r["kind"] == "value_change" for r in regions)
    if not regions and not value_changes and mean_ssim > 0.985 and not has_layout:
        verdict = "identical"
    elif has_layout and has_values:
        verdict = "layout_and_value_change"
    elif has_layout:
        verdict = "layout_change"
    elif has_values:
        verdict = "value_change"
    elif regions:
        verdict = "visual_change"
    else:
        verdict = "near_identical"

    overlay, heat = b_al.copy(), cv2.applyColorMap(diff, cv2.COLORMAP_INFERNO)
    colors = {"value_change": (0, 0, 255), "label_change": (0, 165, 255), "chart_line_change": (255, 0, 255), "visual_change": (0, 200, 200)}
    for r in regions:
        x, y, w, h = r["bbox"]
        cv2.rectangle(overlay, (x, y), (x + w, y + h), colors[r["kind"]], 2)
    ssim_vis = cv2.applyColorMap(np.clip((1 - ssim) * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    images = {"screen_a": to_base64_png(a), "screen_b_aligned": to_base64_png(b_al), "changes_overlay": to_base64_png(overlay), "abs_difference": to_base64_png(heat), "ssim_dissimilarity": to_base64_png(ssim_vis)}
    if reg["matches"]:
        ka, kb = reg["kp"]
        images["sift_matches"] = to_base64_png(cv2.drawMatches(b, kb, a, ka, sorted(reg["matches"], key=lambda m: m.distance)[:40], None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS))
    return {"verdict": verdict, "mean_ssim": round(mean_ssim, 4), "changed_pixels_pct": changed_pct, "layout": layout, "regions": regions, "value_changes": value_changes,
            "instruments_appeared": appeared, "instruments_disappeared": disappeared, "ocr_available": bool(ocr_ok), "notes": notes, "images": images,
            "interpretation": ("Differences are reported as VISUAL/OCR changes. A numeric difference is only a value change if the same instrument label is read on both screens; "
                               "a change in layout alone does not alter any market value.")}
