"""
Feature 8 -- Video-based market-screen intelligence (+ Feature C, intelligent frame selection).

Pipeline: read video sequentially with cv2.VideoCapture -> sample at a target rate -> change-score
frame selection -> per selected frame: content detection (chart axes / table rules / trained layout
detector if present) + OCR field extraction -> per-instrument value tracking -> event detection ->
chronological timeline.

Frame selection ("event-driven change-threshold policy", NOT reinforcement learning): a sampled frame is
kept only if it differs from the last KEPT frame by enough pixels (or enough in a local block, so a
single changing number on a busy screen still counts) AND it has settled (differs little from the
previous sampled frame, so half-rendered transitions are skipped). A hard budget then prunes the
lowest-scoring kept frames. The report states how many frames OCR was spared.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from app.cv_engine.vision import flow as flow_mod
from app.cv_engine.vision import digitize
from app.cv_engine.vision.jobs import JobContext

ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".webm", ".mkv"}
MAX_VIDEO_BYTES = 60 * 1024 * 1024
MAX_DURATION_S = 240.0
SIG_W, SIG_H = 320, 180
CHANGE_PCT = 0.08       # % of signature pixels changed (|dI|>25) to count as a change
BLOCK_MEAN = 12.0       # or mean abs diff inside one 16x9 block
SETTLE_PCT = 0.06       # consecutive-sample change below this = screen has settled


def probe(path: str) -> dict:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("Could not open video (unsupported codec or corrupt file)")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    meta = {"fps": round(float(fps), 3), "frame_count": n, "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration_s": round(n / fps, 2) if fps > 0 and n > 0 else None}
    ok, _ = cap.read()
    cap.release()
    if not ok:
        raise ValueError("Video opened but no frames could be decoded")
    return meta


def signature(frame: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return cv2.GaussianBlur(cv2.resize(g, (SIG_W, SIG_H), interpolation=cv2.INTER_AREA), (3, 3), 0)


def change_scores(a: np.ndarray, b: np.ndarray) -> dict:
    d = cv2.absdiff(a, b)
    blocks = cv2.resize(d.astype(np.float32), (16, 9), interpolation=cv2.INTER_AREA)
    return {"changed_pct": round(100.0 * float((d > 25).mean()), 4), "max_block_mean": round(float(blocks.max()), 2)}


class FrameSelector:
    """Streaming selector; feed sampled frames in time order with consider()."""

    def __init__(self, change_pct: float = CHANGE_PCT, block_mean: float = BLOCK_MEAN, settle_pct: float = SETTLE_PCT):
        self.change_pct, self.block_mean, self.settle_pct = change_pct, block_mean, settle_pct
        self.last_kept: np.ndarray | None = None
        self.prev: np.ndarray | None = None
        self.pending: dict | None = None
        self.kept: list[dict] = []

    def _keep(self, rec: dict):
        self.kept.append(rec)
        self.last_kept = rec["sig"]

    def consider(self, idx: int, t: float, frame: np.ndarray) -> None:
        sig = signature(frame)
        if self.last_kept is None:
            self._keep({"idx": idx, "t": t, "frame": frame, "sig": sig, "score": 100.0, "reason": "first frame", "block": 0.0})
            self.prev = sig
            return
        vs_kept = change_scores(self.last_kept, sig)
        step = change_scores(self.prev, sig)
        changed = vs_kept["changed_pct"] >= self.change_pct or vs_kept["max_block_mean"] >= self.block_mean
        settled = step["changed_pct"] < self.settle_pct and step["max_block_mean"] < self.block_mean
        if changed:
            rec = {"idx": idx, "t": t, "frame": frame, "sig": sig, "score": vs_kept["changed_pct"], "block": vs_kept["max_block_mean"], "reason": "visual change"}
            if settled:
                self._keep(rec)
                self.pending = None
            else:
                self.pending = rec      # still moving -- wait for the screen to settle
        elif self.pending is not None:
            self._keep(self.pending)
            self.pending = None
        self.prev = sig

    def finish(self):
        if self.pending is not None:
            self._keep(self.pending)
            self.pending = None


def prune(kept: list[dict], budget: int) -> list[dict]:
    if len(kept) <= budget:
        return kept
    mid = sorted(kept[1:-1], key=lambda r: -r["score"])[: max(0, budget - 2)]
    return sorted([kept[0], *mid, kept[-1]], key=lambda r: r["idx"])


def frame_content(img: np.ndarray) -> dict:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ax = digitize.find_axes(g)
    bg = int(np.median(np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])))
    lines = (cv2.absdiff(g, np.full_like(g, bg)) >= 30).astype(np.uint8) * 255
    hor = cv2.morphologyEx(lines, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, g.shape[1] // 4), 1)))
    n_rules = len([1 for a, b in digitize._runs((hor > 0).sum(axis=1) >= 0.25 * g.shape[1])])
    out = {"has_chart_axes": bool(ax["found"]), "n_horizontal_rules": n_rules, "has_table_like_rules": n_rules >= 4}
    return out


def extract_values(img: np.ndarray) -> dict:
    from app.cv_engine.pipeline import run_pipeline
    ok, buf = cv2.imencode(".png", img)
    r = run_pipeline(buf.tobytes(), "frame.png")
    return {"fields": [f for f in r["fields"] if f.get("instrument")], "ocr_available": r["ocr_available"], "chart_type": r["chart_type"]}


def _thumb(img: np.ndarray, w: int = 420) -> str:
    import base64
    s = w / img.shape[1]
    t = cv2.resize(img, (w, int(img.shape[0] * s)), interpolation=cv2.INTER_AREA) if s < 1 else img
    ok, buf = cv2.imencode(".jpg", t, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode("ascii")


def analyze_video(path: str, ctx: JobContext | None = None, sample_fps: float = 5.0, max_frames: int = 24, with_ocr: bool = True) -> dict:
    t_start = time.perf_counter()
    cpu_start = time.process_time()
    meta = probe(path)
    if meta["duration_s"] and meta["duration_s"] > MAX_DURATION_S:
        raise ValueError(f"Video too long ({meta['duration_s']}s; limit {MAX_DURATION_S:.0f}s)")
    fps = meta["fps"] or 25.0
    stride = max(1, int(round(fps / max(0.5, sample_fps))))
    cap = cv2.VideoCapture(path)
    sel = FrameSelector()
    idx, sampled = -1, 0
    total = meta["frame_count"] or 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        if idx % stride:
            continue
        sel.consider(idx, idx / fps, frame)
        sampled += 1
        if ctx and total and sampled % 5 == 0:
            ctx.progress(0.35 * idx / total, f"scanning frames ({idx}/{total})")
            ctx.check()
    cap.release()
    sel.finish()
    kept = prune(sel.kept, max_frames)
    decode_s = time.perf_counter() - t_start

    frames_out, tracks, prev_fields = [], {}, {}
    for k, rec in enumerate(kept):
        if ctx:
            ctx.progress(0.35 + 0.6 * (k + 1) / max(1, len(kept)), f"reading frame {k + 1}/{len(kept)}")
            ctx.check()
        content = frame_content(rec["frame"])
        vals = extract_values(rec["frame"]) if with_ocr else {"fields": [], "ocr_available": False}
        for f in vals["fields"]:
            tracks.setdefault(f"{f['instrument']}|{f['metric']}", []).append({"t": round(rec["t"], 2), "value": f["value"], "confidence": f["confidence"], "flagged": f["flagged"]})
        frames_out.append({"index": rec["idx"], "t": round(rec["t"], 2), "score_changed_pct": rec["score"], "score_block_mean": rec["block"], "reason": rec["reason"],
                           "content": content, "fields": [{k2: f[k2] for k2 in ("instrument", "metric", "value", "unit", "confidence", "flagged")} for f in vals["fields"]],
                           "thumbnail": _thumb(rec["frame"])})
    events = build_events(frames_out, kept)
    proc_s = time.perf_counter() - t_start
    stats = {"frames_in_video": total or idx + 1, "frames_sampled": sampled, "frames_selected": len(kept), "frames_skipped_as_redundant": max(0, sampled - len(kept)),
             "ocr_calls": len(kept) if with_ocr else 0, "ocr_spared_pct": round(100 * (1 - len(kept) / max(1, sampled)), 1), "sample_fps": round(fps / stride, 2),
             "decode_and_select_s": round(decode_s, 2), "total_s": round(proc_s, 2), "cpu_s": round(time.process_time() - cpu_start, 2),
             "processing_fps": round((idx + 1) / max(proc_s, 1e-6), 1)}
    return {"video": meta, "frames": frames_out, "tracks": tracks, "events": events, "stats": stats, "ocr_enabled": with_ocr,
            "selection_policy": {"name": "event-driven change-threshold policy with settle check and budget pruning", "reinforcement_learning": False,
                                 "change_pct_threshold": CHANGE_PCT, "block_mean_threshold": BLOCK_MEAN, "max_frames": max_frames},
            "limitations": ["Values are OCR reads of screen pixels; a misread digit produces a false value event. Changes are only reported when confirmed in the next kept frame (or the last frame).",
                            "Frame selection is threshold-based and can miss changes smaller than the thresholds or faster than the sampling rate.",
                            "Events describe what the SCREEN showed; they are not market data and need analyst confirmation before use."]}


def build_events(frames: list[dict], kept: list[dict]) -> list[dict]:
    events: list[dict] = []
    for i, f in enumerate(frames):
        if i == 0:
            continue
        p = frames[i - 1]
        pv = {(x["instrument"], x["metric"]): x for x in p["fields"]}
        cv_ = {(x["instrument"], x["metric"]): x for x in f["fields"]}
        last = i == len(frames) - 1
        nxt = {(x["instrument"], x["metric"]): x for x in frames[i + 1]["fields"]} if not last else {}
        for key, cur in cv_.items():
            old = pv.get(key)
            if old is None:
                events.append({"t": f["t"], "frame_index": f["index"], "kind": "instrument_appeared", "severity": "info", "title": f"{key[0]} appeared on screen", "detail": {"instrument": key[0], "value": cur["value"]}})
            elif abs(cur["value"] - old["value"]) > 1e-9:
                confirmed = last or (key in nxt and abs(nxt[key]["value"] - cur["value"]) < 1e-9)
                d = round(cur["value"] - old["value"], 6)
                unit = cur["unit"]
                events.append({"t": f["t"], "frame_index": f["index"], "kind": "value_change", "severity": "notice" if confirmed else "info",
                               "title": f"{key[0]} {key[1]} changed {old['value']} -> {cur['value']}" + (f" ({d * 100:+.1f} bp)" if unit == "pct" else ""),
                               "detail": {"instrument": key[0], "metric": key[1], "unit": unit, "from": old["value"], "to": cur["value"], "delta": d,
                                          "confidence": min(old["confidence"], cur["confidence"]), "confirmed_in_next_frame": bool(confirmed), "flagged": bool(cur["flagged"] or old["flagged"])}})
        for key in pv:
            if key not in cv_:
                events.append({"t": f["t"], "frame_index": f["index"], "kind": "instrument_disappeared", "severity": "info", "title": f"{key[0]} no longer readable", "detail": {"instrument": key[0]}})
        layout_flip = (p["content"]["has_chart_axes"] != f["content"]["has_chart_axes"]) or (p["content"]["has_table_like_rules"] != f["content"]["has_table_like_rules"])
        if f["score_changed_pct"] >= 15 or layout_flip:
            events.append({"t": f["t"], "frame_index": f["index"], "kind": "scene_change", "severity": "notice",
                           "title": "Screen layout changed" if layout_flip else f"Major screen change ({f['score_changed_pct']:.0f}% of pixels)",
                           "detail": {"changed_pct": f["score_changed_pct"], "chart_axes_before": p["content"]["has_chart_axes"], "chart_axes_after": f["content"]["has_chart_axes"]}})
        a, b = kept[i - 1]["frame"], kept[i]["frame"]
        shift = flow_mod.curve_vertical_shift(a, b) if p["content"]["has_chart_axes"] and f["content"]["has_chart_axes"] else None
        if shift and abs(shift["median_shift_px"]) >= 2:
            events.append({"t": f["t"], "frame_index": f["index"], "kind": "chart_motion", "severity": "notice",
                           "title": f"Plotted line moved {abs(shift['median_shift_px']):.0f}px {'down' if shift['median_shift_px'] > 0 else 'up'} the screen",
                           "detail": {**shift, "caveat": "Visual movement only; does not establish market direction."}})
    events.sort(key=lambda e: (e["t"], e["kind"]))
    return events


# ------------------------------------------------------------------ simulated terminal video (demo + tests)
def _terminal_frame(t: float, seed_shift: int = 0) -> np.ndarray:
    img = np.full((420, 640, 3), (22, 18, 14), np.uint8)
    F = cv2.FONT_HERSHEY_DUPLEX
    if t < 8.0:
        cv2.putText(img, "G-SEC MONITOR (SIM)", (20, 40), F, 0.9, (230, 230, 230), 2, cv2.LINE_AA)
        y10 = 6.85 if t < 3.0 else 7.02
        usd = 83.2500 if t < 6.0 else 83.4100
        rows = [("2Y", f"{6.45:.2f}%"), ("5Y", f"{6.62:.2f}%"), ("10Y", f"{y10:.2f}%"), ("USD/INR", f"{usd:.4f}")]
        for k, (lab, val) in enumerate(rows):
            cv2.putText(img, lab, (30, 110 + 60 * k), F, 0.95, (230, 230, 230), 2, cv2.LINE_AA)
            cv2.putText(img, val, (260, 110 + 60 * k), F, 0.95, (230, 230, 230), 2, cv2.LINE_AA)
    else:
        cv2.putText(img, "YIELD CURVE VIEW (SIM)", (20, 40), F, 0.8, (230, 230, 230), 2, cv2.LINE_AA)
        x0, y0, x1, y1 = 70, 80, 600, 370
        cv2.line(img, (x0, y0), (x0, y1), (170, 170, 170), 2)
        cv2.line(img, (x0, y1), (x1, y1), (170, 170, 170), 2)
        off = 0 if t < 10.0 else -30     # line moves UP the screen at t=10s
        pts = np.array([[x0 + 30 + i * 70, int(y1 - 70 - 12 * np.sqrt(i + 1) * 4 + off)] for i in range(7)], np.int32)
        cv2.polylines(img, [pts], False, (60, 160, 255), 3, cv2.LINE_AA)
    return img


def make_demo_video(path: str, seconds: float = 12.0, fps: int = 10) -> dict:
    """Writes a simulated market-terminal clip (MJPG/AVI). Returns the scripted ground truth so tests can
    check the detected timeline. ALL values are simulated; nothing here is real market data."""
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), fps, (640, 420))
    if not w.isOpened():
        raise RuntimeError("OpenCV VideoWriter (MJPG) is unavailable in this environment")
    for i in range(int(seconds * fps)):
        w.write(_terminal_frame(i / fps))
    w.release()
    return {"scripted_events": [{"t": 3.0, "instrument": "10Y", "from": 6.85, "to": 7.02}, {"t": 6.0, "instrument": "USD/INR", "from": 83.25, "to": 83.41},
                                {"t": 8.0, "kind": "scene_change"}, {"t": 10.0, "kind": "chart_motion", "direction": "up"}], "fps": fps, "seconds": seconds}
