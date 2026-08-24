"""
SIFT (Scale-Invariant Feature Transform) lab -- CS4231 Module 2 lab requirement
"Implement Feature extraction using SIFT."

Real-world Treasury use case: identifying a repeated chart template/watermark across
report screenshots, or measuring visual similarity between two chart images (e.g. "is this
the same broker's chart layout as last week's?") -- NOT a market predictor.
"""
from __future__ import annotations

import cv2
import numpy as np


def run_sift_matching(gray_a: np.ndarray, gray_b: np.ndarray, ratio_thresh: float = 0.75) -> dict:
    sift = cv2.SIFT_create()
    kp_a, desc_a = sift.detectAndCompute(gray_a, None)
    kp_b, desc_b = sift.detectAndCompute(gray_b, None)

    result = {
        "n_keypoints_a": len(kp_a),
        "n_keypoints_b": len(kp_b),
        "n_descriptors_a": 0 if desc_a is None else desc_a.shape[0],
        "n_descriptors_b": 0 if desc_b is None else desc_b.shape[0],
        "n_matches_raw": 0,
        "n_good_matches": 0,
        "match_ratio_threshold": ratio_thresh,
    }

    kp_img_a = cv2.drawKeypoints(gray_a, kp_a, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    kp_img_b = cv2.drawKeypoints(gray_b, kp_b, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    match_img = None
    if desc_a is not None and desc_b is not None and len(kp_a) >= 2 and len(kp_b) >= 2:
        bf = cv2.BFMatcher()
        raw_matches = bf.knnMatch(desc_a, desc_b, k=2)
        result["n_matches_raw"] = len(raw_matches)
        good = [m for m, n in raw_matches if m.distance < ratio_thresh * n.distance]
        result["n_good_matches"] = len(good)
        good_sorted = sorted(good, key=lambda m: m.distance)[:40]
        match_img = cv2.drawMatches(
            gray_a, kp_a, gray_b, kp_b, good_sorted, None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
        )

    return {"result": result, "keypoints_a": kp_img_a, "keypoints_b": kp_img_b, "matches": match_img}
