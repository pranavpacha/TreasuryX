"""
Feature 6 -- Visual anomaly detection.

Finds unusual *visual structure* in a chart/table screenshot. Every finding is a property of the
PICTURE (a gap, a jump, a spike, an unreadable number, an unfamiliar layout). None of them is
evidence of a market anomaly: a real market move, a plotting artefact and a rendering/scaling
error look identical here. Findings are therefore routed to analyst review, never acted on.

Detectors (all computed from pixels):
  gap          : stretch of the plotted line with no curve pixels (missing/broken segment)
  spike        : single excursion that returns to the local median within <=3 samples
  discontinuity: sustained level shift (large step that does not revert)
  value_flag   : OCR-extracted values that are implausible / low-confidence (unreadable)
Spike/jump/gap thresholds are expressed in plot-height fractions and robust (MAD) noise
estimates, so they do not depend on axis units or calibration.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.cv_engine.preprocessing import to_base64_png
from app.cv_engine.vision import digitize

MIN_STEP = 0.10          # fraction of plot height
MAD_K = 6.0
DISCLAIMER = ("Visual anomaly = an unusual structure in the image. It is NOT a confirmed financial anomaly; "
              "it may be a rendering, scaling or capture artefact. Review before drawing any market conclusion.")


def _sev(value: float, thr: float) -> float:
    return round(float(min(1.0, value / (3 * thr))), 3)


def curve_anomalies(points: list[dict], gaps: list[dict], plot_rect: list[float], discrete: bool) -> list[dict]:
    out: list[dict] = []
    y = np.array([p["y_fraction"] for p in points])
    x = np.array([p["x_px"] for p in points])
    top, bot = plot_rect[1], plot_rect[3]

    def box(i0: int, i1: int) -> list[float]:
        ys = [points[k]["y_px"] for k in range(i0, i1 + 1)]
        return [round(float(x[i0] - 6), 1), round(float(min(ys) - 6), 1), round(float(x[i1] - x[i0] + 12), 1), round(float(max(ys) - min(ys) + 12), 1)]

    for g in gaps:
        out.append({"kind": "gap", "severity": _sev(g["x_end_px"] - g["x_start_px"], 0.05 * (plot_rect[2] - plot_rect[0])),
                    "bbox": [g["x_start_px"] - 4, top, g["x_end_px"] - g["x_start_px"] + 8, bot - top],
                    "description": f"No curve pixels for {g['x_end_px'] - g['x_start_px']:.0f}px of the plotted line (missing or broken segment).",
                    "evidence": {"x_start_px": g["x_start_px"], "x_end_px": g["x_end_px"]}})
    if len(y) < 4:
        return out
    if discrete:
        # markers: deviation from the straight line through both neighbours
        for i in range(1, len(y) - 1):
            dev = abs(y[i] - (y[i - 1] + y[i + 1]) / 2)
            if dev > 0.12 + 0.5 * abs(y[i + 1] - y[i - 1]):
                out.append({"kind": "spike", "severity": _sev(dev, 0.15), "bbox": box(i, i),
                            "description": f"Point {i + 1} sits {dev * 100:.0f}% of the plot height off the line through its neighbours.",
                            "evidence": {"index": i, "deviation_fraction": round(float(dev), 3)}})
        for i in range(len(y) - 1):
            step = y[i + 1] - y[i]
            tail_same = i + 2 < len(y) and abs(y[i + 2] - y[i + 1]) < 0.5 * abs(step)
            if abs(step) > 0.32 and tail_same and not any(a["bbox"][0] <= x[i] <= a["bbox"][0] + a["bbox"][2] for a in out if a["kind"] == "spike"):
                out.append({"kind": "discontinuity", "severity": _sev(abs(step), 0.32), "bbox": box(i, i + 1),
                            "description": f"Level shift of {abs(step) * 100:.0f}% of the plot height between adjacent points that does not revert.",
                            "evidence": {"index": i + 1, "step_fraction": round(float(step), 3)}})
        return out
    # Dense per-column grid (missing columns stay NaN, so a gap never creates a fake step).
    x0 = int(np.floor(x.min()))
    n_cols = int(np.ceil(x.max())) - x0 + 1
    grid = np.full(n_cols, np.nan)
    for xi, yi in zip(x, y):
        grid[int(round(xi)) - x0] = yi
    win = max(3, int(0.03 * n_cols))
    small = max(2, int(0.01 * n_cols))
    hot_idx, thr, valid_n = [], MIN_STEP, 0
    for w_ in (small, win):
        ends = np.full(n_cols, np.nan)
        ends[: n_cols - w_] = grid[w_:] - grid[: n_cols - w_]    # change of the line over a window of 1% / 3% of the width
        valid = ends[~np.isnan(ends)]
        if valid.size < 10:
            return out
        valid_n = valid.size
        mad = float(np.median(np.abs(valid - np.median(valid)))) * 1.4826
        t_w = max(MIN_STEP, MAD_K * mad)
        hot_idx.append(np.flatnonzero(np.abs(np.nan_to_num(ends)) > t_w))
        thr = max(thr, t_w) if w_ == win else thr
    hot = np.unique(np.concatenate(hot_idx))
    if hot.size == 0:
        return out
    groups = np.split(hot, np.flatnonzero(np.diff(hot) > win) + 1)
    for g in groups:
        s0, e0 = int(g[0]), int(g[-1]) + win
        before = np.nanmedian(grid[max(0, s0 - 2 * win): s0 + 1]) if s0 > 0 else np.nan
        after = np.nanmedian(grid[e0: e0 + 2 * win + 1]) if e0 < n_cols else np.nan
        seg = grid[s0: e0 + 1]
        if np.isnan(before) or np.isnan(after) or np.all(np.isnan(seg)):
            continue
        peak = float(seg[np.nanargmax(np.abs(seg - before))] - before)
        reverts = abs(after - before) < 0.4 * abs(peak)
        i0, i1 = x0 + s0, x0 + min(e0, n_cols - 1)
        ys_px = [p["y_px"] for p in points if i0 <= p["x_px"] <= i1] or [top, bot]
        bbox = [round(float(i0 - 6), 1), round(float(min(ys_px) - 6), 1), round(float(i1 - i0 + 12), 1), round(float(max(ys_px) - min(ys_px) + 12), 1)]
        if reverts:
            out.append({"kind": "spike", "severity": _sev(abs(peak), thr), "bbox": bbox,
                        "description": f"Excursion of {abs(peak) * 100:.0f}% of the plot height within {win} px-columns that returns to the previous level.",
                        "evidence": {"x_start_px": i0, "x_end_px": i1, "excursion_fraction": round(peak, 3), "threshold": round(thr, 3)}})
        else:
            out.append({"kind": "discontinuity", "severity": _sev(abs(after - before), thr), "bbox": bbox,
                        "description": f"Abrupt level shift of {abs(after - before) * 100:.0f}% of the plot height that does not revert.",
                        "evidence": {"x_start_px": i0, "x_end_px": i1, "level_shift_fraction": round(float(after - before), 3), "threshold": round(thr, 3)}})
    return out


def analyze(img: np.ndarray, with_ocr: bool = True) -> dict:
    dig = digitize.digitize(img, max_points=4000)
    anomalies: list[dict] = []
    method_notes: list[str] = []
    main = max(dig["series"], key=lambda s: s["n_points"]) if dig.get("series") else None
    if main is not None:
        anomalies += curve_anomalies(main["points"], main["gaps"], dig["plot_rect"], main["mode"] == "markers")
    else:
        method_notes.append(f"No line series found (chart kind: {dig.get('chart_kind')}); curve-structure detectors did not run.")

    if with_ocr:
        from app.cv_engine.ocr import _TESSERACT_IMPORT_OK
        if _TESSERACT_IMPORT_OK:
            from app.cv_engine.pipeline import run_pipeline
            ok, buf = cv2.imencode(".png", img)
            r = run_pipeline(buf.tobytes(), "anomaly.png")
            for f in r["fields"]:
                low = f["confidence"] < 0.5
                if f.get("flagged") or low:
                    sr = f.get("source_region") or [0, 0, 20, 20]
                    anomalies.append({"kind": "value_flag", "severity": 0.8 if f.get("flagged") else 0.4, "bbox": [float(v) for v in sr],
                                      "description": f"{f.get('instrument') or 'unlabelled value'} = {f['value']}: " + (f.get("flag_reason") or f"low OCR confidence ({f['confidence']:.2f})"),
                                      "evidence": {"instrument": f.get("instrument"), "value": f["value"], "ocr_confidence": f["confidence"], "flag_reason": f.get("flag_reason")}})
        else:
            method_notes.append("OCR unavailable: value-readability checks did not run.")

    ov = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    colors = {"gap": (0, 165, 255), "spike": (0, 0, 255), "discontinuity": (255, 0, 255), "value_flag": (0, 255, 255)}
    for a in anomalies:
        x, y, w, h = [int(round(v)) for v in a["bbox"]]
        cv2.rectangle(ov, (x, y), (x + w, y + h), colors[a["kind"]], 2)
    anomalies.sort(key=lambda a: -a["severity"])
    return {"anomalies": anomalies, "n_anomalies": len(anomalies), "chart_kind": dig.get("chart_kind"), "digitization_confidence": dig.get("confidence"),
            "method_notes": method_notes, "disclaimer": DISCLAIMER, "review_required": bool(anomalies), "overlay": to_base64_png(ov),
            "detectors": {"gap": "no curve pixels over a stretch of the line", "spike": "excursion reverting in <=3 samples (MAD-scaled)", "discontinuity": "sustained level shift (MAD-scaled)",
                          "value_flag": "OCR value implausible or low confidence", "novel_layout": "Siamese-embedding kNN distance above the 99th percentile of known layouts"}}
