"""
Edge-detection lab: Sobel X/Y, gradient magnitude, Laplacian, DoG, LoG, and Canny with
user-adjustable thresholds -- covers CS4231 Module 2 ("Edge Detection ... Blobs, Corner
Detection; Scale Space") lab requirement "Implement Edge detection using DoG, LoG, Canny
and Hough Transform."
"""
from __future__ import annotations

import cv2
import numpy as np


def sobel_edges(gray: np.ndarray) -> dict[str, np.ndarray]:
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sx ** 2 + sy ** 2)
    magnitude = np.clip(magnitude / (magnitude.max() + 1e-6) * 255, 0, 255).astype(np.uint8)
    sx_disp = np.clip(np.abs(sx) / (np.abs(sx).max() + 1e-6) * 255, 0, 255).astype(np.uint8)
    sy_disp = np.clip(np.abs(sy) / (np.abs(sy).max() + 1e-6) * 255, 0, 255).astype(np.uint8)
    return {"sobel_x": sx_disp, "sobel_y": sy_disp, "gradient_magnitude": magnitude}


def laplacian_edges(gray: np.ndarray) -> np.ndarray:
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    return np.clip(np.abs(lap) / (np.abs(lap).max() + 1e-6) * 255, 0, 255).astype(np.uint8)


def difference_of_gaussians(gray: np.ndarray, sigma1: float = 1.0, sigma2: float = 2.0) -> np.ndarray:
    """DoG approximates the Laplacian of Gaussian (LoG) and is used for blob/edge detection
    at a chosen scale -- the difference of two Gaussian-smoothed copies of the image."""
    g1 = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma1)
    g2 = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma2)
    dog = g1.astype(np.float32) - g2.astype(np.float32)
    dog = np.clip((dog - dog.min()) / (dog.max() - dog.min() + 1e-6) * 255, 0, 255).astype(np.uint8)
    return dog


def laplacian_of_gaussian(gray: np.ndarray, sigma: float = 1.4) -> np.ndarray:
    """LoG = Gaussian smoothing (to suppress noise) followed by the Laplacian operator
    (to find zero-crossings, i.e. edges) -- a single-scale edge/blob detector."""
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma)
    log = cv2.Laplacian(blurred, cv2.CV_64F, ksize=3)
    return np.clip(np.abs(log) / (np.abs(log).max() + 1e-6) * 255, 0, 255).astype(np.uint8)


def canny_adjustable(gray: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    return cv2.Canny(gray, threshold1=low, threshold2=high)
