"""Dense optical flow (Farneback) -- CS4231 Module 2: "Optical Flow." Treasury framing:
tracking motion between two chart snapshots (e.g. a live-updating chart) is structurally the
same problem as tracking a moving object between video frames; shown here on two uploaded
frames (or one frame synthetically shifted, if only one image is provided) for demonstration."""
from __future__ import annotations

import cv2
import numpy as np


def dense_optical_flow(gray_a: np.ndarray, gray_b: np.ndarray) -> dict:
    flow = cv2.calcOpticalFlowFarneback(gray_a, gray_b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    hsv = np.zeros((*gray_a.shape, 3), dtype=np.uint8)
    hsv[..., 1] = 255
    hsv[..., 0] = angle * 180 / np.pi / 2
    hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
    flow_rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    step = 12
    overlay = cv2.cvtColor(gray_b, cv2.COLOR_GRAY2BGR)
    h, w = gray_a.shape
    for y in range(step // 2, h, step):
        for x in range(step // 2, w, step):
            dx, dy = flow[y, x]
            cv2.arrowedLine(overlay, (x, y), (int(x + dx), int(y + dy)), (0, 255, 0), 1, tipLength=0.4)

    return {
        "flow_field_color": flow_rgb,
        "vector_overlay": overlay,
        "mean_magnitude": float(np.mean(magnitude)),
        "max_magnitude": float(np.max(magnitude)),
    }


def synthetic_shift(gray: np.ndarray, dx: int = 6, dy: int = 3) -> np.ndarray:
    """Used when the user uploads only one image -- produces a second frame by translating
    the first, so optical flow has a genuine (if synthetic) motion field to recover."""
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(gray, m, (gray.shape[1], gray.shape[0]), borderMode=cv2.BORDER_REPLICATE)
