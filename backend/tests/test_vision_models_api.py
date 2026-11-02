"""API layer for features 9 (classify), 10 (similarity + index) and 11 (zero-shot search)."""
from __future__ import annotations

import time

import pytest

from app.cv_engine.vision import runtime, synth, video
from tests.vision_helpers import files, needs_ocr

MODELS_AVAILABLE = runtime.model_status("classifier_cnn")["available"] and runtime.model_status("classifier_vit")["available"] and runtime.model_status("encoder")["available"]
needs_models = pytest.mark.skipif(not MODELS_AVAILABLE, reason="trained ONNX models not present (run `python -m app.cv_engine.vision.train`)")


@pytest.fixture(autouse=True)
def _clean(client):
    client.delete("/api/cv/overrides")
    yield
    client.delete("/api/cv/overrides")


# ------------------------------------------------------------------ 9. classify
@needs_models
def test_classify_endpoint(client):
    r = client.post("/api/vision/classify", files=files("yc.png", synth.render("yield_curve", 26, 0).image))
    assert r.status_code == 200
    j = r.json()
    assert j["predictions"]["cnn"]["label"] in synth.KINDS and j["predictions"]["vit"]["label"] in synth.KINDS
    assert "SYNTHETIC" in j["domain_gap_note"] and j["classes"] == synth.KINDS


@needs_models
def test_classifier_benchmark_endpoint(client):
    j = client.get("/api/vision/classifier/benchmark").json()
    assert "cnn" in j and "vit" in j and j["dataset"]["images_total"] > 0


def test_classify_returns_503_without_models(client, monkeypatch):
    monkeypatch.setattr(runtime, "_nets", {"classifier_cnn": None, "classifier_vit": None})
    monkeypatch.setattr(runtime, "_errors", {"classifier_cnn": "missing", "classifier_vit": "missing"})
    r = client.post("/api/vision/classify", files=files("x.png", synth.render("bond_table", 26, 0).image))
    assert r.status_code == 503


# ------------------------------------------------------------------ 10. similarity
@needs_models
def test_similarity_compare_endpoint(client):
    img = synth.render("fx_line_chart", 26, 1).image
    r = client.post("/api/vision/similarity/compare", files={**files("a.png", img, "file_a"), **files("b.png", img.copy(), "file_b")})
    assert r.status_code == 200 and r.json()["verdict"]["label"] == "near_duplicate"


@needs_models
def test_similarity_index_lifecycle(client):
    assert client.get("/api/vision/index").json()["count"] == 0
    r = client.post("/api/vision/index", files=files("report1.png", synth.render("bond_table", 26, 0).image))
    assert r.status_code == 200 and r.json()["filename"] == "report1.png"
    assert client.get("/api/vision/index").json()["count"] == 1
    r = client.post("/api/vision/index/search", files=files("q.png", synth.render("bond_table", 26, 1).image))
    j = r.json()
    assert j["index_size"] == 1 and j["results"][0]["filename"] == "report1.png" and j["results"][0]["similarity"] > 0.5
    iid = client.get("/api/vision/index").json()["items"][0]["id"]
    assert client.delete(f"/api/vision/index/{iid}").status_code == 200
    assert client.get("/api/vision/index").json()["count"] == 0
    assert client.delete(f"/api/vision/index/{iid}").status_code == 404


@needs_models
def test_seed_synthetic_is_idempotent(client):
    r1 = client.post("/api/vision/index/seed-synthetic").json()
    assert r1["added"] == len(synth.KINDS)
    r2 = client.post("/api/vision/index/seed-synthetic").json()
    assert r2["added"] == 0


@needs_models
@needs_ocr
def test_financial_image_intelligence_upload_is_auto_indexed(client):
    img = synth.render("yield_curve", 26, 0, scale=2).image
    client.post("/api/cv/extract", files=files("terminal.png", img))
    items = client.get("/api/vision/index").json()["items"]
    assert any(i["origin"] == "financial_image_intelligence" and i["filename"] == "terminal.png" for i in items)


def test_similarity_endpoints_503_without_encoder(client, monkeypatch):
    monkeypatch.setattr(runtime, "embed", lambda img: None)
    img = synth.render("bond_table", 26, 0).image
    assert client.post("/api/vision/similarity/compare", files={**files("a.png", img, "file_a"), **files("b.png", img.copy(), "file_b")}).status_code == 503
    assert client.post("/api/vision/index", files=files("a.png", img)).status_code == 503
    assert client.post("/api/vision/index/search", files=files("a.png", img)).status_code == 503


# ------------------------------------------------------------------ 11. zero-shot search
def test_clip_status_endpoint(client):
    assert "available" in client.get("/api/vision/clip/status").json()


@needs_models
@needs_ocr
def test_zero_shot_search_with_reference_gallery(client):
    r = client.post("/api/vision/search/zero-shot", data={"query": "a government securities yield curve", "include_reference": "true"})
    assert r.status_code == 200
    j = r.json()
    assert len(j["results"]) == len(synth.KINDS) * 2 and j["results"][0]["rank"] == 1
    assert all("thumbnail" in r_ for r_ in j["results"]) and j["clip_ran"] is False


def test_zero_shot_search_validation(client):
    assert client.post("/api/vision/search/zero-shot", data={"query": ""}).status_code == 400
    assert client.post("/api/vision/search/zero-shot", data={"query": "x", "include_reference": "false"}).status_code == 400
    assert client.post("/api/vision/search/zero-shot", data={"query": "x", "backend": "bogus"}).status_code == 400
