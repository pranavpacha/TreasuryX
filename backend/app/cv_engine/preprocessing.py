"""
Stage 1 -- Preprocessing.

resize -> grayscale -> denoise (fastNlMeansDenoising) -> normalize (CLAHE contrast
normalization) -> adaptive threshold. Each intermediate is kept so the UI can show
the professor an actual before/after pipeline (section 21 of the spec).
"""
from __future__ import annotations

import base64

import cv2
import numpy as np

MAX_DIM = 1400


def to_base64_png(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Failed to encode image")
    return "data:image/png;base64," + base64.b64encode(buf).decode("ascii")


def resize_keep_aspect(img: np.ndarray, max_dim: int = MAX_DIM) -> np.ndarray:
    h, w = img.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def preprocess(img_bgr: np.ndarray) -> dict[str, np.ndarray]:
    """Returns a dict of named intermediate images for the CV pipeline viewer."""
    resized = resize_keep_aspect(img_bgr)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    normalized = clahe.apply(denoised)
    thresh = cv2.adaptiveThreshold(
        normalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10,
    )
    return {
        "original": resized,
        "grayscale": gray,
        "denoised": denoised,
        "normalized": normalized,
        "thresholded": thresh,
    }
