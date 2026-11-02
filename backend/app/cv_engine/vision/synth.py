"""
Synthetic financial-screenshot generator -- the reproducible dataset behind the detector,
segmenter, classifier, Siamese encoder, few-shot and self-supervised experiments.

Why synthetic: no labeled dataset of financial screenshots (with boxes + pixel masks + chart
ground truth) exists for this project. Everything here is procedurally drawn with OpenCV, so
boxes, masks and the true underlying numbers are known BY CONSTRUCTION. Every number it
produces is labeled synthetic; none of it is real market data, and metrics measured on it say
nothing about accuracy on real screenshots (see docs/datasets.md).

Leakage control: a *template* fixes the layout, theme, palette, margins, fonts and label sets;
a *variant* of a template only changes the data, a few-pixel jitter and image degradation
(noise / blur / JPEG). Splits are made BY TEMPLATE (train 0-19, val 20-24, test 25-29 per
kind), so no variant of a test template is ever seen in training.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field

import cv2
import numpy as np

W, H = 480, 320
FONT = cv2.FONT_HERSHEY_DUPLEX

KINDS = [
    "yield_curve", "fx_line_chart", "candlestick_chart", "bond_table",
    "market_report", "risk_dashboard", "portfolio_chart", "financial_statement",
]
KIND_LABELS = {
    "yield_curve": "Yield curve", "fx_line_chart": "FX line chart", "candlestick_chart": "Candlestick chart",
    "bond_table": "Bond table", "market_report": "Market report", "risk_dashboard": "Risk dashboard",
    "portfolio_chart": "Portfolio chart", "financial_statement": "Financial statement",
}
DET_CLASSES = ["chart_region", "table_region", "legend", "axis_labels", "header", "risk_section", "value_label", "footnote"]
SEG_CLASSES = ["background", "curve", "text", "table", "axes", "legend"]
SEG_BG, SEG_CURVE, SEG_TEXT, SEG_TABLE, SEG_AXES, SEG_LEGEND = range(6)

TEMPLATES_PER_KIND = 30
VARIANTS_PER_TEMPLATE = 5
SPLITS = {"train": range(0, 20), "val": range(20, 25), "test": range(25, 30)}

LIGHT = dict(bg=(255, 255, 255), text=(30, 30, 30), grid=(222, 222, 222), axis=(70, 70, 70), panel=(240, 240, 240), name="light")
DARK = dict(bg=(24, 20, 16), text=(232, 232, 232), grid=(62, 56, 50), axis=(160, 160, 160), panel=(40, 34, 28), name="dark")
CURVE_LIGHT = [(214, 100, 24), (30, 120, 240), (60, 160, 40), (190, 40, 190), (40, 40, 220)]
CURVE_DARK = [(255, 170, 60), (50, 160, 255), (90, 220, 90), (220, 80, 220), (60, 210, 240)]
UP_COLOR, DOWN_COLOR = (80, 170, 40), (50, 50, 215)

TENORS = ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]
FX_PAIRS = [("USD/INR", 83.2, 0.55, 4), ("EUR/USD", 1.085, 0.013, 4), ("EUR/INR", 90.4, 0.8, 3), ("GBP/INR", 105.3, 1.0, 3)]
WORDS = ("yields eased markets priced liquidity rupee rates central bank policy inflation demand auction supply "
         "curve steepened narrowed spread corporate treasury issuance duration carry volatility inflows outlook "
         "banking system surplus guidance dealers positioning benchmark session traders futures").split()
TITLES = {
    "yield_curve": ["G-Sec Yield Curve", "India Government Yield Curve", "Sovereign Curve", "INR Par Yield Curve"],
    "fx_line_chart": ["Spot Rate", "FX Spot - 3M", "Exchange Rate Trend", "Currency Monitor"],
    "candlestick_chart": ["OHLC Daily", "Price Action", "Candlestick View", "FX Candles"],
    "bond_table": ["G-Sec Yield Table", "Benchmark Bond Quotes", "Rates Monitor", "Bond Valuation Sheet"],
    "market_report": ["Daily Market Wrap", "Treasury Morning Note", "Rates Strategy Weekly", "Market Commentary"],
    "risk_dashboard": ["Portfolio Risk Summary", "Risk Dashboard", "Desk Risk Report", "VaR and Exposure"],
    "portfolio_chart": ["Portfolio Allocation", "Asset Mix", "Exposure Breakdown", "Holdings Overview"],
    "financial_statement": ["Statement of Income", "Financial Summary", "Balance Sheet Extract", "Annual Results"],
}


@dataclass
class SynthDoc:
    image: np.ndarray                     # HxWx3 uint8 BGR
    mask: np.ndarray                      # HxW uint8, values = SEG_* class ids
    boxes: list[tuple[int, int, int, int, int]]  # (det_class_idx, x, y, w, h) in pixels
    kind: str
    template: int
    variant: int
    scale: int
    truth: dict = field(default_factory=dict)

    @property
    def template_key(self) -> str:
        return f"{self.kind}:{self.template}"


class Canvas:
    """Draws in 480x320 'base' coordinates, multiplied by `scale`; every primitive also writes
    the matching semantic class into a mask so segmentation ground truth is exact."""

    def __init__(self, theme: dict, scale: int):
        self.s, self.theme = scale, theme
        self.w, self.h = W * scale, H * scale
        self.img = np.full((self.h, self.w, 3), theme["bg"], np.uint8)
        self.mask = np.zeros((self.h, self.w), np.uint8)
        self.boxes: list[tuple[int, int, int, int, int]] = []

    def _p(self, v: float) -> int:
        return int(round(v * self.s))

    def _t(self, t: float) -> int:
        return max(1, int(round(t * self.s)))

    def rect(self, x0, y0, x1, y1, color, thick: float = -1, seg: int | None = None):
        a, b = (self._p(x0), self._p(y0)), (self._p(x1), self._p(y1))
        th = -1 if thick < 0 else self._t(thick)
        cv2.rectangle(self.img, a, b, color, th)
        if seg is not None:
            cv2.rectangle(self.mask, a, b, seg, th)

    def line(self, p0, p1, color, thick: float = 1, seg: int | None = None):
        a, b = (self._p(p0[0]), self._p(p0[1])), (self._p(p1[0]), self._p(p1[1]))
        cv2.line(self.img, a, b, color, self._t(thick), cv2.LINE_AA if self.s > 1 else cv2.LINE_8)
        if seg is not None:
            cv2.line(self.mask, a, b, seg, self._t(thick))

    def polyline(self, pts, color, thick: float = 1.5, seg: int | None = SEG_CURVE):
        arr = np.array([[self._p(x), self._p(y)] for x, y in pts], np.int32)
        if len(arr) < 2:
            return
        cv2.polylines(self.img, [arr], False, color, self._t(thick), cv2.LINE_AA)
        if seg is not None:
            cv2.polylines(self.mask, [arr], False, seg, self._t(thick))

    def circle(self, c, r, color, fill=True, seg: int | None = SEG_CURVE):
        ctr, rad = (self._p(c[0]), self._p(c[1])), max(1, self._p(r))
        cv2.circle(self.img, ctr, rad, color, -1 if fill else self._t(1), cv2.LINE_AA)
        if seg is not None:
            cv2.circle(self.mask, ctr, rad, seg, -1)

    def text(self, txt, x, y, size=0.42, color=None, thick=1, align="l", seg=SEG_TEXT):
        """(x, y) = top-left of the text (base coords). Returns pixel bbox (x, y, w, h)."""
        color = color or self.theme["text"]
        fs, th = size * self.s, self._t(thick)
        (tw, tht), base = cv2.getTextSize(txt, FONT, fs, th)
        px, py = self._p(x), self._p(y)
        if align == "r":
            px -= tw
        elif align == "c":
            px -= tw // 2
        cv2.putText(self.img, txt, (px, py + tht), FONT, fs, color, th, cv2.LINE_AA)
        if seg is not None:
            cv2.rectangle(self.mask, (px, py), (px + tw, py + tht + base // 2), seg, -1)
        return px, py, tw, tht + base // 2

    def box(self, cls: str, x0, y0, x1, y1):
        a, b = max(0, self._p(x0)), max(0, self._p(y0))
        c, d = min(self.w - 1, self._p(x1)), min(self.h - 1, self._p(y1))
        if c - a > 3 and d - b > 3:
            self.boxes.append((DET_CLASSES.index(cls), a, b, c - a, d - b))

    def box_px(self, cls: str, x, y, w, h, pad: int = 2):
        a, b = max(0, x - pad), max(0, y - pad)
        c, d = min(self.w - 1, x + w + pad), min(self.h - 1, y + h + pad)
        if c - a > 3 and d - b > 3:
            self.boxes.append((DET_CLASSES.index(cls), a, b, c - a, d - b))


def _nice_range(lo: float, hi: float, max_ticks: int = 6) -> tuple[float, float, float]:
    span = max(hi - lo, 1e-6)
    raw = span / (max_ticks - 1)
    mag = 10 ** np.floor(np.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    return float(np.floor(lo / step) * step), float(np.ceil(hi / step) * step), float(step)


def _fmt(v: float, step: float) -> str:
    dec = 0 if step >= 1 else int(min(5, max(1, np.ceil(-np.log10(step)))))
    if step < 1 and abs(step * 10 ** dec - round(step * 10 ** dec)) > 1e-6:
        dec += 1
    return f"{v:.{dec}f}"


def _template_params(kind: str, template: int) -> dict:
    rng = np.random.default_rng(zlib.crc32(f"tpl:{kind}:{template}".encode()))
    dark = bool(rng.random() < 0.5)
    theme = dict(DARK if dark else LIGHT)
    if not dark:
        v = int(rng.integers(244, 256))
        theme["bg"] = (v, v, v)
    colors = CURVE_DARK if dark else CURVE_LIGHT
    return dict(
        rng=rng, theme=theme, color=colors[int(rng.integers(len(colors)))], color2=colors[int(rng.integers(len(colors)))],
        ml=int(rng.integers(50, 78)), mr=int(rng.integers(16, 44)), mt=int(rng.integers(36, 56)), mb=int(rng.integers(44, 62)),
        title=TITLES[kind][int(rng.integers(len(TITLES[kind])))], title_center=bool(rng.random() < 0.4),
        title_size=float(rng.uniform(0.46, 0.62)), tick_size=float(rng.uniform(0.34, 0.42)),
        legend_pos=str(rng.choice(["tr", "tl", "br", "none"])), vgrid=bool(rng.random() < 0.4),
        footnote=bool(rng.random() < 0.7), thick=float(rng.choice([1.2, 1.6, 2.0])),
        n_h=int(rng.integers(3, 6)), pair=FX_PAIRS[int(rng.integers(len(FX_PAIRS)))],
        mode=str(rng.choice(["pie", "bars", "area"])), cols=int(rng.integers(3, 5)), rows=int(rng.integers(6, 11)),
        n_tenors=int(rng.integers(6, 10)), tenor_start=int(rng.integers(0, 4)), kpi=bool(rng.random() < 0.6),
        table_style=str(rng.choice(["grid", "ruled"])), font_text=float(rng.uniform(0.34, 0.42)),
    )


def _header(c: Canvas, tp: dict, title: str | None = None, y: float = 8):
    title = title or tp["title"]
    x = W / 2 if tp["title_center"] else tp["ml"] if tp.get("align_title_plot") else 14
    bx = c.text(title, x, y, tp["title_size"], thick=1, align="c" if tp["title_center"] else "l")
    c.box_px("header", *bx)
    return bx


def _footnote(c: Canvas, tp: dict, text: str = "Source: simulated demo data. Not for trading."):
    if tp["footnote"]:
        bx = c.text(text, 14, H - 14, 0.3, color=c.theme["axis"])
        c.box_px("footnote", *bx)


def _legend(c: Canvas, tp: dict, rect, labels: list[str], colors: list[tuple[int, int, int]]):
    if tp["legend_pos"] == "none":
        return
    x0, y0, x1, y1 = rect
    lw, lh = 74, 6 + 12 * len(labels)
    lx = x1 - lw - 6 if tp["legend_pos"] in ("tr", "br") else x0 + 6
    ly = y0 + 6 if tp["legend_pos"] in ("tr", "tl") else y1 - lh - 6
    c.rect(lx, ly, lx + lw, ly + lh, c.theme["panel"], -1, SEG_LEGEND)
    c.rect(lx, ly, lx + lw, ly + lh, c.theme["axis"], 1, SEG_LEGEND)
    for i, (lab, col) in enumerate(zip(labels, colors)):
        yy = ly + 4 + 12 * i
        c.rect(lx + 4, yy + 3, lx + 14, yy + 6, col, -1, SEG_CURVE)
        c.text(lab, lx + 18, yy, 0.32)
    c.box("legend", lx, ly, lx + lw, ly + lh)


def _axes_frame(c: Canvas, tp: dict, rv, y_lo: float, y_hi: float, step: float, x_ticks: list[tuple[float, str]],
                y_labels=True):
    """Draws plot frame, gridlines, tick labels. Returns (x0, y0, x1, y1) and y-tick truth."""
    j = int(rv.integers(-2, 3))
    x0, y0, x1, y1 = tp["ml"] + j, tp["mt"] + int(rv.integers(-2, 3)), W - tp["mr"] + j, H - tp["mb"]
    th = c.theme
    n_ticks = int(round((y_hi - y_lo) / step))
    y_ticks = []
    ylab_boxes = []
    for i in range(n_ticks + 1):
        v = y_lo + i * step
        yy = y1 - (v - y_lo) / (y_hi - y_lo) * (y1 - y0)
        if 0 < i < n_ticks:
            c.line((x0, yy), (x1, yy), th["grid"], 0.8, SEG_AXES)
        c.line((x0 - 3, yy), (x0, yy), th["axis"], 1, SEG_AXES)
        if y_labels:
            ylab_boxes.append(c.text(_fmt(v, step), x0 - 6, yy - 4, tp["tick_size"], align="r"))
        y_ticks.append({"value": float(v), "y_px": float(yy * c.s)})
    if tp["vgrid"]:
        for xf, _ in x_ticks:
            xx = x0 + xf * (x1 - x0)
            c.line((xx, y0), (xx, y1), th["grid"], 0.8, SEG_AXES)
    xt_truth, xlab_boxes = [], []
    for xf, lab in x_ticks:
        xx = x0 + xf * (x1 - x0)
        c.line((xx, y1), (xx, y1 + 3), th["axis"], 1, SEG_AXES)
        xlab_boxes.append(c.text(lab, xx, y1 + 6, tp["tick_size"], align="c"))
        xt_truth.append({"label": lab, "x_px": float(xx * c.s)})
    c.line((x0, y0), (x0, y1), th["axis"], 1.6, SEG_AXES)
    c.line((x0, y1), (x1, y1), th["axis"], 1.6, SEG_AXES)
    if ylab_boxes:
        xs, ys = min(b[0] for b in ylab_boxes), min(b[1] for b in ylab_boxes)
        xe, ye = max(b[0] + b[2] for b in ylab_boxes), max(b[1] + b[3] for b in ylab_boxes)
        c.box_px("axis_labels", xs, ys, xe - xs, ye - ys)
    if xlab_boxes:
        xs, ys = min(b[0] for b in xlab_boxes), min(b[1] for b in xlab_boxes)
        xe, ye = max(b[0] + b[2] for b in xlab_boxes), max(b[1] + b[3] for b in xlab_boxes)
        c.box_px("axis_labels", xs, ys, xe - xs, ye - ys)
    c.box("chart_region", x0, y0, x1, y1)
    return (x0, y0, x1, y1), y_ticks, xt_truth


def _anomaly_apply(series: np.ndarray, kind: str | None, rv) -> tuple[np.ndarray, dict | None, set[int]]:
    """Inject a controlled VISUAL anomaly (used only to evaluate the anomaly detector)."""
    if kind is None:
        return series, None, set()
    s = series.copy()
    n = len(s)
    span = float(s.max() - s.min()) or 1.0
    if kind == "spike":
        i = int(rv.integers(n // 4, 3 * n // 4))
        s[i] += float(rv.choice([-1, 1])) * 0.7 * span
        return s, {"kind": kind, "index": i}, set()
    if kind == "jump":
        i = int(rv.integers(n // 4, 3 * n // 4))
        s[i:] += float(rv.choice([-1, 1])) * 0.7 * span
        return s, {"kind": kind, "index": i}, set()
    if kind == "gap":
        width = max(2, int(0.14 * n))
        i = int(rv.integers(n // 4, 3 * n // 4 - width))
        return s, {"kind": kind, "index": i, "width": width}, set(range(i + 1, i + width))
    raise ValueError(f"unknown anomaly {kind}")


def _draw_series(c: Canvas, pts: list[tuple[float, float]], skip: set[int], color, thick: float):
    seg: list[tuple[float, float]] = []
    for i, p in enumerate(pts):
        if i in skip:
            c.polyline(seg, color, thick)
            seg = []
        else:
            seg.append(p)
    c.polyline(seg, color, thick)


def _yield_curve(c: Canvas, tp: dict, rv, anomaly) -> dict:
    tenors = TENORS[tp["tenor_start"]: tp["tenor_start"] + tp["n_tenors"]]
    n = len(tenors)
    shape = str(rv.choice(["normal", "flat", "inverted", "humped"]))
    base = float(rv.uniform(5.2, 7.4))
    i = np.arange(n)
    shapes = {"normal": 0.9 * (1 - np.exp(-i / 3.0)), "flat": 0.05 * i, "inverted": 0.8 - 0.9 * (1 - np.exp(-i / 3.0)),
              "humped": 0.7 * np.sin(np.pi * i / max(1, n - 1))}
    vals = np.round(base + shapes[shape] + rv.normal(0, 0.03, n), 2)
    vals, info, skip = _anomaly_apply(vals, anomaly, rv)
    lo, hi, step = _nice_range(float(vals.min()) - 0.15, float(vals.max()) + 0.15, 6)
    x_ticks = [((k + 0.5) / n, t) for k, t in enumerate(tenors)]
    _header(c, tp)
    rect, y_ticks, xt = _axes_frame(c, tp, rv, lo, hi, step, x_ticks)
    x0, y0, x1, y1 = rect
    pts = [(x0 + (k + 0.5) / n * (x1 - x0), y1 - (v - lo) / (hi - lo) * (y1 - y0)) for k, v in enumerate(vals)]
    _draw_series(c, pts, skip, tp["color"], tp["thick"])
    for k, p in enumerate(pts):
        c.circle(p, 2.6, tp["color"])
    _legend(c, tp, rect, ["Par yield"], [tp["color"]])
    if tp["kpi"]:
        bx = c.text(f"{tenors[min(n - 1, 4)]}  {vals[min(n - 1, 4)]:.2f}%", W - 14, 10, 0.42, align="r")
        c.box_px("value_label", *bx)
    _footnote(c, tp)
    return {"plot_rect_px": [v * c.s for v in rect], "y_ticks": y_ticks, "x_ticks": xt, "y_range": [lo, hi], "categorical_x": True,
            "points": [{"x_label": t, "value": float(v), "x_px": p[0] * c.s, "y_px": p[1] * c.s} for t, v, p in zip(tenors, vals, pts)],
            "anomaly": info, "curve_color_bgr": list(tp["color"])}


def _fx_line(c: Canvas, tp: dict, rv, anomaly) -> dict:
    pair, base, vol, dec = tp["pair"]
    n = int(rv.integers(60, 100))
    s = base * (1 + rv.uniform(-0.01, 0.01)) + np.cumsum(rv.normal(0, vol * 0.18, n)) + np.linspace(0, rv.uniform(-1, 1) * vol, n)
    s = np.round(s, dec)
    s, info, skip = _anomaly_apply(s, anomaly, rv)
    lo, hi, step = _nice_range(float(s.min()) - 0.05 * np.ptp(s), float(s.max()) + 0.05 * np.ptp(s), 6)
    labels = ["01-Sep", "08-Sep", "15-Sep", "22-Sep", "29-Sep"]
    x_ticks = [(k / 4, lab) for k, lab in enumerate(labels)]
    _header(c, tp, f"{pair} {tp['title']}")
    rect, y_ticks, xt = _axes_frame(c, tp, rv, lo, hi, step, x_ticks)
    x0, y0, x1, y1 = rect
    pts = [(x0 + k / (n - 1) * (x1 - x0), y1 - (v - lo) / (hi - lo) * (y1 - y0)) for k, v in enumerate(s)]
    _draw_series(c, pts, skip, tp["color"], tp["thick"])
    _legend(c, tp, rect, [pair], [tp["color"]])
    if tp["kpi"]:
        bx = c.text(f"{pair} {s[-1]:.{dec}f}", W - 14, 10, 0.42, align="r")
        c.box_px("value_label", *bx)
    _footnote(c, tp)
    return {"plot_rect_px": [v * c.s for v in rect], "y_ticks": y_ticks, "x_ticks": xt, "y_range": [lo, hi], "categorical_x": False,
            "pair": pair, "points": [{"x_idx": k, "value": float(v), "x_px": p[0] * c.s, "y_px": p[1] * c.s} for k, (v, p) in enumerate(zip(s, pts))],
            "anomaly": info, "curve_color_bgr": list(tp["color"])}


def _candles(c: Canvas, tp: dict, rv, _anomaly) -> dict:
    n = int(rv.integers(22, 36))
    close = 100 + np.cumsum(rv.normal(0, 1.2, n))
    open_ = np.concatenate([[100.0], close[:-1]]) + rv.normal(0, 0.3, n)
    hi_ = np.maximum(open_, close) + np.abs(rv.normal(0.8, 0.4, n))
    lo_ = np.minimum(open_, close) - np.abs(rv.normal(0.8, 0.4, n))
    lo, hi, step = _nice_range(float(lo_.min()) - 0.5, float(hi_.max()) + 0.5, 6)
    _header(c, tp)
    rect, y_ticks, xt = _axes_frame(c, tp, rv, lo, hi, step, [(k / 4, f"D{k * n // 4}") for k in range(5)])
    x0, y0, x1, y1 = rect
    bw = (x1 - x0) / n
    ypx = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)  # noqa: E731
    for k in range(n):
        cx = x0 + (k + 0.5) * bw
        col = UP_COLOR if close[k] >= open_[k] else DOWN_COLOR
        c.line((cx, ypx(hi_[k])), (cx, ypx(lo_[k])), col, 1, SEG_CURVE)
        c.rect(cx - bw * 0.3, ypx(max(open_[k], close[k])), cx + bw * 0.3, ypx(min(open_[k], close[k])) + 0.5, col, -1, SEG_CURVE)
    _legend(c, tp, rect, ["Up", "Down"], [UP_COLOR, DOWN_COLOR])
    _footnote(c, tp)
    return {"plot_rect_px": [v * c.s for v in rect], "y_ticks": y_ticks, "x_ticks": xt, "y_range": [lo, hi]}


def _grid_table(c: Canvas, tp: dict, rv, x0, y0, x1, y1, header: list[str], rows: list[list[str]], style: str) -> list[list[str]]:
    th = c.theme
    nr, nc = len(rows) + 1, len(header)
    rh = (y1 - y0) / nr
    cw = (x1 - x0) / nc
    c.rect(x0, y0, x1, y1, th["panel"], -1, SEG_TABLE)
    c.rect(x0, y0, x1, y0 + rh, th["grid"] if th["name"] == "light" else th["panel"], -1, SEG_TABLE)
    for r in range(nr + 1):
        yy = y0 + r * rh
        c.line((x0, yy), (x1, yy), th["axis"] if r in (0, 1, nr) else th["grid"], 1, SEG_TABLE)
    if style == "grid":
        for k in range(nc + 1):
            c.line((x0 + k * cw, y0), (x0 + k * cw, y1), th["axis"] if k in (0, nc) else th["grid"], 1, SEG_TABLE)
    fs = tp["font_text"]
    for k, hname in enumerate(header):
        if k == 0:
            c.text(hname, x0 + 5, y0 + rh / 2 - 4, fs, thick=1)
        else:
            c.text(hname, x0 + (k + 1) * cw - 6, y0 + rh / 2 - 4, fs, thick=1, align="r")
    for r, row in enumerate(rows):
        for k, cell in enumerate(row):
            if k == 0:
                c.text(cell, x0 + 5, y0 + (r + 1.5) * rh - 4, fs)
            else:
                c.text(cell, x0 + (k + 1) * cw - 6, y0 + (r + 1.5) * rh - 4, fs, align="r")
    c.box("table_region", x0, y0, x1, y1)
    return rows


def _bond_table(c: Canvas, tp: dict, rv, _anomaly) -> dict:
    _header(c, tp)
    nr = tp["rows"]
    tenors = list(rv.choice(TENORS, size=min(nr, len(TENORS)), replace=False))
    tenors.sort(key=TENORS.index)
    header = ["Tenor", "Coupon %", "Yield %", "Price"][: tp["cols"]] if tp["cols"] < 4 else ["Tenor", "Coupon %", "Yield %", "Price"]
    rows = []
    truth_rows = []
    for t in tenors:
        y = round(float(rv.uniform(5.8, 7.6)), 2)
        cp = round(float(rv.uniform(5.5, 8.0)), 2)
        px = round(float(rv.uniform(96, 104)), 2)
        rows.append([t, f"{cp:.2f}", f"{y:.2f}", f"{px:.2f}"][: len(header)])
        truth_rows.append({"tenor": t, "yield": y})
    x0, y0 = 20 + int(rv.integers(-2, 3)), 40 + int(rv.integers(-2, 3))
    _grid_table(c, tp, rv, x0, y0, W - 20, min(H - 34, y0 + 24 * (len(rows) + 1)), header, rows, tp["table_style"])
    _footnote(c, tp)
    return {"rows": truth_rows}


def _words(rv, n: int) -> str:
    return " ".join(str(w) for w in rv.choice(WORDS, size=n))


def _market_report(c: Canvas, tp: dict, rv, _anomaly) -> dict:
    _header(c, tp, y=8)
    c.text("Treasury Desk  |  Simulated", 14, 28, 0.32, color=c.theme["axis"])
    chart_right = bool(tp["rng"].random() < 0.5)
    tx0, tx1 = (14, 270) if chart_right else (200, W - 14)
    for para in range(2):
        for ln in range(int(rv.integers(5, 8))):
            c.text(_words(rv, 5), tx0, 48 + para * 92 + ln * 12, 0.33)
    cx0, cx1 = (290, W - 14) if chart_right else (14, 188)
    cy0, cy1 = 52, 200
    lo, hi = 0.0, 1.0
    c.line((cx0, cy0), (cx0, cy1), c.theme["axis"], 1.4, SEG_AXES)
    c.line((cx0, cy1), (cx1, cy1), c.theme["axis"], 1.4, SEG_AXES)
    n = 14
    y = np.cumsum(rv.normal(0, 0.1, n)) + 0.5
    y = (y - y.min()) / (np.ptp(y) + 1e-6) * 0.8 + 0.1
    pts = [(cx0 + k / (n - 1) * (cx1 - cx0), cy1 - v * (cy1 - cy0)) for k, v in enumerate(y)]
    c.polyline(pts, tp["color"], tp["thick"])
    lab = c.text("Fig. 1", (cx0 + cx1) / 2, cy1 + 4, 0.3, align="c")
    c.box_px("axis_labels", *lab)
    c.box("chart_region", cx0, cy0, cx1, cy1)
    _footnote(c, tp)
    return {}


def _risk_dashboard(c: Canvas, tp: dict, rv, _anomaly) -> dict:
    _header(c, tp)
    labels = [("VaR 95%", f"{rv.uniform(0.8, 3.2):.2f} Cr"), ("ES 97.5%", f"{rv.uniform(1.2, 4.5):.2f} Cr"),
              ("DV01", f"{rv.uniform(2, 14):.1f} L"), ("Mod Dur", f"{rv.uniform(2, 8):.2f}")]
    th = c.theme
    two_by_two = bool(tp["rng"].random() < 0.5)
    metrics = {}
    for k, (name, val) in enumerate(labels):
        if two_by_two:
            r, col = divmod(k, 2)
            x0, y0 = 14 + col * 232, 36 + r * 52
            x1, y1 = x0 + 224, y0 + 46
        else:
            x0, y0 = 14 + k * 116, 36
            x1, y1 = x0 + 110, y0 + 56
        c.rect(x0, y0, x1, y1, th["panel"], -1, SEG_TABLE)
        c.rect(x0, y0, x1, y1, th["axis"], 1, SEG_TABLE)
        c.text(name, x0 + 6, y0 + 6, 0.34, color=th["axis"])
        c.text(val, x0 + 6, y0 + 24, 0.55, thick=1)
        c.box("risk_section", x0, y0, x1, y1)
        metrics[name] = val
    by = 150 if two_by_two else 110
    bx0, bx1, by1 = 50, W - 30, H - 44
    c.line((bx0, by), (bx0, by1), th["axis"], 1.4, SEG_AXES)
    c.line((bx0, by1), (bx1, by1), th["axis"], 1.4, SEG_AXES)
    nb = int(rv.integers(5, 9))
    bw = (bx1 - bx0) / nb
    for k in range(nb):
        hh = float(rv.uniform(0.15, 1.0)) * (by1 - by - 8)
        c.rect(bx0 + k * bw + 4, by1 - hh, bx0 + (k + 1) * bw - 4, by1 - 1, tp["color"], -1, SEG_CURVE)
    c.box("chart_region", bx0, by, bx1, by1)
    lab = c.text("DV01 by bucket", (bx0 + bx1) / 2, by1 + 6, 0.32, align="c")
    c.box_px("axis_labels", *lab)
    _footnote(c, tp)
    return {"metrics": metrics}


def _portfolio(c: Canvas, tp: dict, rv, _anomaly) -> dict:
    _header(c, tp)
    names = ["G-Sec", "T-Bill", "SDL", "Corp", "FX", "Cash"]
    k = int(rv.integers(3, 6))
    w = rv.dirichlet(np.ones(k) * 2.0)
    cols = (CURVE_DARK if c.theme["name"] == "dark" else CURVE_LIGHT) + [(150, 150, 150)]
    mode = tp["mode"]
    if mode == "pie":
        cx, cy, r = 150, 168, 92
        ang = -90.0
        for i in range(k):
            sweep = float(w[i] * 360)
            cv2.ellipse(c.img, (c._p(cx), c._p(cy)), (c._p(r), c._p(r)), 0, ang, ang + sweep, cols[i], -1, cv2.LINE_AA)
            cv2.ellipse(c.mask, (c._p(cx), c._p(cy)), (c._p(r), c._p(r)), 0, ang, ang + sweep, SEG_CURVE, -1)
            ang += sweep
        c.box("chart_region", cx - r, cy - r, cx + r, cy + r)
    else:
        rect, _, _ = _axes_frame(c, tp, rv, 0, 100, 25, [((i + 0.5) / k, names[i]) for i in range(k)])
        x0, y0, x1, y1 = rect
        bw = (x1 - x0) / k
        for i in range(k):
            hh = float(w[i]) * 100 / 100 * (y1 - y0) * 1.8
            hh = min(hh, y1 - y0 - 2)
            c.rect(x0 + i * bw + 5, y1 - hh, x0 + (i + 1) * bw - 5, y1 - 1, cols[i], -1, SEG_CURVE)
    if mode == "pie":
        lx0, ly0 = 290, 70
        lh = 10 + 18 * k
        c.rect(lx0, ly0, lx0 + 170, ly0 + lh, c.theme["panel"], -1, SEG_LEGEND)
        c.rect(lx0, ly0, lx0 + 170, ly0 + lh, c.theme["axis"], 1, SEG_LEGEND)
        for i in range(k):
            yy = ly0 + 6 + 18 * i
            c.rect(lx0 + 8, yy + 2, lx0 + 20, yy + 12, cols[i], -1, SEG_CURVE)
            c.text(f"{names[i]}  {w[i] * 100:.1f}%", lx0 + 28, yy, 0.36)
        c.box("legend", lx0, ly0, lx0 + 170, ly0 + lh)
    else:
        _legend(c, tp, (tp["ml"], tp["mt"], W - tp["mr"], H - tp["mb"]), names[:k], cols[:k])
    _footnote(c, tp)
    return {"weights": [float(x) for x in w]}


def _statement(c: Canvas, tp: dict, rv, _anomaly) -> dict:
    _header(c, tp, f"{tp['title']} (FY2025)")
    items = ["Net interest income", "Fee income", "Trading gains", "Operating expense", "Provisions", "Pre-tax profit", "Tax", "Net profit",
             "Total assets", "Total liabilities"]
    nr = min(tp["rows"], len(items))
    rows = [[items[i], f"{rv.uniform(100, 9000):,.0f}", f"{rv.uniform(100, 9000):,.0f}"] for i in range(nr)]
    _grid_table(c, tp, rv, 20, 40, W - 20, min(H - 34, 40 + 22 * (nr + 1)), ["Item (INR cr)", "FY24", "FY25"], rows, "ruled")
    _footnote(c, tp, "Figures are simulated for demonstration.")
    return {}


_BUILDERS = {
    "yield_curve": _yield_curve, "fx_line_chart": _fx_line, "candlestick_chart": _candles, "bond_table": _bond_table,
    "market_report": _market_report, "risk_dashboard": _risk_dashboard, "portfolio_chart": _portfolio, "financial_statement": _statement,
}


def degrade(img: np.ndarray, rv, strength: float = 1.0) -> np.ndarray:
    """Variant-level degradation: noise, blur, JPEG -- the 'screenshot capture' variability."""
    out = img.astype(np.float32)
    sigma = float(rv.uniform(0, 6)) * strength
    if sigma > 0.5:
        out += rv.normal(0, sigma, out.shape)
    out = np.clip(out, 0, 255).astype(np.uint8)
    if rv.random() < 0.3 * strength:
        out = cv2.GaussianBlur(out, (3, 3), 0.7)
    if rv.random() < 0.5 * strength:
        ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, int(rv.integers(55, 95))])
        if ok:
            out = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return out


def render(kind: str, template: int, variant: int = 0, scale: int = 1, anomaly: str | None = None, degrade_variant: bool = True) -> SynthDoc:
    if kind not in _BUILDERS:
        raise ValueError(f"unknown kind {kind}")
    tp = _template_params(kind, template)
    rv = np.random.default_rng(zlib.crc32(f"var:{kind}:{template}:{variant}:{anomaly}".encode()))
    c = Canvas(tp["theme"], scale)
    truth = _BUILDERS[kind](c, tp, rv, anomaly)
    img = c.img
    if degrade_variant and variant > 0:
        img = degrade(img, rv)
    return SynthDoc(image=img, mask=c.mask, boxes=c.boxes, kind=kind, template=template, variant=variant, scale=scale, truth=truth)


def iter_split(split: str, kinds: list[str] | None = None, variants: int = VARIANTS_PER_TEMPLATE, scale: int = 1):
    for kind in kinds or KINDS:
        for t in SPLITS[split]:
            for v in range(variants):
                yield render(kind, t, v, scale)


def dataset_manifest(variants: int = VARIANTS_PER_TEMPLATE) -> dict:
    per_split = {s: len(r) * variants * len(KINDS) for s, r in SPLITS.items()}
    return {
        "kinds": KINDS, "det_classes": DET_CLASSES, "seg_classes": SEG_CLASSES,
        "templates_per_kind": TEMPLATES_PER_KIND, "variants_per_template": variants,
        "split_templates": {s: [r.start, r.stop - 1] for s, r in SPLITS.items()},
        "images_per_split": per_split, "images_total": sum(per_split.values()),
        "class_distribution_per_split": {s: len(r) * variants for s, r in SPLITS.items()},
        "base_resolution": [W, H], "note": "Synthetic, procedurally generated. Splits are made by template; variants of a template never cross splits.",
    }
