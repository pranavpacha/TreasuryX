"""
Stage 2 -- Structural / feature processing.

Canny edge detection + Hough line detection to find candidate chart axes (long
near-horizontal / near-vertical lines), and contour detection to find the largest
rectangular region (the plotted chart area / table region).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class DetectedRegion:
    x: int
    y: int
    w: int
    h: int
    kind: str  # "chart_area" | "axis_line"


def detect_edges(gray: np.ndarray) -> np.ndarray:
    return cv2.Canny(gray, threshold1=50, threshold2=150)


def detect_lines(edges: np.ndarray) -> list[tuple[int, int, int, int]]:
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=60, maxLineGap=10)
    if lines is None:
        return []
    return [tuple(int(v) for v in line[0]) for line in lines]


def detect_chart_region(gray: np.ndarray) -> DetectedRegion | None:
    """Largest bounding rectangle from contours on the thresholded image --
    a reasonable proxy for the main plotted/table region in a screenshot."""
    edges = detect_edges(gray)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    h_img, w_img = gray.shape[:2]
    best = None
    best_area = 0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        # Ignore tiny noise regions and the whole-image bounding box
        if area > best_area and area < 0.98 * h_img * w_img and w > 40 and h > 40:
            best_area = area
            best = DetectedRegion(x=x, y=y, w=w, h=h, kind="chart_area")
    return best


def draw_regions(img_bgr: np.ndarray, regions: list[DetectedRegion], lines: list[tuple[int, int, int, int]]) -> np.ndarray:
    out = img_bgr.copy()
    for x1, y1, x2, y2 in lines:
        cv2.line(out, (x1, y1), (x2, y2), (0, 165, 255), 1)
    for r in regions:
        cv2.rectangle(out, (r.x, r.y), (r.x + r.w, r.y + r.h), (0, 220, 0), 2)
    return out
