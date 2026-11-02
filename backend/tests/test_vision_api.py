"""Vision API: upload validation, the five analysis endpoints, and -- most importantly -- the approval
flow: a CV-read value must NEVER change Treasury state until an analyst approves it."""
from __future__ import annotations

import io
import time

import cv2
import numpy as np
import pytest

from app.api import vision_common
from app.config import settings
from app.cv_engine.vision import synth, video
from tests.vision_helpers import files, needs_ocr, png

ISIN = "IN0020240001"


@pytest.fixture(autouse=True)
def _clean_overrides(client):
    client.delete("/api/cv/overrides")
    yield
    client.delete("/api/cv/overrides")


def _bond_yield(client, isin=ISIN):
    return next(b for b in client.get("/api/bonds").json() if b["isin"] == isin)


def _fx_rate(client, pair="USDINR"):
    return next(q for q in client.get("/api/fx/quotes").json() if q["pair"] == pair)["rate"]


# ------------------------------------------------------------------ uploads
def test_sample_image_endpoint_and_validation(client):
    r = client.get("/api/vision/sample-image?kind=yield_curve")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.headers["x-synthetic"] == "true"
    assert client.get("/api/vision/sample-image?kind=nope").status_code == 400
    assert client.get("/api/vision/sample-image?template=3").status_code == 422


@pytest.mark.parametrize("path", ["quality", "digitize", "anomaly"])
def test_upload_validation_rejects_bad_files(client, path, monkeypatch):
    url = f"/api/vision/{path}"
    assert client.post(url, files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400
    assert client.post(url, files={"file": ("x.png", b"", "image/png")}).status_code == 400
    assert client.post(url, files={"file": ("x.png", b"not an image at all", "image/png")}).status_code == 400
    tiny = np.zeros((8, 8, 3), np.uint8)
    assert client.post(url, files=files("tiny.png", tiny)).status_code == 400
    monkeypatch.setattr(settings, "max_upload_size_bytes", 100)
    assert client.post(url, files=files("big.png", np.zeros((64, 64, 3), np.uint8))).status_code == 413


def test_compare_requires_two_valid_images(client):
    ok = files("a.png", synth.render("bond_table", 26, 0).image, "file_a")
    r = client.post("/api/vision/compare", files={**ok, "file_b": ("b.txt", b"x", "text/plain")})
    assert r.status_code == 400


# ------------------------------------------------------------------ feature endpoints
def test_quality_endpoint(client):
    r = client.post("/api/vision/quality?with_ocr=false", files=files("t.png", synth.render("bond_table", 26, 0, 2).image))
    assert r.status_code == 200
    j = r.json()
    assert j["before"]["verdict"] in ("good", "fair", "poor") and j["images"]["after"].startswith("data:image/png") and j["comparison"]


@needs_ocr
def test_digitize_endpoint_returns_json_csv_and_uncertainty(client):
    img = synth.render("yield_curve", 26, 1, scale=2).image
    j = client.post("/api/vision/digitize", files=files("yc.png", img)).json()
    assert j["chart_kind"] == "yield_curve" and j["csv"].startswith("series,x_px") and j["overlay"].startswith("data:image/png")
    p = j["series"][0]["points"][0]
    assert {"y_value", "y_uncertainty", "tenor"} <= set(p) and j["limitations"] and "NOT a calibrated probability" in j["confidence_note"]


def test_digitize_manual_calibration_needs_both_bounds(client):
    r = client.post("/api/vision/digitize", files=files("c.png", synth.render("fx_line_chart", 26, 1, 2).image), data={"y_top_value": "1.1"})
    assert r.status_code == 400
    r = client.post("/api/vision/digitize", files=files("c.png", synth.render("fx_line_chart", 26, 1, 2).image), data={"y_top_value": "1.1", "y_bottom_value": "1.0"})
    assert r.status_code == 200 and r.json()["calibration"]["y"]["source"] == "manual"


def test_compare_and_anomaly_and_flow_endpoints(client):
    a, b = video._terminal_frame(1.0), video._terminal_frame(4.0)
    r = client.post("/api/vision/compare?with_ocr=false", files={**files("a.png", a, "file_a"), **files("b.png", b, "file_b")})
    assert r.status_code == 200 and r.json()["verdict"] == "visual_change" and r.json()["images"]["changes_overlay"]
    r = client.get("/api/vision/anomaly/sample?anomaly_kind=spike")
    j = r.json()
    assert r.status_code == 200 and any(x["kind"] == "spike" for x in j["anomalies"]) and j["ground_truth"]["injected"]["kind"] == "spike"
    assert client.get("/api/vision/anomaly/sample?anomaly_kind=none").json()["anomalies"] == []
    r = client.post("/api/vision/flow", files=[("files", ("1.png", png(a), "image/png")), ("files", ("2.png", png(b), "image/png"))])
    assert r.status_code == 200 and len(r.json()["pairs"]) == 1
    assert client.post("/api/vision/flow", files=[("files", ("1.png", png(a), "image/png"))]).status_code == 400


# ------------------------------------------------------------------ proposals: nothing changes until approved
def _propose(client, items, source="chart_digitization", ref="chart.png"):
    return client.post("/api/vision/proposals", json={"source": source, "source_ref": ref, "items": items})


def test_creating_a_proposal_changes_no_market_value(client):
    before_bond, before_fx = _bond_yield(client)["current_yield_pct"], _fx_rate(client)
    r = _propose(client, [{"target": "bond_yield", "instrument_id": ISIN, "value": before_bond + 0.4, "confidence": 0.9, "uncertainty": 0.002},
                          {"target": "fx", "instrument_id": "USDINR", "value": before_fx + 0.2}])
    assert r.status_code == 200 and len(r.json()["created"]) == 2 and "No market value has been changed" in r.json()["message"]
    assert all(p["status"] == "pending" for p in r.json()["created"])
    assert client.get("/api/cv/overrides").json() == []
    assert _bond_yield(client)["current_yield_pct"] == before_bond and _bond_yield(client)["is_cv_corrected"] is False
    assert _fx_rate(client) == before_fx
    assert len(client.get("/api/vision/proposals?status=pending").json()) == 2


def test_approval_propagates_to_bonds_and_fx(client):
    b0, f0 = _bond_yield(client), _fx_rate(client)
    pid = _propose(client, [{"target": "bond_yield", "instrument_id": ISIN, "value": b0["current_yield_pct"] + 0.3}]).json()["created"][0]["id"]
    r = client.post(f"/api/vision/proposals/{pid}/approve", json={"note": "checked vs terminal"})
    assert r.status_code == 200
    a = r.json()["analytics"]
    assert a["previous_value"] == b0["current_yield_pct"] and a["delta_bps"] == pytest.approx(30.0) and a["clean_price_after"] < a["clean_price_before"]
    b1 = _bond_yield(client)
    assert b1["current_yield_pct"] == pytest.approx(b0["current_yield_pct"] + 0.3) and b1["is_cv_corrected"] is True and b1["clean_price"] < b0["clean_price"]
    assert client.get("/api/cv/overrides").json()[0]["source"] == "vision:chart_digitization"
    assert client.post(f"/api/vision/proposals/{pid}/approve", json={}).status_code == 409   # cannot approve twice

    fid = _propose(client, [{"target": "fx", "instrument_id": "USDINR", "value": round(f0 + 0.2, 4)}], source="screenshot_comparison").json()["created"][0]["id"]
    assert client.post(f"/api/vision/proposals/{fid}/approve", json={}).status_code == 200
    assert _fx_rate(client) == pytest.approx(f0 + 0.2)
    # audit trail
    assert client.get("/api/vision/proposals?status=approved").json()[0]["decided_at"]


def test_analyst_can_correct_value_before_approving(client):
    b0 = _bond_yield(client)["current_yield_pct"]
    pid = _propose(client, [{"target": "bond_yield", "instrument_id": ISIN, "value": b0 + 0.5}]).json()["created"][0]["id"]
    client.post(f"/api/vision/proposals/{pid}/approve", json={"value": b0 + 0.1})
    assert _bond_yield(client)["current_yield_pct"] == pytest.approx(b0 + 0.1)
    assert client.get("/api/vision/proposals?status=approved").json()[0]["applied_value"] == pytest.approx(b0 + 0.1)


def test_flagged_values_need_explicit_confirmation(client):
    pid = _propose(client, [{"target": "bond_yield", "instrument_id": ISIN, "value": 40.0}]).json()["created"][0]["id"]   # e.g. a dropped decimal point
    r = client.post(f"/api/vision/proposals/{pid}/approve", json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "confirmation_required" and r.json()["detail"]["warnings"]
    assert client.get("/api/cv/overrides").json() == []
    assert client.post(f"/api/vision/proposals/{pid}/approve", json={"confirm_flagged": True}).status_code == 200


def test_invalid_and_unmappable_values_are_never_staged(client):
    r = _propose(client, [{"target": "bond_yield", "instrument_id": ISIN, "value": -1.0}, {"target": "bond_yield", "instrument_id": "50Y", "value": 7.0},
                          {"target": "fx", "instrument_id": "XXXYYY", "value": 1.0}, {"target": "fx", "instrument_id": "USDINR", "value": 0}])
    j = r.json()
    assert r.status_code == 200 and j["created"] == [] and len(j["skipped"]) == 4
    assert any("mapping unavailable" in s["reason"] for s in j["skipped"])
    assert client.post("/api/vision/proposals", json={"source": "bogus", "items": [{"target": "fx", "instrument_id": "USDINR", "value": 83}]}).status_code == 400
    assert client.post("/api/vision/proposals", json={"source": "ocr", "items": [{"target": "equity", "instrument_id": "X", "value": 1}]}).status_code == 422


def test_reject_leaves_state_untouched_and_duplicates_are_not_restaged(client):
    b0 = _bond_yield(client)["current_yield_pct"]
    item = {"target": "bond_yield", "instrument_id": ISIN, "value": b0 + 0.2}
    p1 = _propose(client, [item]).json()["created"][0]
    p2 = _propose(client, [item]).json()["created"][0]
    assert p1["id"] == p2["id"] and len(client.get("/api/vision/proposals").json()) == 1
    r = client.post(f"/api/vision/proposals/{p1['id']}/reject", json={"note": "misread"})
    assert r.json()["status"] == "rejected" and client.get("/api/cv/overrides").json() == []
    assert _bond_yield(client)["current_yield_pct"] == b0
    assert client.post(f"/api/vision/proposals/{p1['id']}/approve", json={}).status_code == 409
    assert client.post("/api/vision/proposals/9999/approve", json={}).status_code == 404


@needs_ocr
def test_digitized_curve_flows_to_proposals_not_to_treasury(client):
    """End to end: digitize a yield-curve screenshot -> stage its mappable tenors -> nothing has changed yet."""
    j = client.post("/api/vision/digitize", files=files("yc.png", synth.render("yield_curve", 26, 1, scale=2).image)).json()
    items = [{"target": "bond_yield", "instrument_id": p["tenor"], "value": round(p["y_value"], 3), "confidence": j["confidence"], "uncertainty": p["y_uncertainty"]}
             for p in j["series"][0]["points"] if p.get("tenor")]
    assert len(items) >= 6
    r = _propose(client, items).json()
    assert len(r["created"]) + len(r["skipped"]) == len(items)           # every tenor is either staged or explained
    assert all("mapping unavailable" in s["reason"] for s in r["skipped"])
    assert client.get("/api/cv/overrides").json() == []


# ------------------------------------------------------------------ events
def test_events_lifecycle(client):
    e = client.post("/api/vision/events", json={"kind": "spike", "source": "anomaly", "severity": "notice", "title": "Visual spike", "detail": {"x": 1}}).json()
    assert e["status"] == "open"
    assert client.get("/api/vision/events?status=open").json()[0]["id"] == e["id"]
    assert client.post(f"/api/vision/events/{e['id']}/status?status=acknowledged").json()["status"] == "acknowledged"
    assert client.get("/api/vision/events?status=open").json() == []
    assert client.post("/api/vision/events", json={"kind": "k", "source": "s", "severity": "critical", "title": "t"}).status_code == 422
    assert client.post("/api/vision/events/999/status?status=dismissed").status_code == 404


# ------------------------------------------------------------------ video
def test_video_upload_validation(client, monkeypatch):
    assert client.post("/api/vision/video", files={"file": ("x.txt", b"abc", "text/plain")}).status_code == 400
    assert client.post("/api/vision/video", files={"file": ("x.avi", b"", "video/avi")}).status_code == 400
    assert client.post("/api/vision/video", files={"file": ("x.avi", b"garbage" * 50, "video/avi")}).status_code == 400
    monkeypatch.setattr(vision_common, "MAX_VIDEO_BYTES", 10)
    assert client.post("/api/vision/video", files={"file": ("x.avi", b"0123456789ABC", "video/avi")}).status_code == 413
    assert client.get("/api/vision/jobs/nope").status_code == 404 and client.delete("/api/vision/jobs/nope").status_code == 404


@needs_ocr
def test_video_job_creates_events_but_never_changes_market_data(client, tmp_path):
    p = str(tmp_path / "t.avi")
    video.make_demo_video(p)
    before = _bond_yield(client)["current_yield_pct"]
    with open(p, "rb") as fh:
        job = client.post("/api/vision/video", files={"file": ("terminal.avi", fh.read(), "video/avi")}).json()
    for _ in range(300):
        st = client.get(f"/api/vision/jobs/{job['id']}").json()
        if st["status"] in ("done", "failed", "cancelled"):
            break
        time.sleep(0.2)
    assert st["status"] == "done" and st["progress"] == 1.0 and st["meta"]["events_created"] >= 2
    kinds = {e["kind"] for e in client.get("/api/vision/events?status=open").json()}
    assert {"value_change", "chart_motion"} <= kinds
    assert client.get("/api/cv/overrides").json() == [] and _bond_yield(client)["current_yield_pct"] == before
    # polling again must not duplicate events
    n = len(client.get("/api/vision/events").json())
    client.get(f"/api/vision/jobs/{job['id']}")
    assert len(client.get("/api/vision/events").json()) == n


# ------------------------------------------------------------------ regressions on the existing OCR workflow
def _fx_screenshot(text: str) -> bytes:
    img = np.full((200, 640, 3), 255, np.uint8)
    cv2.putText(img, text, (30, 110), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 0, 0), 2)
    return png(img)


@needs_ocr
def test_fx_screenshot_extraction_and_confidence_is_never_the_value(client):
    r = client.post("/api/cv/extract", files={"file": ("fx.png", io.BytesIO(_fx_screenshot("USD/INR 83.4210")), "image/png")})
    assert r.status_code == 200
    f = next(x for x in r.json()["fields"] if x["instrument"] == "USD/INR")
    assert f["value"] == pytest.approx(83.421, abs=0.005) and 0 < f["confidence"] <= 1 and f["value"] != f["confidence"]
    assert client.get("/api/cv/overrides").json() == []      # extraction alone commits nothing


@needs_ocr
def test_fx_quote_read_from_screenshot_becomes_a_proposal_with_normalised_pair(client):
    f = next(x for x in client.post("/api/cv/extract", files={"file": ("fx.png", io.BytesIO(_fx_screenshot("USD/INR 83.4210")), "image/png")}).json()["fields"] if x["instrument"] == "USD/INR")
    r = _propose(client, [{"target": "fx", "instrument_id": f["instrument"], "value": f["value"], "confidence": f["confidence"]}], source="ocr", ref="fx.png").json()
    assert r["created"][0]["instrument_id"] == "USDINR" and r["created"][0]["status"] == "pending"
    assert client.get("/api/cv/overrides").json() == []
