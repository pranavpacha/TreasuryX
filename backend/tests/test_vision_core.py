"""Classical-CV vision modules: synthetic dataset integrity, quality analyzer, chart digitizer,
screenshot comparison, visual anomaly detector, optical flow. Ground truth comes from the generator,
never from the code under test."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.cv_engine.vision import anomaly, compare, digitize, flow, quality, synth, video
from tests.vision_helpers import needs_ocr


# ------------------------------------------------------------------ synthetic dataset
def test_splits_are_disjoint_by_template():
    sets = {s: set(r) for s, r in synth.SPLITS.items()}
    assert not (sets["train"] & sets["val"]) and not (sets["train"] & sets["test"]) and not (sets["val"] & sets["test"])
    assert max(sets["test"]) == synth.TEMPLATES_PER_KIND - 1


def test_render_is_deterministic_and_variants_differ():
    a, b = synth.render("yield_curve", 3, 1), synth.render("yield_curve", 3, 1)
    assert np.array_equal(a.image, b.image) and a.boxes == b.boxes
    assert not np.array_equal(synth.render("yield_curve", 3, 1).image, synth.render("yield_curve", 3, 2).image)


@pytest.mark.parametrize("kind", synth.KINDS)
def test_annotations_are_valid_for_every_kind(kind):
    d = synth.render(kind, 25, 0)
    h, w = d.image.shape[:2]
    assert d.boxes, "every document kind must carry at least one detection box"
    for cls, x, y, bw, bh in d.boxes:
        assert 0 <= cls < len(synth.DET_CLASSES) and bw > 3 and bh > 3 and x >= 0 and y >= 0 and x + bw <= w and y + bh <= h
    assert d.mask.shape == (h, w) and d.mask.max() < len(synth.SEG_CLASSES)
    assert (d.mask > 0).any()


def test_dataset_manifest_counts_add_up():
    m = synth.dataset_manifest()
    assert m["images_total"] == sum(m["images_per_split"].values()) == len(synth.KINDS) * synth.TEMPLATES_PER_KIND * synth.VARIANTS_PER_TEMPLATE


# ------------------------------------------------------------------ quality (feature 5)
@pytest.fixture(scope="module")
def table_img():
    return synth.render("bond_table", 26, 0, scale=2).image


def test_quality_detects_blur_noise_lowcontrast_and_skew(table_img):
    clean = quality.measure(table_img)
    blurred = quality.measure(cv2.GaussianBlur(table_img, (0, 0), 3))
    assert blurred["blur_laplacian_var"] < 0.2 * clean["blur_laplacian_var"]
    noisy = (table_img.astype(np.float32) + np.random.default_rng(0).normal(0, 15, table_img.shape)).clip(0, 255).astype(np.uint8)
    assert quality.measure(noisy)["noise_sigma"] > 5 * clean["noise_sigma"]
    flat = (table_img.astype(np.float32) * 0.15 + 120).astype(np.uint8)
    assert quality.assess(flat)["checks"][3]["status"] in ("warn", "poor") and quality.measure(flat)["contrast_std"] < 15
    h, w = table_img.shape[:2]
    rot = cv2.warpAffine(table_img, cv2.getRotationMatrix2D((w / 2, h / 2), 4.0, 1.0), (w, h), borderValue=(255, 255, 255))
    assert quality.measure(rot)["skew_deg"] == pytest.approx(4.0, abs=0.75)
    assert abs(clean["skew_deg"]) < 0.6


def test_quality_detects_90_degree_rotation(table_img):
    assert quality.measure(cv2.rotate(table_img, cv2.ROTATE_90_CLOCKWISE))["rotated_90"] is True
    assert quality.measure(table_img)["rotated_90"] is False


def test_quality_enhancement_is_re_measured_and_improves_skew(table_img):
    h, w = table_img.shape[:2]
    rot = cv2.warpAffine(table_img, cv2.getRotationMatrix2D((w / 2, h / 2), 4.0, 1.0), (w, h), borderValue=(255, 255, 255))
    r = quality.analyze(rot, with_ocr=False)
    assert "deskew" in r["applied_operations"]
    assert abs(r["after"]["measurements"]["skew_deg"]) < abs(r["before"]["measurements"]["skew_deg"])
    assert r["images"]["before"].startswith("data:image/png") and r["images"]["after"].startswith("data:image/png")


def test_quality_flags_low_resolution():
    tiny = cv2.resize(synth.render("bond_table", 26, 0).image, (120, 80))
    st = {c["check"]: c["status"] for c in quality.assess(tiny)["checks"]}
    assert st["resolution"] == "poor"
    assert any(r["op"] == "upscale" for r in quality.assess(tiny)["recommendations"])


# ------------------------------------------------------------------ digitization (feature 1)
@needs_ocr
@pytest.mark.parametrize("tpl", [25, 26, 27])
def test_yield_curve_digitization_matches_ground_truth(tpl):
    d = synth.render("yield_curve", tpl, 1, scale=2)
    r = digitize.digitize(d.image)
    assert r["chart_kind"] == "yield_curve" and r["calibration"]["y"]["source"] == "ocr"
    got = {p["tenor"]: p for p in r["series"][0]["points"] if "tenor" in p}
    truth = {p["x_label"]: p["value"] for p in d.truth["points"]}
    assert set(got) == set(truth), "every plotted tenor must be recovered and labelled"
    res = r["resolution"]["value_per_pixel_y"]
    for t, v in truth.items():
        err = abs(got[t]["y_value"] - v)
        assert err <= 2 * res, f"{t}: error {err} exceeds 2 pixels of resolution ({res})"
        assert got[t]["y_uncertainty"] > 0


@needs_ocr
def test_fx_series_digitization_within_stated_uncertainty():
    d = synth.render("fx_line_chart", 28, 2, scale=2)
    r = digitize.digitize(d.image)
    pts = [p for p in r["series"][0]["points"] if "y_value" in p and not p.get("steep_segment")]
    tx = np.array([p["x_px"] for p in d.truth["points"]])
    ty = np.array([p["value"] for p in d.truth["points"]])
    errs = np.array([abs(p["y_value"] - np.interp(p["x_px"], tx, ty)) for p in pts])
    unc = np.array([p["y_uncertainty"] for p in pts])
    assert np.mean(errs <= unc) > 0.9, "stated uncertainty must cover the true value for >90% of points"
    assert 0 < r["confidence"] <= 1 and "NOT a calibrated probability" in r["confidence_note"]


def test_manual_calibration_maps_pixels_linearly():
    d = synth.render("fx_line_chart", 26, 1, scale=2)
    x0, y0, x1, y1 = d.truth["plot_rect_px"]
    lo, hi = d.truth["y_range"]
    r = digitize.digitize(d.image, {"y_top_value": hi, "y_bottom_value": lo})
    assert r["calibration"]["y"]["source"] == "manual"
    s = r["series"][0]["points"]
    tx = np.array([p["x_px"] for p in d.truth["points"]])
    ty = np.array([p["value"] for p in d.truth["points"]])
    errs = [abs(p["y_value"] - np.interp(p["x_px"], tx, ty)) for p in s if not p.get("steep_segment")]
    assert np.median(errs) < 0.01 * (hi - lo)


def test_no_values_invented_without_calibration(monkeypatch):
    """With OCR unavailable and no manual calibration the digitizer must return NO numbers, only plot-normalised coordinates."""
    monkeypatch.setattr(digitize.ocr_mod, "_TESSERACT_IMPORT_OK", False)
    r = digitize.digitize(synth.render("fx_line_chart", 26, 1, scale=2).image)
    pts = r["series"][0]["points"]
    assert pts and all("y_value" not in p and "y_fraction" in p for p in pts)
    assert r["calibration"]["y"]["source"] is None and any("No y-axis calibration" in l for l in r["limitations"])


def test_bar_chart_and_candlestick_are_rejected_as_not_line_charts():
    for kind in ("candlestick_chart", "portfolio_chart"):
        r = digitize.digitize(synth.render(kind, 26, 0, scale=2).image)
        assert r["series"] == [] or r["chart_kind"] in ("candlestick_or_bars", "unknown", "line_chart")
    assert digitize.digitize(synth.render("candlestick_chart", 26, 0, scale=2).image)["chart_kind"] == "candlestick_or_bars"


def test_digitize_csv_export_has_one_row_per_point():
    r = digitize.digitize(synth.render("fx_line_chart", 26, 1, scale=2).image, {"y_top_value": 1.0, "y_bottom_value": 0.0})
    assert len(digitize.to_csv(r).splitlines()) == 1 + sum(s["n_points"] for s in r["series"])


# ------------------------------------------------------------------ comparison (feature 4)
@needs_ocr
def test_compare_separates_value_change_from_layout_shift():
    a, b = video._terminal_frame(1.0), video._terminal_frame(4.0)    # 10Y 6.85 -> 7.02
    r = compare.compare(a, b)
    assert r["verdict"] == "value_change"
    vc = {v["instrument"]: v for v in r["value_changes"]}
    assert vc["10Y"]["value_a"] == 6.85 and vc["10Y"]["value_b"] == 7.02 and vc["10Y"]["delta_bps"] == pytest.approx(17.0)
    assert any(x["kind"] == "value_change" for x in r["regions"])
    # same content, shifted: must be a LAYOUT change with no value change
    M = np.float32([[1, 0, 14], [0, 1, 9]])
    shifted = cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), borderValue=(22, 18, 14))
    r2 = compare.compare(a, shifted)
    assert r2["verdict"] == "layout_change" and r2["value_changes"] == []
    assert r2["layout"]["transform"]["translation_px"] == pytest.approx([-14, -9], abs=1.5)


def test_compare_identical_images():
    a = video._terminal_frame(1.0)
    r = compare.compare(a, a.copy(), with_ocr=False)
    assert r["verdict"] == "identical" and r["mean_ssim"] > 0.99 and r["regions"] == []


def test_ssim_properties():
    g = cv2.cvtColor(synth.render("bond_table", 26, 0).image, cv2.COLOR_BGR2GRAY)
    assert compare.ssim_map(g, g).min() == pytest.approx(1.0, abs=1e-6)
    assert compare.ssim_map(g, 255 - g).mean() < 0.5


# ------------------------------------------------------------------ anomaly (feature 6)
@pytest.mark.parametrize("ak,expected", [("gap", {"gap"}), ("spike", {"spike"})])
def test_injected_anomalies_are_found_and_clean_charts_are_not(ak, expected):
    for kind in ("fx_line_chart", "yield_curve"):
        found = {a["kind"] for a in anomaly.analyze(synth.render(kind, 26, 1, scale=2, anomaly=ak).image, False)["anomalies"]}
        assert found & expected, f"{kind}/{ak}: found {found}"
        assert anomaly.analyze(synth.render(kind, 26, 1, scale=2).image, False)["anomalies"] == []


def test_anomaly_output_never_claims_a_market_anomaly():
    r = anomaly.analyze(synth.render("fx_line_chart", 26, 1, scale=2, anomaly="spike").image, False)
    assert "NOT a confirmed financial anomaly" in r["disclaimer"] and r["review_required"] is True
    assert all(a["bbox"] and 0 <= a["severity"] <= 1 for a in r["anomalies"])


# ------------------------------------------------------------------ optical flow (feature 7)
def test_lucas_kanade_recovers_known_translation():
    img = synth.render("fx_line_chart", 26, 1).image
    M = np.float32([[1, 0, 6], [0, 1, 3]])
    moved = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    r = flow.analyze_pair(img, moved)["summary"]
    assert r["lk_median_dx"] == pytest.approx(6.0, abs=0.8) and r["lk_median_dy"] == pytest.approx(3.0, abs=0.8)
    # Dense flow is only defined where there is texture (flat backgrounds report ~0), so the *mean* over all pixels
    # under-states the shift; the median over the moving region and the peak magnitude recover it.
    reg = flow.analyze_pair(img, moved)["moving_regions"][0]
    assert reg["median_dx"] == pytest.approx(6.0, abs=1.0) and reg["median_dy"] == pytest.approx(3.0, abs=1.0)
    assert r["max_magnitude_px"] == pytest.approx(np.hypot(6, 3), abs=1.5)


def test_flow_on_identical_frames_reports_no_motion():
    img = synth.render("fx_line_chart", 26, 1).image
    r = flow.analyze_pair(img, img.copy())
    assert r["summary"]["mean_magnitude_px"] < 0.05 and r["moving_regions"] == []


def test_curve_vertical_shift_sign_and_sequence_api():
    a, b = video._terminal_frame(9.0), video._terminal_frame(11.0)   # line moves UP by 30px
    s = flow.curve_vertical_shift(a, b)
    assert s is not None and s["median_shift_px"] == pytest.approx(-30, abs=3)
    seq = flow.analyze_sequence([a, b, b])
    assert seq["n_frames"] == 3 and len(seq["pairs"]) == 2 and "does not establish market direction" in seq["caveat"]
    with pytest.raises(ValueError):
        flow.analyze_sequence([a])
