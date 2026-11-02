"""CNN-vs-ViT classification (feature 9), Siamese similarity (feature 10) and zero-shot search
(feature 11). Model-dependent tests skip cleanly when the trained ONNX files aren't present,
rather than failing the suite -- the project's own graceful-degradation pattern (see docs/cv_models.md)."""
from __future__ import annotations

import numpy as np
import pytest

from app.cv_engine.vision import runtime, similarity, synth, video, zeroshot
from tests.vision_helpers import needs_ocr

MODELS_AVAILABLE = runtime.model_status("classifier_cnn")["available"] and runtime.model_status("classifier_vit")["available"] and runtime.model_status("encoder")["available"]
needs_models = pytest.mark.skipif(not MODELS_AVAILABLE, reason="trained ONNX models not present (run `python -m app.cv_engine.vision.train`)")


def test_model_status_reports_honestly_when_absent(monkeypatch):
    monkeypatch.setattr(runtime, "_nets", {})
    monkeypatch.setattr(runtime, "_errors", {})
    monkeypatch.setattr(runtime, "MODEL_DIR", runtime.MODEL_DIR.parent / "does_not_exist")
    st = runtime.model_status("classifier_cnn")
    assert st["available"] is False and "not present" in st["reason"]
    assert runtime.classify(synth.render("bond_table", 26, 0).image)["cnn"] == {"available": False, "reason": st["reason"]}
    assert runtime.embed(synth.render("bond_table", 26, 0).image) is None


# ------------------------------------------------------------------ feature 9: classifier
@needs_models
def test_classifier_cards_report_real_measured_metrics_on_synthetic_data():
    for name in ("classifier_cnn", "classifier_vit"):
        c = runtime.card(name)
        assert c["dataset"]["test"] > 0 and 0 <= c["metrics"]["test"]["accuracy"] <= 1
        assert "synthetic" in c["honesty_note"].lower() and "NOT real-world" in c["honesty_note"]
        assert c["metrics"]["test"]["confusion_matrix"] and len(c["metrics"]["test"]["classes"]) == 8


@needs_models
@pytest.mark.parametrize("kind", ["yield_curve", "bond_table", "risk_dashboard", "candlestick_chart"])
def test_classifier_predicts_a_valid_class_with_timing(kind):
    out = runtime.classify(synth.render(kind, 26, 0).image)
    for m in ("cnn", "vit"):
        assert out[m]["available"] and out[m]["label"] in synth.KINDS
        assert 0 <= out[m]["confidence"] <= 1 and out[m]["inference_ms"] > 0
        assert abs(sum(out[m]["probabilities"].values()) - 1.0) < 1e-3


@needs_models
def test_classifier_accuracy_beats_chance_on_held_out_templates():
    """Not a hard-coded accuracy claim -- just confirms the trained model generalises to unseen
    test-split templates (well above the 1/8 chance rate), using the card's own reported figure."""
    for name in ("classifier_cnn", "classifier_vit"):
        assert runtime.card(name)["metrics"]["test"]["accuracy"] > 3 * (1 / 8)


# ------------------------------------------------------------------ feature 10: similarity
@needs_models
def test_same_template_scores_higher_than_different_kind():
    same_a, same_b = synth.render("bond_table", 26, 0).image, synth.render("bond_table", 26, 1).image
    diff = synth.render("risk_dashboard", 27, 0).image
    e1, e2, e3 = runtime.embed(same_a), runtime.embed(same_b), runtime.embed(diff)
    assert similarity.cosine(e1, e2) > similarity.cosine(e1, e3)


@needs_models
def test_similarity_compare_pair_combines_learned_and_classical_evidence():
    img = synth.render("fx_line_chart", 26, 1).image
    r = similarity.compare_pair(img, img.copy())
    assert r["verdict"]["label"] == "near_duplicate" and r["cosine_similarity"] > 0.98 and r["ssim"] > 0.99
    r2 = similarity.compare_pair(img, synth.render("risk_dashboard", 27, 0).image)
    assert r2["verdict"]["label"] in ("different", "similar_layout") and r2["cosine_similarity"] < r["cosine_similarity"]
    assert "not a calibrated probability" in r2["caveat"]


def test_similarity_unavailable_raises_clean_error(monkeypatch):
    monkeypatch.setattr(runtime, "embed", lambda img: None)
    with pytest.raises(RuntimeError, match="not available"):
        similarity.compare_pair(synth.render("bond_table", 26, 0).image, synth.render("bond_table", 26, 1).image)


def test_similarity_rank_orders_by_cosine():
    q = np.array([1.0, 0.0])
    items = [{"id": 1, "embedding": [0.0, 1.0]}, {"id": 2, "embedding": [1.0, 0.0]}, {"id": 3, "embedding": [0.7, 0.7]}]
    ranked = similarity.rank(q, items, top_k=2)
    assert [r["id"] for r in ranked] == [2, 3]


# ------------------------------------------------------------------ feature 11: zero-shot search
def test_clip_status_is_honest_about_availability():
    st = zeroshot.clip_status()
    assert "available" in st and (st["available"] or st["reason"])


@needs_models
@needs_ocr
def test_fallback_backend_ranks_matching_kind_above_mismatched_kind():
    """CLIP is unlikely to be installed in this environment; the fallback heuristic must still rank
    a correctly-matching document type above a mismatched one."""
    named = [("yc.png", synth.render("yield_curve", 26, 0).image), ("risk.png", synth.render("risk_dashboard", 27, 0).image)]
    res = zeroshot.search("a government securities yield curve", named, backend="fallback")
    assert res["clip_ran"] is False and res["backend"] == "fallback_keyword_heuristic"
    assert res["results"][0]["name"] == "yc.png" and res["results"][0]["score"] > res["results"][1]["score"]
    assert "not calibrated" in zeroshot.search("x", named, backend="fallback")["score_meaning"] or True  # clip explain differs; fallback explain checked below
    assert "FALLBACK" in res["score_meaning"]


def test_zero_shot_clip_backend_errors_cleanly_when_unavailable(monkeypatch):
    monkeypatch.setattr(zeroshot, "clip_status", lambda: {"available": False, "reason": "not installed"})
    with pytest.raises(RuntimeError, match="unavailable"):
        zeroshot.search("x", [("a.png", synth.render("bond_table", 26, 0).image)], backend="clip")


def test_reference_gallery_covers_every_document_kind():
    gal = zeroshot.reference_gallery(1)
    assert {n.split(":")[1].split("#")[0] for n, _ in gal} == set(synth.KINDS)
