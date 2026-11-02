"""
Feature 7 -- Optical flow for market-screen sequences.

Dense Farneback flow (every pixel) + sparse pyramidal Lucas-Kanade on Shi-Tomasi corners with a
forward-backward consistency check. Flow measures how pixels MOVED between two frames. It says
nothing about whether a market rose or fell: a chart's axis can be re-scaled, a window scrolled
or a ticker re-rendered and the flow field will show motion either way.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.cv_engine.preprocessing import to_base64_png
from app.cv_engine.vision import digitize

MAX_DIM = 640
MOVE_THR_PX = 1.0
CAVEAT = ("Optical flow measures visual (pixel) movement only. It does not establish market direction: re-scaled axes, scrolling windows "
          "and re-rendered text all produce motion.")


def _prep(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    s = min(1.0, MAX_DIM / max(g.shape))
    return cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else g


def farneback(ga: np.ndarray, gb: np.ndarray) -> np.ndarray:
    return cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 3, 15, 3, 5, 1.2, 0)


def lucas_kanade(ga: np.ndarray, gb: np.ndarray, max_corners: int = 200) -> dict:
    p0 = cv2.goodFeaturesToTrack(ga, maxCorners=max_corners, qualityLevel=0.01, minDistance=7, blockSize=7)
    if p0 is None:
        return {"tracks": [], "n_corners": 0}
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    p1, st, _ = cv2.calcOpticalFlowPyrLK(ga, gb, p0, None, **lk)
    p0r, st2, _ = cv2.calcOpticalFlowPyrLK(gb, ga, p1, None, **lk)
    fb_err = np.linalg.norm((p0 - p0r).reshape(-1, 2), axis=1)
    good = (st.ravel() == 1) & (st2.ravel() == 1) & (fb_err < 1.0)
    a, b = p0.reshape(-1, 2)[good], p1.reshape(-1, 2)[good]
    return {"tracks": np.hstack([a, b]).tolist(), "n_corners": int(len(p0)), "n_reliable": int(good.sum())}


def flow_to_color(flow: np.ndarray) -> np.ndarray:
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    hsv = np.zeros((*flow.shape[:2], 3), np.uint8)
    hsv[..., 0] = ang * 180 / np.pi / 2
    hsv[..., 1] = 255
    hsv[..., 2] = np.clip(mag / max(1.0, np.percentile(mag, 99.5)) * 255, 0, 255)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def curve_vertical_shift(img_a: np.ndarray, img_b: np.ndarray) -> dict | None:
    """Median vertical displacement of the coloured plotted line between two frames of the same chart
    (segmentation-based, independent of the flow field). Positive = line moved DOWN the image."""
    try:
        ga = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
        ax = digitize.find_axes(ga)
        if not ax["found"]:
            return None
        x0, y0, x1, y1 = [int(v) for v in ax["plot_rect"]]
        rect = (x0 + 3, y0 + 3, x1 - 1, y1 - 3)
        ys = []
        for im in (img_a, img_b):
            series, _ = digitize._hue_series_masks(im, rect)
            if not series:
                return None
            m = digitize._clean_series_mask(series[0]["mask"], rect[2] - rect[0], rect[3] - rect[1])
            ys.append(digitize._columns(m)["y"])
        both = ~np.isnan(ys[0]) & ~np.isnan(ys[1])
        if both.sum() < 20:
            return None
        d = ys[1][both] - ys[0][both]
        return {"median_shift_px": round(float(np.median(d)), 2), "mean_shift_px": round(float(d.mean()), 2), "columns_compared": int(both.sum()),
                "note": "Same axes are assumed in both frames; if the axis range changed this is a visual shift, not a value change."}
    except Exception:  # noqa: BLE001
        return None


def analyze_pair(img_a: np.ndarray, img_b: np.ndarray) -> dict:
    ga, gb = _prep(img_a), _prep(img_b)
    if ga.shape != gb.shape:
        gb = cv2.resize(gb, (ga.shape[1], ga.shape[0]), interpolation=cv2.INTER_AREA)
    flow = farneback(ga, gb)
    mag = np.linalg.norm(flow, axis=2)
    moving = (mag > MOVE_THR_PX).astype(np.uint8) * 255
    moving = cv2.morphologyEx(cv2.dilate(moving, np.ones((5, 5), np.uint8)), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(moving, connectivity=8)
    h, w = ga.shape
    regions = []
    for i in sorted(range(1, n), key=lambda k: -stats[k, cv2.CC_STAT_AREA])[:8]:
        x, y, rw, rh, ar = [int(v) for v in stats[i]]
        if ar < 0.0005 * h * w:
            continue
        f = flow[y:y + rh, x:x + rw].reshape(-1, 2)
        sel = np.linalg.norm(f, axis=1) > MOVE_THR_PX
        mdx, mdy = (np.median(f[sel], axis=0) if sel.any() else (0.0, 0.0))
        regions.append({"bbox": [x, y, rw, rh], "median_dx": round(float(mdx), 2), "median_dy": round(float(mdy), 2),
                        "mean_magnitude": round(float(np.linalg.norm(f, axis=1).mean()), 2), "direction_deg": round(float(np.degrees(np.arctan2(mdy, mdx))), 1)})
    lk = lucas_kanade(ga, gb)
    tr = np.array(lk["tracks"]) if lk["tracks"] else np.zeros((0, 4))
    disp = tr[:, 2:] - tr[:, :2] if len(tr) else np.zeros((0, 2))
    lk_moving = np.linalg.norm(disp, axis=1) > MOVE_THR_PX if len(disp) else np.array([], bool)
    flow_img = flow_to_color(flow)
    arrows = cv2.cvtColor(gb, cv2.COLOR_GRAY2BGR)
    step = max(10, min(h, w) // 28)
    for yy in range(step // 2, h, step):
        for xx in range(step // 2, w, step):
            dx, dy = flow[yy, xx]
            if abs(dx) + abs(dy) > MOVE_THR_PX:
                cv2.arrowedLine(arrows, (xx, yy), (int(round(xx + dx)), int(round(yy + dy))), (0, 255, 0), 1, tipLength=0.4)
    for x0, y0, x1, y1 in tr[lk_moving] if len(tr) else []:
        cv2.arrowedLine(arrows, (int(x0), int(y0)), (int(x1), int(y1)), (0, 165, 255), 2, tipLength=0.4)
    for r in regions:
        x, y, rw, rh = r["bbox"]
        cv2.rectangle(arrows, (x, y), (x + rw, y + rh), (255, 0, 255), 1)
    return {
        "summary": {"mean_magnitude_px": round(float(mag.mean()), 3), "max_magnitude_px": round(float(mag.max()), 2), "moving_pixel_share_pct": round(100 * float((mag > MOVE_THR_PX).mean()), 2),
                    "lk_corners": lk["n_corners"], "lk_reliable_tracks": lk.get("n_reliable", 0), "lk_moving_tracks": int(lk_moving.sum()),
                    "lk_median_dx": round(float(np.median(disp[:, 0])), 2) if len(disp) else None, "lk_median_dy": round(float(np.median(disp[:, 1])), 2) if len(disp) else None},
        "moving_regions": regions, "curve_shift": curve_vertical_shift(img_a, img_b),
        "images": {"flow_color": to_base64_png(flow_img), "vectors": to_base64_png(arrows)},
    }


def analyze_sequence(frames: list[np.ndarray]) -> dict:
    if len(frames) < 2:
        raise ValueError("optical flow needs at least 2 frames")
    pairs = []
    for i in range(len(frames) - 1):
        r = analyze_pair(frames[i], frames[i + 1])
        r["pair"] = [i, i + 1]
        pairs.append(r)
    mags = [p["summary"]["mean_magnitude_px"] for p in pairs]
    peak = int(np.argmax(mags))
    return {"n_frames": len(frames), "pairs": pairs,
            "overall": {"mean_of_mean_magnitudes_px": round(float(np.mean(mags)), 3), "most_motion_pair": pairs[peak]["pair"], "most_motion_magnitude_px": mags[peak],
                        "total_moving_regions": int(sum(len(p["moving_regions"]) for p in pairs))},
            "caveat": CAVEAT, "methods": ["Farneback dense optical flow (polynomial expansion)", "Pyramidal Lucas-Kanade on Shi-Tomasi corners with forward-backward check"]}
