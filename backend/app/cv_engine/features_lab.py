"""Corner and blob detection -- CS4231 Module 2: "Blobs, Corner Detection; Scale Space and
Scale Selection." Corners are useful for locating chart-axis intersections/gridline crossings;
blobs for locating markers/legend swatches on a financial chart."""
from __future__ import annotations

import cv2
import numpy as np


def harris_corners(gray: np.ndarray, block_size: int = 2, ksize: int = 3, k: float = 0.04, thresh_ratio: float = 0.01) -> dict:
    gray_f = np.float32(gray)
    dst = cv2.cornerHarris(gray_f, block_size, ksize, k)
    dst = cv2.dilate(dst, None)
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    threshold = thresh_ratio * dst.max()
    ys, xs = np.where(dst > threshold)
    overlay[dst > threshold] = (0, 0, 255)
    return {"overlay": overlay, "n_corners": int(len(xs)), "response_map": np.clip(dst / (dst.max() + 1e-6) * 255, 0, 255).astype(np.uint8)}


def blob_detection(gray: np.ndarray) -> dict:
    params = cv2.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 8
    params.maxArea = 5000
    params.filterByCircularity = False
    params.filterByConvexity = False
    params.filterByInertia = False
    detector = cv2.SimpleBlobDetector_create(params)
    keypoints = detector.detect(255 - gray)  # blobs are typically dark-on-light in chart markers
    overlay = cv2.drawKeypoints(
        gray, keypoints, None, (0, 0, 255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
    )
    return {"overlay": overlay, "n_blobs": len(keypoints)}
