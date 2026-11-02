"""
Feature 1 -- Chart digitization: screenshot of a line / yield-curve chart -> approximate numeric series.

Pipeline (all classical CV; nothing is learned):
  1. Axis + plot-region detection   : |I - background| threshold -> long-line morphology (open with
                                      1xN / Nx1 kernels) -> left axis, bottom axis, plot rectangle.
  2. Curve segmentation             : HSV saturation threshold (curves are coloured, text/grid are grey),
                                      circular hue clustering -> one mask per series; legend swatches and
                                      specks rejected by connected-component size.
  3. Marker detection               : morphological opening with a disc wider than the line.
  4. Pixel->value calibration       : OCR the tick labels (Tesseract), snap to tick marks, least-squares
                                      linear fit; decimal-point loss repaired ONLY if a global decimal shift
                                      makes the labels linear. Manual calibration overrides OCR.
  5. Uncertainty                    : localisation + calibration residual + 1px edge error in quadrature.

Pixel-derived values are APPROXIMATE. Nothing is returned as a value unless a calibration exists;
otherwise only normalised plot coordinates are returned and the result says so.
"""
from __future__ import annotations

import re

import cv2
import numpy as np

from app.cv_engine import ocr as ocr_mod
from app.cv_engine.preprocessing import to_base64_png

NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
TENOR_RE = re.compile(r"^(\d{1,2})\s?([MY])$", re.IGNORECASE)


# ------------------------------------------------------------------ helpers
def _bg_level(gray: np.ndarray) -> int:
    border = np.concatenate([gray[0], gray[-1], gray[:, 0], gray[:, -1]])
    return int(np.median(border))


def _runs(mask1d: np.ndarray) -> list[tuple[int, int]]:
    idx = np.flatnonzero(mask1d)
    if idx.size == 0:
        return []
    splits = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[splits + 1]]
    ends = np.r_[idx[splits], idx[-1]]
    return list(zip(starts.tolist(), ends.tolist()))


def find_axes(gray: np.ndarray) -> dict:
    h, w = gray.shape
    bg = _bg_level(gray)
    strong = (cv2.absdiff(gray, np.full_like(gray, bg)) >= 45).astype(np.uint8) * 255
    hor = cv2.morphologyEx(strong, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 5), 1)))
    ver = cv2.morphologyEx(strong, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(15, h // 5))))
    out = {"found": False, "background_gray": bg}
    # left axis: leftmost sufficiently tall vertical-line group in the left half
    col_len = (ver > 0).sum(axis=0)
    left = [r for r in _runs(col_len >= 0.35 * h) if r[0] < 0.5 * w]
    # bottom axis: lowest sufficiently wide horizontal-line group
    row_len = (hor > 0).sum(axis=1)
    bottom = [r for r in _runs(row_len >= 0.35 * w) if r[1] > 0.4 * h]
    if left and bottom:
        lx0, lx1 = left[0]
        by0, by1 = bottom[-1]
        x_axis_x = (lx0 + lx1) / 2.0
        y_axis_y = (by0 + by1) / 2.0
        ys = np.flatnonzero(ver[:, lx0: lx1 + 1].any(axis=1))
        xs = np.flatnonzero(hor[by0: by1 + 1].any(axis=0))
        top = float(ys.min()) if ys.size else 0.15 * h
        right = float(xs.max()) if xs.size else float(w - 1)
        out.update(found=True, left_axis_x=x_axis_x, bottom_axis_y=y_axis_y, plot_rect=[x_axis_x, top, right, y_axis_y],
                   axis_thickness_px=int(max(lx1 - lx0 + 1, by1 - by0 + 1)))
        return out
    # fallback: faint gridlines
    faint = (cv2.absdiff(gray, np.full_like(gray, bg)) >= 14).astype(np.uint8) * 255
    gh = cv2.morphologyEx(faint, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 3), 1)))
    rows = _runs((gh > 0).sum(axis=1) >= 0.3 * w)
    if len(rows) >= 2:
        cols = np.flatnonzero(gh[rows[0][0]: rows[-1][1] + 1].any(axis=0))
        out.update(found=False, fallback="gridlines", plot_rect=[float(cols.min()), float(rows[0][0]), float(cols.max()), float(rows[-1][1])])
        return out
    out.update(found=False, fallback="image-margins", plot_rect=[0.1 * w, 0.1 * h, 0.95 * w, 0.9 * h])
    return out


def _hue_series_masks(img: np.ndarray, rect: tuple[int, int, int, int]) -> tuple[list[dict], np.ndarray]:
    x0, y0, x1, y1 = rect
    roi = img[y0:y1, x0:x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    sat = (hsv[..., 1] >= 70) & (hsv[..., 2] >= 70)
    series = []
    remaining = sat.copy()
    hue = hsv[..., 0].astype(np.int32)
    for _ in range(4):
        px = hue[remaining]
        if px.size < 12:
            break
        hist = np.bincount(px, minlength=180).astype(np.float64)
        smooth = sum(np.roll(hist, s) for s in range(-6, 7))
        peak = int(smooth.argmax())
        d = np.abs(hue - peak)
        d = np.minimum(d, 180 - d)
        m = remaining & (d <= 12)
        if m.sum() < 12:
            break
        series.append({"hue": peak, "mask": m})
        remaining &= ~m
    return series, sat


def _clean_series_mask(mask: np.ndarray, plot_w: int, plot_h: int) -> np.ndarray:
    m = mask.astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    for k in range(1, n):
        w, h, a = stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT], stats[k, cv2.CC_STAT_AREA]
        if a < 6:
            continue
        if w < 0.05 * plot_w and h < 0.07 * plot_h:      # legend swatch / speck
            continue
        keep[lab == k] = 1
    return keep


def _columns(mask: np.ndarray) -> dict:
    h, w = mask.shape
    ys_c = np.full(w, np.nan)
    thick = np.zeros(w)
    span = np.zeros(w)
    for x in range(w):
        ys = np.flatnonzero(mask[:, x])
        if ys.size:
            ys_c[x] = float(np.median(ys))
            thick[x] = ys.size
            span[x] = ys.max() - ys.min() + 1
    return {"y": ys_c, "thick": thick, "span": span}


def _find_markers(mask: np.ndarray, thickness: float) -> list[tuple[float, float, float]]:
    k = int(max(5, round(1.5 * thickness))) | 1
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, _, stats, cents = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 0.4 * np.pi * (k / 2) ** 2:
            out.append((float(cents[i][0]), float(cents[i][1]), float(stats[i, cv2.CC_STAT_AREA])))
    return sorted(out)


# ------------------------------------------------------------------ OCR of tick labels
def _ocr_words(img: np.ndarray, region: tuple[int, int, int, int], scale: float = 3.0, whitelist: str | None = None, psm: int = 11) -> list[dict]:
    if not ocr_mod._TESSERACT_IMPORT_OK:
        return []
    x0, y0, x1, y1 = [int(v) for v in region]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.shape[1], x1), min(img.shape[0], y1)
    if x1 - x0 < 6 or y1 - y0 < 6:
        return []
    crop = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img[y0:y1, x0:x1]
    if crop.mean() < 127:
        crop = 255 - crop
    crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    crop = cv2.copyMakeBorder(crop, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
    cfg = f"--psm {psm}" + (f" -c tessedit_char_whitelist={whitelist}" if whitelist else "")
    try:
        d = ocr_mod.pytesseract.image_to_data(crop, output_type=ocr_mod.Output.DICT, config=cfg)
    except Exception:  # noqa: BLE001 -- tesseract binary missing
        return []
    words = []
    for i, t in enumerate(d["text"]):
        t = (t or "").strip()
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            continue
        if not t or conf < 0:
            continue
        lx, ly, lw, lh = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        words.append({"text": t, "conf": conf / 100.0, "x": x0 + (lx - 12) / scale, "y": y0 + (ly - 12) / scale, "w": lw / scale, "h": lh / scale,
                      "cx": x0 + (lx - 12 + lw / 2) / scale, "cy": y0 + (ly - 12 + lh / 2) / scale})
    return words


def _tick_rows(gray: np.ndarray, axis_x: float, plot_top: float, plot_bot: float, bg: int) -> list[float]:
    """Row centres of the short tick marks just left of the y axis (sub-pixel snap targets)."""
    xa, xb = int(axis_x) - 7, int(axis_x) - 2
    if xa < 0:
        return []
    strip = cv2.absdiff(gray[:, xa:xb], bg)[:, :] >= 45
    rows = strip.sum(axis=1) >= max(2, (xb - xa) // 2)
    return [(a + b) / 2.0 for a, b in _runs(rows) if plot_top - 4 <= (a + b) / 2 <= plot_bot + 4]


def _fit_linear(px: np.ndarray, vals: np.ndarray) -> dict:
    a, b = np.polyfit(px, vals, 1)
    res = vals - (a * px + b)
    return {"slope": float(a), "intercept": float(b), "rms_value_error": float(np.sqrt(np.mean(res ** 2))),
            "rms_px_error": float(np.sqrt(np.mean(res ** 2)) / max(abs(a), 1e-12)), "n_ticks": int(len(px))}


def calibrate_y(img: np.ndarray, gray: np.ndarray, plot: list[float], axis_x: float, manual: dict | None) -> dict:
    top, bot = plot[1], plot[3]
    if manual and manual.get("y_top_value") is not None and manual.get("y_bottom_value") is not None:
        a = (manual["y_top_value"] - manual["y_bottom_value"]) / (top - bot)
        return {"source": "manual", "slope": a, "intercept": manual["y_bottom_value"] - a * bot, "n_ticks": 2, "rms_value_error": 0.0, "rms_px_error": 0.0,
                "ticks": [{"value": manual["y_bottom_value"], "y_px": bot}, {"value": manual["y_top_value"], "y_px": top}],
                "notes": ["Manual calibration: plot top/bottom edges assumed to sit exactly at the supplied values."]}
    words = _ocr_words(img, (max(0, axis_x - 0.2 * img.shape[1]), top - 14, axis_x - 3, bot + 14), whitelist="0123456789.-%")
    cand = [w for w in words if NUM_RE.match(w["text"].replace("%", "").replace(",", ""))]
    if len(cand) < 2:
        return {"source": None, "reason": "fewer than 2 numeric y-axis tick labels were read" + ("" if ocr_mod._TESSERACT_IMPORT_OK else " (Tesseract unavailable)"), "n_ticks": len(cand)}
    snaps = _tick_rows(gray, axis_x, top, bot, _bg_level(gray))
    ypx = np.array([min(snaps, key=lambda s: abs(s - w["cy"])) if snaps and min(abs(s - w["cy"]) for s in snaps) <= 6 else w["cy"] for w in cand])
    raw = np.array([float(w["text"].replace("%", "").replace(",", "")) for w in cand])
    notes: list[str] = []
    best = None
    for shift in range(0, 4):
        vals = raw / (10 ** shift)
        if len(vals) >= 3:
            fit = _fit_linear(ypx, vals)
            score = fit["rms_px_error"]
        else:
            fit, score = _fit_linear(ypx, vals) if len(vals) == 2 else None, 0.0 if shift == 0 else 1e9
        if fit and (best is None or score < best[0] - 1e-9):
            best = (score, shift, fit, vals)
    if best is None:
        return {"source": None, "reason": "could not fit tick labels", "n_ticks": len(cand)}
    _, shift, fit, vals = best
    # robust: drop outliers > 3 MAD (px) and refit once
    if len(vals) >= 4:
        res = np.abs(vals - (fit["slope"] * ypx + fit["intercept"])) / max(abs(fit["slope"]), 1e-12)
        keep = res <= max(2.0, 3 * 1.4826 * np.median(res))
        if keep.sum() >= 3 and keep.sum() < len(vals):
            ypx, vals = ypx[keep], vals[keep]
            fit = _fit_linear(ypx, vals)
            notes.append(f"{int((~keep).sum())} tick label(s) rejected as outliers.")
    if shift:
        notes.append(f"OCR dropped decimal points; labels divided by 10^{shift} because that makes the tick labels exactly linear in pixel position.")
    if len(vals) == 2:
        notes.append("Only 2 tick labels read: linearity cannot be validated (decimal-point loss would go unnoticed).")
    fit.update(source="ocr", ticks=[{"value": float(v), "y_px": float(p)} for v, p in zip(vals, ypx)], notes=notes, decimal_shift=shift)
    return fit


def calibrate_x(img: np.ndarray, plot: list[float], manual: dict | None) -> dict:
    left, right, bot = plot[0], plot[2], plot[3]
    words = _ocr_words(img, (left - 40, bot + 3, right + 40, bot + 34), whitelist=None)
    labels = [{"text": w["text"], "cx": w["cx"], "conf": w["conf"]} for w in words]
    tenors = [l for l in labels if TENOR_RE.match(l["text"])]
    out: dict = {"labels": labels}
    if len(tenors) >= 3:
        out.update(kind="tenor", tenors=[{"label": TENOR_RE.match(t["text"]).group(1) + TENOR_RE.match(t["text"]).group(2).upper(), "cx": t["cx"]} for t in sorted(tenors, key=lambda t: t["cx"])])
        return out
    if manual and manual.get("x_left_value") is not None and manual.get("x_right_value") is not None:
        out.update(kind="numeric", source="manual", slope=(manual["x_right_value"] - manual["x_left_value"]) / (right - left), intercept=manual["x_left_value"] - (manual["x_right_value"] - manual["x_left_value"]) / (right - left) * left)
        return out
    nums = [l for l in labels if NUM_RE.match(l["text"])]
    if len(nums) >= 3:
        fit = _fit_linear(np.array([n["cx"] for n in nums]), np.array([float(n["text"]) for n in nums]))
        if fit["rms_px_error"] < 3:
            out.update(kind="numeric", source="ocr", **fit)
            return out
    out["kind"] = "labels" if labels else "none"
    return out


def _fill_missing_tenors(img: np.ndarray, pts: list[dict], rect: tuple, axis_y: float) -> None:
    """A marker whose x-label was missed by the whole-axis OCR gets a second, tighter OCR attempt on just
    the strip below it (single-word mode). Never guesses: no readable tenor -> the marker stays unlabelled."""
    if len(pts) < 3:
        return
    xs = sorted(p["x_px"] for p in pts)
    spacing = float(np.median(np.diff(xs)))
    for p in pts:
        if "tenor" in p:
            continue
        words = _ocr_words(img, (p["x_px"] - 0.45 * spacing, axis_y + 3, p["x_px"] + 0.45 * spacing, axis_y + 34), scale=3.0, whitelist="0123456789MY", psm=7)
        for w in words:
            m = TENOR_RE.match(w["text"].replace(" ", ""))
            if m:
                p["tenor"] = f"{m.group(1)}{m.group(2).upper()}"
                p["tenor_source"] = "per-marker OCR"
                break
    seen: dict[str, dict] = {}
    for p in pts:
        t = p.get("tenor")
        if t and t in seen:   # duplicate tenor: keep the marker nearest its label, drop the other's label
            loser = p if abs(p["x_px"] - p["x_px"]) >= 0 and p.get("tenor_source") else seen[t]
            loser.pop("tenor", None)
        elif t:
            seen[t] = p


# ------------------------------------------------------------------ main entry
def digitize(img: np.ndarray, calibration: dict | None = None, max_points: int = 120) -> dict:
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    limitations = ["Values are reconstructed from pixel positions and are approximate; they are not the source data.",
                   "Accuracy is bounded by image resolution: one pixel corresponds to the 'value_per_pixel' shown below."]
    axes = find_axes(gray)
    px0, py0, px1, py1 = axes["plot_rect"]
    pad = max(2, int(0.008 * w))
    rect = (int(px0) + pad, int(py0) + pad, int(px1) - 1, int(py1) - pad)
    result: dict = {"image_size": [w, h], "plot_rect": [round(v, 1) for v in axes["plot_rect"]], "axes_found": bool(axes["found"]),
                    "theme": "dark" if axes["background_gray"] < 110 else "light", "series": [], "limitations": limitations,
                    "ocr_available": bool(ocr_mod._TESSERACT_IMPORT_OK)}
    if not axes["found"]:
        limitations.append(f"Axis lines were not found (fallback: {axes.get('fallback')}); the plot region is a guess, so accuracy is much lower.")
    if rect[2] - rect[0] < 40 or rect[3] - rect[1] < 30:
        result.update(chart_kind="unknown", confidence=0.0, confidence_factors=[], error="plot region too small to analyse")
        return result
    pw, ph = rect[2] - rect[0], rect[3] - rect[1]
    hue_series, _ = _hue_series_masks(img, rect)
    ov = img.copy()
    cv2.rectangle(ov, (int(px0), int(py0)), (int(px1), int(py1)), (0, 220, 0), 1)

    # chart-kind gate: filled areas / candlesticks are not line series
    kind = "line_chart"
    for s in hue_series:
        closed = cv2.morphologyEx(s["mask"].astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=2)
        n, _, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
        comps = [stats[i] for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 30]
        width_cover = sum(c[cv2.CC_STAT_WIDTH] for c in comps if c[cv2.CC_STAT_WIDTH] >= 0.05 * pw)
        small = [c for c in comps if c[cv2.CC_STAT_WIDTH] < 0.08 * pw]
        filled = any(c[cv2.CC_STAT_AREA] / max(1, c[cv2.CC_STAT_WIDTH] * c[cv2.CC_STAT_HEIGHT]) > 0.55
                     and c[cv2.CC_STAT_WIDTH] * c[cv2.CC_STAT_HEIGHT] > 0.04 * pw * ph for c in comps)
        if filled or (len(small) >= 8 and width_cover < 0.6 * pw):
            kind = "candlestick_or_bars"
    if kind != "line_chart":
        limitations.append("Filled shapes / many small bodies detected (bar, area, candlestick or pie chart). Line digitization does not apply; no series were extracted.")
        result.update(chart_kind=kind, confidence=0.0, confidence_factors=[], overlay=to_base64_png(ov))
        return result

    cal_y = calibrate_y(img, gray, [px0, py0, px1, py1], axes.get("left_axis_x", px0), calibration) if axes["found"] or calibration else {"source": None, "reason": "no axes", "n_ticks": 0}
    cal_x = calibrate_x(img, [px0, py0, px1, py1], calibration)
    result["calibration"] = {"y": {k: v for k, v in cal_y.items()}, "x": {k: v for k, v in cal_x.items() if k != "labels"}}
    slope = cal_y.get("slope")
    res_y = abs(slope) if slope is not None else None

    for si, s in enumerate(hue_series):
        mask = _clean_series_mask(s["mask"], pw, ph)
        cols = _columns(mask)
        valid = np.flatnonzero(~np.isnan(cols["y"]))
        if valid.size < 0.15 * pw:
            continue
        first, last = int(valid[0]), int(valid[-1])
        thickness = float(np.median(cols["thick"][valid]))
        covered = valid.size / max(1, last - first + 1)
        gaps = [(a + first, b + first) for a, b in _runs(np.isnan(cols["y"][first:last + 1])) if b - a + 1 >= max(3, 0.015 * pw)]
        markers = _find_markers(mask, thickness)
        discrete = 3 <= len(markers) <= 24 and bool(mask.sum() > 0)
        if discrete:   # categorical axes (tenors) put markers at even spacing; corners of a wiggly line do not
            sp = np.diff([m[0] for m in markers])
            discrete = bool(np.mean(np.abs(sp / np.median(sp) - 1) < 0.3) >= 0.75)
        bgr = [int(v) for v in np.median(img[rect[1]:rect[3], rect[0]:rect[2]][mask.astype(bool)], axis=0)]
        pts = []
        if discrete:
            mode = "markers"
            for (mx, my, _a) in markers:
                pts.append({"x_px": mx + rect[0], "y_px": my + rect[1], "loc_err_px": 0.7})
        else:
            mode = "continuous"
            xs = np.linspace(first, last, min(max_points, last - first + 1)).round().astype(int)
            for x in xs:
                if np.isnan(cols["y"][x]):
                    continue
                steep = cols["span"][x] > 2.2 * thickness
                pts.append({"x_px": float(x + rect[0]), "y_px": float(cols["y"][x] + rect[1]), "loc_err_px": float(max(0.7, cols["span"][x] / 2)), "steep_segment": bool(steep)})
        for p in pts:
            p["x_fraction"] = (p["x_px"] - px0) / max(1.0, px1 - px0)
            p["y_fraction"] = (py1 - p["y_px"]) / max(1.0, py1 - py0)
            if slope is not None:
                p["y_value"] = round(cal_y["slope"] * p["y_px"] + cal_y["intercept"], 6)
                u = np.sqrt((p["loc_err_px"] * res_y) ** 2 + cal_y["rms_value_error"] ** 2 + (1.0 * res_y) ** 2)
                p["y_uncertainty"] = round(float(u), 6)
            if cal_x.get("kind") == "tenor":
                near = min(cal_x["tenors"], key=lambda t: abs(t["cx"] - p["x_px"]))
                spacing = np.median(np.diff([t["cx"] for t in cal_x["tenors"]])) if len(cal_x["tenors"]) > 1 else pw
                if abs(near["cx"] - p["x_px"]) <= 0.45 * spacing:
                    p["tenor"] = near["label"]
            elif cal_x.get("kind") == "numeric":
                p["x_value"] = round(cal_x["slope"] * p["x_px"] + cal_x["intercept"], 6)
            elif cal_x.get("labels"):
                near = min(cal_x["labels"], key=lambda t: abs(t["cx"] - p["x_px"]))
                if abs(near["cx"] - p["x_px"]) <= 0.02 * pw:
                    p["x_label"] = near["text"]
        if mode == "markers":
            _fill_missing_tenors(img, pts, rect, py1)
        series = {"index": si, "color_bgr": bgr, "mode": mode, "n_points": len(pts), "coverage": round(covered, 3), "line_thickness_px": round(thickness, 1),
                  "gaps": [{"x_start_px": a + rect[0], "x_end_px": b + rect[0]} for a, b in gaps], "points": pts}
        result["series"].append(series)
        for p in pts:
            cv2.circle(ov, (int(round(p["x_px"])), int(round(p["y_px"]))), 3, (255, 0, 255), -1)
        if mode == "markers":
            for p in pts:
                cv2.circle(ov, (int(round(p["x_px"])), int(round(p["y_px"]))), 6, (255, 255, 0), 1)
    for t in cal_y.get("ticks", []):
        cv2.line(ov, (int(px0) - 8, int(round(t["y_px"]))), (int(px0), int(round(t["y_px"]))), (0, 255, 255), 2)

    result["overlay"] = to_base64_png(ov)
    # ------------------------------------------------------------ interpretation + confidence
    if not result["series"]:
        result.update(chart_kind="unknown", confidence=0.0, confidence_factors=[])
        limitations.append("No coloured curve was found inside the plot region (grey/black curves are not supported by the hue segmenter).")
        return result
    main = max(result["series"], key=lambda s: s["n_points"])
    tenor_pts = [p for p in main["points"] if "tenor" in p]
    result["chart_kind"] = "yield_curve" if (main["mode"] == "markers" and len(tenor_pts) >= 3) else "line_chart"
    if slope is None:
        limitations.append(f"No y-axis calibration ({cal_y.get('reason')}). Only normalised plot coordinates are returned; supply the axis values manually to get numbers.")
    for n in cal_y.get("notes", []):
        limitations.append(n)
    if main["gaps"]:
        limitations.append(f"{len(main['gaps'])} gap(s) in the plotted line (no curve pixels) -- values inside gaps are NOT interpolated.")
    if any(p.get("steep_segment") for p in main["points"]):
        limitations.append("Near-vertical segments exist: the column median is used, so values there carry a larger error.")
    if len(result["series"]) > 1:
        limitations.append(f"{len(result['series'])} colour series detected; each is reported separately and none is labelled by the legend text.")
    factors = [
        {"factor": "axes_detected", "score": 1.0 if axes["found"] else 0.45},
        {"factor": "y_calibration", "score": 0.0 if slope is None else (0.55 if cal_y["source"] == "ocr" and cal_y["n_ticks"] == 2 else min(1.0, 1.0 - min(0.5, cal_y.get("rms_px_error", 0) / 6)))},
        {"factor": "curve_coverage", "score": round(float(main["coverage"]), 3)},
        {"factor": "series_clarity", "score": 1.0 if len(result["series"]) == 1 else 0.8},
    ]
    result["confidence"] = round(float(np.prod([f["score"] for f in factors])), 3)
    result["confidence_factors"] = factors
    result["confidence_note"] = "Heuristic product of the factors above, NOT a calibrated probability of numerical correctness."
    result["resolution"] = {"value_per_pixel_y": None if res_y is None else round(res_y, 6),
                            "quantisation_note": "one-pixel vertical error ~ this many y-axis units"}
    return result


def to_csv(result: dict) -> str:
    lines = ["series,x_px,y_px,x_label_or_tenor,x_value,y_value,y_uncertainty"]
    for s in result.get("series", []):
        for p in s["points"]:
            lab = p.get("tenor") or p.get("x_label") or ""
            lines.append(",".join(str(v) for v in (s["index"], round(p["x_px"], 1), round(p["y_px"], 1), lab, p.get("x_value", ""), p.get("y_value", ""), p.get("y_uncertainty", ""))))
    return "\n".join(lines)
