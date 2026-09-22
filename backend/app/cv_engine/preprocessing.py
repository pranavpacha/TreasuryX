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



# Heuristic thresholds for image-quality gating, applied to the ORIGINAL (pre-resize)
# image so a large image downscaled by resize_keep_aspect doesn't get penalized for its
# post-resize dimensions. Blur is the variance of the Laplacian -- a standard, widely-cited
# focus measure (low variance = few sharp edges = likely blurry); the exact threshold is
# image-content-dependent, so this is a heuristic flag for the user, not a hard rejection.
MIN_DIM_OK = 200
BLUR_VARIANCE_LOW = 50.0
CONTRAST_STD_LOW = 20.0


def assess_image_quality(img_bgr: np.ndarray) -> dict:
    """Real, computed quality indicators (not fabricated) -- resolution, a Laplacian-variance
    blur estimate, and grayscale contrast (std-dev) -- surfaced to the user before they spend
    time reviewing extraction results from an image that was never going to OCR well."""
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if img_bgr.ndim == 3 else img_bgr
    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast_std = float(gray.std())

    reasons: list[str] = []
    if min(h, w) < MIN_DIM_OK:
        reasons.append(f"Low resolution ({w}x{h}px, smaller side under {MIN_DIM_OK}px).")
    if blur_variance < BLUR_VARIANCE_LOW:
        reasons.append(f"Image appears blurry (edge-sharpness score {blur_variance:.1f}, below {BLUR_VARIANCE_LOW:.0f}).")
    if contrast_std < CONTRAST_STD_LOW:
        reasons.append(f"Low contrast (intensity std-dev {contrast_std:.1f}, below {CONTRAST_STD_LOW:.0f}).")

    return {
        "width": w,
        "height": h,
        "blur_variance": round(blur_variance, 1),
        "contrast_std": round(contrast_std, 1),
        "verdict": "low" if reasons else "ok",
        "reasons": reasons,
        "recommendation": "Upload a higher-resolution, well-lit, in-focus screenshot for more reliable extraction." if reasons else None,
    }


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
