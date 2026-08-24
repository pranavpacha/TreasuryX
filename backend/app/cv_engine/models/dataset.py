"""
Synthetic financial-chart-image dataset generator.

Why synthetic: a real labeled dataset of FX/yield/bar/table financial screenshots doesn't
exist for this project and scraping one would be both impractical and legally murky. Instead
we generate a small, clearly-labeled-as-synthetic dataset with real structural variation
(line noise, marker jitter, color/position randomization) so the CNN/ViT experiments below
produce genuine (if small-scale) learned classifiers and honest metrics -- not fabricated
numbers. This mirrors the course's own CNN-for-recognition labs at a scale that fits a laptop.

Classes: fx_line_chart, yield_curve_chart, bar_chart, table_report
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

IMG_SIZE = 64
CLASSES = ["fx_line_chart", "yield_curve_chart", "bar_chart", "table_report"]


@dataclass
class Sample:
    image: np.ndarray  # HxWx3 uint8
    label: int


def _blank(rng: np.random.Generator) -> np.ndarray:
    bg = int(rng.integers(245, 256))
    return np.full((IMG_SIZE, IMG_SIZE, 3), bg, dtype=np.uint8)


def _gen_fx_line_chart(rng: np.random.Generator) -> np.ndarray:
    img = _blank(rng)
    n = 20
    x = np.linspace(6, IMG_SIZE - 6, n)
    y = IMG_SIZE / 2 + np.cumsum(rng.normal(0, 2.2, n))
    y = np.clip(y, 8, IMG_SIZE - 8)
    pts = np.stack([x, y], axis=1).astype(np.int32)
    color = (int(rng.integers(0, 80)), int(rng.integers(0, 80)), int(rng.integers(150, 230)))
    cv2.polylines(img, [pts], False, color, 1, cv2.LINE_AA)
    cv2.line(img, (4, IMG_SIZE - 4), (IMG_SIZE - 4, IMG_SIZE - 4), (60, 60, 60), 1)
    cv2.line(img, (4, 4), (4, IMG_SIZE - 4), (60, 60, 60), 1)
    return img


def _gen_yield_curve_chart(rng: np.random.Generator) -> np.ndarray:
    img = _blank(rng)
    n = 8
    x = np.linspace(8, IMG_SIZE - 8, n)
    base = rng.uniform(20, 44)
    slope = rng.uniform(0.5, 3.0)
    y = base - slope * np.log1p(np.arange(n)) + rng.normal(0, 1.0, n)
    y = np.clip(y, 6, IMG_SIZE - 10)
    pts = np.stack([x, y], axis=1).astype(np.int32)
    color = (int(rng.integers(0, 80)), int(rng.integers(140, 210)), int(rng.integers(0, 80)))
    cv2.polylines(img, [pts], False, color, 1, cv2.LINE_AA)
    for p in pts:
        cv2.circle(img, tuple(p), 1, color, -1)
    cv2.line(img, (4, IMG_SIZE - 4), (IMG_SIZE - 4, IMG_SIZE - 4), (60, 60, 60), 1)
    cv2.line(img, (4, 4), (4, IMG_SIZE - 4), (60, 60, 60), 1)
    return img


def _gen_bar_chart(rng: np.random.Generator) -> np.ndarray:
    img = _blank(rng)
    n = int(rng.integers(5, 9))
    width = (IMG_SIZE - 12) // n
    base_y = IMG_SIZE - 6
    for i in range(n):
        h = int(rng.integers(6, IMG_SIZE - 16))
        x0 = 6 + i * width
        x1 = x0 + max(2, width - 3)
        color = (int(rng.integers(150, 230)), int(rng.integers(0, 80)), int(rng.integers(0, 80)))
        cv2.rectangle(img, (x0, base_y - h), (x1, base_y), color, -1)
    cv2.line(img, (4, base_y), (IMG_SIZE - 4, base_y), (60, 60, 60), 1)
    return img


def _gen_table_report(rng: np.random.Generator) -> np.ndarray:
    img = _blank(rng)
    rows = int(rng.integers(4, 7))
    cols = int(rng.integers(2, 4))
    x0, y0, x1, y1 = 6, 6, IMG_SIZE - 6, IMG_SIZE - 6
    for r in range(rows + 1):
        y = int(y0 + r * (y1 - y0) / rows)
        cv2.line(img, (x0, y), (x1, y), (90, 90, 90), 1)
    for c in range(cols + 1):
        x = int(x0 + c * (x1 - x0) / cols)
        cv2.line(img, (x, y0), (x, y1), (90, 90, 90), 1)
    # a few filled "text" cells
    for _ in range(int(rng.integers(3, 8))):
        r, c = int(rng.integers(0, rows)), int(rng.integers(0, cols))
        cx0 = int(x0 + c * (x1 - x0) / cols) + 2
        cy0 = int(y0 + r * (y1 - y0) / rows) + 2
        cx1 = int(x0 + (c + 1) * (x1 - x0) / cols) - 2
        cy1 = cy0 + 2
        cv2.rectangle(img, (cx0, cy0), (max(cx0 + 1, cx1), cy1), (40, 40, 40), -1)
    return img


_GENERATORS = {
    "fx_line_chart": _gen_fx_line_chart,
    "yield_curve_chart": _gen_yield_curve_chart,
    "bar_chart": _gen_bar_chart,
    "table_report": _gen_table_report,
}


def generate_dataset(n_per_class: int = 120, seed: int = 20260101, noise_std: float = 6.0) -> list[Sample]:
    rng = np.random.default_rng(seed)
    samples: list[Sample] = []
    for label, cls in enumerate(CLASSES):
        gen = _GENERATORS[cls]
        for _ in range(n_per_class):
            img = gen(rng)
            if noise_std > 0:
                noise = rng.normal(0, noise_std, img.shape)
                img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
            samples.append(Sample(image=img, label=label))
    rng.shuffle(samples)  # type: ignore[arg-type]
    return samples


def split_dataset(samples: list[Sample], train_frac=0.7, val_frac=0.15):
    n = len(samples)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    return samples[:n_train], samples[n_train:n_train + n_val], samples[n_train + n_val:]
