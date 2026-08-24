"""Tests for the new Computer Vision Lab modules (filters, edges, SIFT, segmentation,
corners/blobs, optical flow) -- classical CV techniques from CS4231."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.cv_engine.edges_lab import (
    canny_adjustable, difference_of_gaussians, laplacian_edges, laplacian_of_gaussian, sobel_edges,
)
from app.cv_engine.features_lab import blob_detection, harris_corners
from app.cv_engine.filters_lab import compare_filters
from app.cv_engine.optical_flow_lab import dense_optical_flow, synthetic_shift
from app.cv_engine.segmentation_lab import iou_dice, run_benchmark, segment_region, synthetic_ground_truth_sample
from app.cv_engine.sift_lab import run_sift_matching


def _test_image(size=(200, 200)) -> np.ndarray:
    img = np.full((*size, 3), 240, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (180, 180), (255, 255, 255), -1)
    cv2.rectangle(img, (20, 20), (180, 180), (10, 10, 10), 2)
    pts = np.array([[30 + i * 5, 150 - (i * 4) % 100] for i in range(30)], np.int32)
    cv2.polylines(img, [pts], False, (200, 30, 30), 2)
    return img


def _gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def test_filters_produce_all_variants():
    gray = _gray(_test_image())
    result = compare_filters(gray)
    assert set(result.keys()) == {"original", "gaussian", "median", "bilateral", "clahe"}
    for img in result.values():
        assert img.shape == gray.shape


def test_filters_gaussian_smooths_noise():
    rng = np.random.default_rng(0)
    gray = _gray(_test_image())
    noisy = np.clip(gray.astype(np.float32) + rng.normal(0, 25, gray.shape), 0, 255).astype(np.uint8)
    result = compare_filters(noisy)
    # Smoothed image should have lower local variance than the noisy input
    assert np.std(result["gaussian"].astype(np.float32)) <= np.std(noisy.astype(np.float32))


def test_sobel_edges_detect_rectangle_boundary():
    gray = _gray(_test_image())
    result = sobel_edges(gray)
    assert result["gradient_magnitude"].max() > 0
    assert result["sobel_x"].shape == gray.shape


def test_laplacian_nonzero_on_edges():
    gray = _gray(_test_image())
    assert laplacian_edges(gray).max() > 0


def test_dog_and_log_run_without_error():
    gray = _gray(_test_image())
    dog = difference_of_gaussians(gray)
    log = laplacian_of_gaussian(gray)
    assert dog.shape == gray.shape
    assert log.shape == gray.shape


def test_canny_adjustable_thresholds_change_output():
    gray = _gray(_test_image())
    strict = canny_adjustable(gray, low=200, high=250)
    loose = canny_adjustable(gray, low=10, high=50)
    # A looser threshold should never detect fewer edge pixels than a stricter one
    assert loose.sum() >= strict.sum()


def test_harris_corners_finds_rectangle_corners():
    gray = _gray(_test_image())
    result = harris_corners(gray)
    assert result["n_corners"] > 0


def test_blob_detection_runs():
    gray = _gray(_test_image())
    result = blob_detection(gray)
    assert "overlay" in result
    assert result["n_blobs"] >= 0


def test_sift_matching_self_similarity():
    img = _test_image()
    gray_a = _gray(img)
    gray_b = _gray(img)  # identical image -> should match itself very well
    out = run_sift_matching(gray_a, gray_b)
    assert out["result"]["n_keypoints_a"] > 0
    assert out["result"]["n_good_matches"] > 0
    # Self-matching should recover at least some unambiguous matches; a synthetic image with
    # repetitive structure (straight edges/corners) legitimately produces some ambiguous
    # descriptors that Lowe's ratio test correctly rejects, so this is a loose sanity bound.
    assert out["result"]["n_good_matches"] >= out["result"]["n_keypoints_a"] * 0.2
    assert out["result"]["n_good_matches"] <= out["result"]["n_keypoints_a"]


def test_sift_matching_handles_no_keypoints_gracefully():
    blank_a = np.full((100, 100), 128, dtype=np.uint8)
    blank_b = np.full((100, 100), 128, dtype=np.uint8)
    out = run_sift_matching(blank_a, blank_b)
    assert out["result"]["n_keypoints_a"] == 0
    assert out["result"]["n_good_matches"] == 0


def test_segmentation_returns_expected_shapes():
    img = _test_image()
    result = segment_region(img)
    assert result["mask"].shape == img.shape[:2]
    assert result["overlay"].shape == img.shape


def test_iou_dice_identical_masks_is_one():
    mask = np.zeros((50, 50), np.uint8)
    mask[10:40, 10:40] = 255
    iou, dice = iou_dice(mask, mask)
    assert iou == pytest.approx(1.0)
    assert dice == pytest.approx(1.0)


def test_iou_dice_disjoint_masks_is_zero():
    a = np.zeros((50, 50), np.uint8)
    a[0:10, 0:10] = 255
    b = np.zeros((50, 50), np.uint8)
    b[40:50, 40:50] = 255
    iou, dice = iou_dice(a, b)
    assert iou == pytest.approx(0.0)
    assert dice == pytest.approx(0.0)


def test_synthetic_ground_truth_sample_has_valid_rect():
    rng = np.random.default_rng(1)
    img, mask, rect = synthetic_ground_truth_sample(rng)
    x, y, w, h = rect
    assert w > 0 and h > 0
    assert mask.sum() > 0
    assert mask[y + h // 2, x + w // 2] == 255  # center of rect is foreground


def test_segmentation_benchmark_produces_reasonable_iou():
    result = run_benchmark(n_samples=5)
    assert result["n_samples"] == 5
    assert 0.0 <= result["mean_iou"] <= 1.0
    assert 0.0 <= result["mean_dice"] <= 1.0


def test_optical_flow_zero_motion_gives_near_zero_magnitude():
    gray = _gray(_test_image())
    out = dense_optical_flow(gray, gray)
    assert out["mean_magnitude"] == pytest.approx(0.0, abs=0.5)


def test_optical_flow_detects_translation():
    gray = _gray(_test_image())
    shifted = synthetic_shift(gray, dx=6, dy=3)
    out = dense_optical_flow(gray, shifted)
    assert out["mean_magnitude"] > 0.5


def test_synthetic_shift_changes_image():
    gray = _gray(_test_image())
    shifted = synthetic_shift(gray)
    assert not np.array_equal(gray, shifted)
