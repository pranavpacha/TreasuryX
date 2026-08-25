from __future__ import annotations

import io

import cv2
import numpy as np


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_overview_returns_disclaimer_and_demo_flag(client):
    r = client.get("/api/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    assert "No real-money trading" in body["disclaimer"]
    assert body["fx_snapshot"]


def test_fx_quotes_all_demo(client):
    r = client.get("/api/fx/quotes")
    assert r.status_code == 200
    quotes = r.json()
    assert len(quotes) == 4
    assert all(q["is_demo"] for q in quotes)


def test_fx_history_valid_pair(client):
    r = client.get("/api/fx/history/USDINR")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_fx_history_invalid_pair_returns_404(client):
    r = client.get("/api/fx/history/XXXYYY")
    assert r.status_code == 404


def test_fx_trade_simulated(client):
    r = client.post("/api/fx/trade", json={
        "instrument_type": "FX", "instrument_id": "USDINR", "side": "BUY", "quantity": 1_000_000, "price": 83.5,
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SIMULATED"
    assert body["notional"] == 83_500_000


def test_fx_trade_invalid_pair_returns_400(client):
    r = client.post("/api/fx/trade", json={
        "instrument_type": "FX", "instrument_id": "ZARINR", "side": "BUY", "quantity": 1000, "price": 1.0,
    })
    assert r.status_code == 400


def test_fx_trade_negative_quantity_rejected(client):
    r = client.post("/api/fx/trade", json={
        "instrument_type": "FX", "instrument_id": "USDINR", "side": "BUY", "quantity": -100, "price": 83.5,
    })
    assert r.status_code == 422  # pydantic validation error


def test_bonds_list(client):
    r = client.get("/api/bonds")
    assert r.status_code == 200
    bonds = r.json()
    assert len(bonds) == 5
    for b in bonds:
        assert b["modified_duration"] > 0
        assert b["dv01_per_100_face"] > 0


def test_bond_ytm_endpoint(client):
    r = client.get("/api/bonds/IN0020240001/ytm", params={"price": 100.0})
    assert r.status_code == 200
    assert "solved_ytm_pct" in r.json()


def test_bond_ytm_unknown_isin_returns_404(client):
    r = client.get("/api/bonds/NOTAREALISIN/ytm", params={"price": 100.0})
    assert r.status_code == 404


def test_yield_curve_default(client):
    r = client.get("/api/yield-curve")
    assert r.status_code == 200
    assert len(r.json()) == 8


def test_yield_curve_compare(client):
    dates = client.get("/api/yield-curve/dates").json()
    r = client.get("/api/yield-curve/compare", params={"date1": dates[0], "date2": dates[-1]})
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] in {"STEEPENING", "FLATTENING", "STABLE"}


def test_risk_summary_has_positions_from_seed(client):
    r = client.get("/api/risk/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["fx_exposure_inr"] > 0
    assert body["regime"] in {"NORMAL", "RISK-ON", "RISK-OFF", "HIGH-VOLATILITY", "CURVE-STEEPENING", "CURVE-FLATTENING"}


def test_scenario_run_valid(client):
    r = client.post("/api/scenario/run", json={
        "label": "test scenario", "fx_shock_pct": {"USDINR": 0.02}, "parallel_yield_shock_bps": 25,
    })
    assert r.status_code == 200
    body = r.json()
    assert "total_pnl" in body
    assert len(body["method_notes"]) > 0


def test_scenario_history_after_run(client):
    client.post("/api/scenario/run", json={"label": "s1", "fx_shock_pct": {}, "parallel_yield_shock_bps": 10})
    r = client.get("/api/scenario/history")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_cv_extract_rejects_bad_extension(client):
    r = client.post("/api/cv/extract", files={"file": ("test.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_cv_extract_rejects_empty_file(client):
    r = client.post("/api/cv/extract", files={"file": ("test.png", b"", "image/png")})
    assert r.status_code == 400


def test_cv_extract_valid_image(client):
    img = np.full((200, 300, 3), 255, dtype=np.uint8)
    cv2.putText(img, "USD/INR 83.45", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    r = client.post("/api/cv/extract", files={"file": ("chart.png", io.BytesIO(buf.tobytes()), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert "stages" in body
    assert "original" in body["stages"]


def test_cv_extract_rejects_corrupt_image(client):
    r = client.post("/api/cv/extract", files={"file": ("chart.png", b"not a real png", "image/png")})
    assert r.status_code == 400


def test_cv_extract_model_details_shape(client):
    """model_details must always be present and internally consistent, whether or not
    torch/trained weights are available in the environment running the test (see
    app/cv_engine/models/infer.py's graceful-degradation contract)."""
    img = np.full((200, 300, 3), 255, dtype=np.uint8)
    cv2.putText(img, "USD/INR 83.45", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    r = client.post("/api/cv/extract", files={"file": ("chart.png", io.BytesIO(buf.tobytes()), "image/png")})
    assert r.status_code == 200
    model_details = r.json()["model_details"]
    assert "available" in model_details
    if model_details["available"]:
        assert model_details["cnn"]["label"] in model_details["classes"]
        assert model_details["vit"]["label"] in model_details["classes"]
        assert 0.0 <= model_details["cnn"]["confidence"] <= 1.0
        assert isinstance(model_details["agree"], bool)
    else:
        assert model_details["reason"]


def test_market3d_yield_surface(client):
    r = client.get("/api/market3d/yield-surface")
    assert r.status_code == 200
    assert len(r.json()["points"]) > 0


def test_market3d_fx_vol_surface(client):
    r = client.get("/api/market3d/fx-vol-surface")
    assert r.status_code == 200
    assert len(r.json()["points"]) > 0


def test_market3d_stress_surface_uses_seeded_positions(client):
    r = client.get("/api/market3d/stress-surface", params={"fx_steps": 3, "yield_steps": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["has_positions"] is True
    assert len(body["grid"]) == 9


def test_trade_blotter_lists_seeded_and_new_trades(client):
    client.post("/api/fx/trade", json={
        "instrument_type": "FX", "instrument_id": "GBPINR", "side": "SELL", "quantity": 500_000, "price": 101.5,
    })
    r = client.get("/api/positions/blotter")
    assert r.status_code == 200
    assert len(r.json()) >= 1
