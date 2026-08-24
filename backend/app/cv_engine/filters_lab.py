"""Filter comparison lab: Gaussian, median, bilateral, CLAHE side by side."""
from __future__ import annotations

import cv2
import numpy as np


def compare_filters(gray: np.ndarray, kernel_size: int = 5, sigma: float = 1.5) -> dict[str, np.ndarray]:
    k = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    gaussian = cv2.GaussianBlur(gray, (k, k), sigmaX=sigma)
    median = cv2.medianBlur(gray, k)
    bilateral = cv2.bilateralFilter(gray, d=k, sigmaColor=75, sigmaSpace=75)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    return {"original": gray, "gaussian": gaussian, "median": median, "bilateral": bilateral, "clahe": clahe}


FILTER_NOTES = {
    "gaussian": "Weighted average using a Gaussian kernel -- smooths noise but blurs edges. "
                "Preserves overall structure, destroys fine detail.",
    "median": "Replaces each pixel with the median of its neighborhood -- excellent at removing "
              "salt-and-pepper noise while preserving edges better than Gaussian blur.",
    "bilateral": "Smooths flat regions while preserving edges by weighting neighbors by both spatial "
                "distance AND intensity similarity -- slower, but best edge preservation.",
    "clahe": "Contrast Limited Adaptive Histogram Equalization -- boosts local contrast in low-light "
            "or washed-out regions of a chart screenshot, improving downstream OCR/edge detection.",
}
