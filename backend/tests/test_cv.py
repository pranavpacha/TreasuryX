"""
CV pipeline tests using synthetically generated chart-like images (clean, noisy,
low-resolution, and a "difficult" case with low contrast). No external test image
files are required, so the suite runs anywhere.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.cv_engine.edges import detect_chart_region, detect_edges, detect_lines
from app.cv_engine.pipeline import classify_chart_type, run_pipeline
from app.cv_engine.preprocessing import assess_image_quality, preprocess


def _make_chart_image(text_lines: list[str], size=(500, 800), noise: float = 0.0, low_res: bool = False) -> bytes:
    img = np.full((size[0], size[1], 3), 255, dtype=np.uint8)
    # axes
    cv2.line(img, (60, 40), (60, size[0] - 60), (0, 0, 0), 2)
    cv2.line(img, (60, size[0] - 60), (size[1] - 40, size[0] - 60), (0, 0, 0), 2)
    # a plotted line
    pts = np.array([[70 + i * 10, size[0] - 100 - (i * 3) % 200] for i in range(60)], dtype=np.int32)
    cv2.polylines(img, [pts], False, (30, 30, 200), 2)
    y = 30
    for line in text_lines:
        cv2.putText(img, line, (80, y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        y += 40
    if noise > 0:
        gauss = np.random.default_rng(0).normal(0, noise, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + gauss, 0, 255).astype(np.uint8)
    if low_res:
        img = cv2.resize(img, (size[1] // 4, size[0] // 4))
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_preprocess_produces_all_stages():
    img = np.zeros((200, 300, 3), dtype=np.uint8)
    stages = preprocess(img)
    assert set(stages.keys()) == {"original", "grayscale", "denoised", "normalized", "thresholded"}
    assert stages["grayscale"].ndim == 2


def test_edge_detection_finds_edges_on_synthetic_square():
    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), 255, -1)
    edges = detect_edges(img)
    assert edges.sum() > 0


def test_chart_region_detected_on_synthetic_chart():
    png = _make_chart_image(["USD/INR 83.45"])
    arr = np.frombuffer(png, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    region = detect_chart_region(gray)
    assert region is not None
    assert region.w > 0 and region.h > 0


def test_hough_lines_detected_on_axes():
    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.line(img, (10, 10), (10, 190), 255, 2)
    edges = detect_edges(img)
    lines = detect_lines(edges)
    assert isinstance(lines, list)


def test_classify_chart_type_yield_curve():
    assert classify_chart_type("10Y Yield Curve tenor maturity") == "yield_curve"


def test_classify_chart_type_fx():
    assert classify_chart_type("USD/INR spot chart") == "fx_chart"


def test_classify_chart_type_unknown_for_gibberish():
    assert classify_chart_type("qzx qzx qzx") == "unknown"


def test_pipeline_runs_end_to_end_on_clean_image():
    png = _make_chart_image(["USD/INR 83.45", "10Y 7.05%"])
    result = run_pipeline(png, "clean.png")
    assert "original" in result["stages"]
    assert result["chart_type"] in {"fx_chart", "yield_curve", "unknown"}
    assert isinstance(result["fields"], list)
    assert isinstance(result["warnings"], list)
    assert 0.0 <= result["mean_confidence"] <= 1.0


def test_pipeline_handles_noisy_image_without_crashing():
    png = _make_chart_image(["EUR/INR 90.12"], noise=35)
    result = run_pipeline(png, "noisy.png")
    assert "original" in result["stages"]


def test_pipeline_handles_low_resolution_image_without_crashing():
    png = _make_chart_image(["GBP/INR 105.4"], low_res=True)
    result = run_pipeline(png, "lowres.png")
    assert "original" in result["stages"]


def test_pipeline_handles_blank_difficult_image_with_warning():
    img = np.full((200, 300, 3), 250, dtype=np.uint8)  # near-blank, low-contrast
    ok, buf = cv2.imencode(".png", img)
    result = run_pipeline(buf.tobytes(), "blank.png")
    assert len(result["warnings"]) >= 1


def test_pipeline_rejects_corrupt_image():
    with pytest.raises(ValueError):
        run_pipeline(b"not an image", "bad.png")


def test_assess_image_quality_flags_low_resolution_blurry_low_contrast():
    # 40x30, near-uniform gray -- tiny, no edges (blurry by the Laplacian-variance measure),
    # and low contrast all at once.
    img = np.full((30, 40, 3), 200, dtype=np.uint8)
    quality = assess_image_quality(img)
    assert quality["verdict"] == "low"
    assert quality["width"] == 40 and quality["height"] == 30
    assert len(quality["reasons"]) >= 2  # resolution + contrast at minimum
    assert quality["recommendation"] is not None


def test_assess_image_quality_passes_sharp_high_contrast_image():
    png = _make_chart_image(["USD/INR 83.45", "10Y 7.05%"])
    arr = np.frombuffer(png, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    quality = assess_image_quality(img)
    assert quality["verdict"] == "ok"
    assert quality["reasons"] == []
    assert quality["recommendation"] is None


def test_pipeline_includes_image_quality_for_low_res_image():
    png = _make_chart_image(["GBP/INR 105.4"], low_res=True)
    result = run_pipeline(png, "lowres.png")
    assert result["image_quality"]["verdict"] == "low"
    assert any("resolution" in r.lower() for r in result["image_quality"]["reasons"])
