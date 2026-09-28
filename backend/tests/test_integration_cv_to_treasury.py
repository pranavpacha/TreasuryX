"""
Integration tests for the CV -> Treasury state-propagation flow: an extracted/corrected value,
once committed, must be visible everywhere else in the app (bonds list, bond positions, risk,
stress surface) -- not just returned once and discarded. This is the core "no disconnected
academic demos" requirement: CV output must actually change application state.
"""
from __future__ import annotations

import io

import cv2
import numpy as np


def _upload_bond_chart(client, isin_hint_text="10Y G-Sec 7.50%"):
    img = np.full((200, 400, 3), 255, dtype=np.uint8)
    cv2.putText(img, isin_hint_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    r = client.post("/api/cv/extract", files={"file": ("chart.png", io.BytesIO(buf.tobytes()), "image/png")})
    assert r.status_code == 200
    return r.json()


def test_committed_bond_yield_override_propagates_to_bonds_list(client):
    isin = "IN0020240001"
    before = client.get("/api/bonds").json()
    bond_before = next(b for b in before if b["isin"] == isin)
    assert bond_before["is_cv_corrected"] is False
    original_yield = bond_before["current_yield_pct"]

    extraction = _upload_bond_chart(client)
    extraction_id = extraction["id"]

    # Directly correct the field to a known value and target the seeded bond, simulating a
    # human reviewing OCR output before committing (the realistic Financial Image Intelligence flow).
    corrected_fields = [{
        "instrument": isin, "metric": "yield", "value": original_yield + 0.5,
        "unit": "pct", "confidence": 0.9, "source_region": None,
    }]
    r = client.post("/api/cv/correct", json={"extraction_id": extraction_id, "corrected_fields": corrected_fields})
    assert r.status_code == 200

    r = client.post("/api/cv/commit", json={"extraction_id": extraction_id, "target": "bond_yield", "instrument_id": isin})
    assert r.status_code == 200
    commit_result = r.json()
    assert commit_result["previous_value"] == original_yield
    assert commit_result["new_value"] == original_yield + 0.5

    after = client.get("/api/bonds").json()
    bond_after = next(b for b in after if b["isin"] == isin)
    assert bond_after["current_yield_pct"] == original_yield + 0.5
    assert bond_after["is_cv_corrected"] is True
    # A higher yield should reprice the bond lower (inverse yield/price relationship)
    assert bond_after["clean_price"] < bond_before["clean_price"]

    client.delete("/api/cv/overrides")


def test_committed_bond_yield_propagates_to_open_positions_and_risk(client):
    isin = "IN0020240001"  # has an open seeded position per app/seed.py
    positions_before = client.get("/api/positions/bonds").json()
    pos_before = next(p for p in positions_before if p["isin"] == isin)

    extraction = _upload_bond_chart(client)
    extraction_id = extraction["id"]
    shocked_yield = pos_before["current_yield_pct"] + 1.0
    client.post("/api/cv/correct", json={
        "extraction_id": extraction_id,
        "corrected_fields": [{"instrument": isin, "metric": "yield", "value": shocked_yield, "unit": "pct", "confidence": 0.9, "source_region": None}],
    })
    commit = client.post("/api/cv/commit", json={"extraction_id": extraction_id, "target": "bond_yield", "instrument_id": isin})
    assert commit.status_code == 200
    assert commit.json()["affected_open_positions"], "commit should report the affected open position"

    positions_after = client.get("/api/positions/bonds").json()
    pos_after = next(p for p in positions_after if p["isin"] == isin)
    assert pos_after["current_yield_pct"] == shocked_yield
    assert pos_after["market_value_inr"] != pos_before["market_value_inr"]

    # Risk summary (bond DV01 in particular) should also move
    risk = client.get("/api/risk/summary").json()
    assert risk["bond_dv01_inr_per_bp"] != 0

    client.delete("/api/cv/overrides")


def test_committed_bond_yield_propagates_to_stress_surface(client):
    # Note: the scenario engine's zero-shock grid point is always exactly 0 P&L by construction
    # (shocked level == current level -> no incremental P&L), regardless of what "current" is --
    # so it can't distinguish a baseline-vs-corrected yield. A NON-zero shock point can: exact
    # repricing is convex in yield, so the same +100bp shock produces a different total P&L
    # depending on what base yield it's applied from.
    isin = "IN0020240001"
    baseline = client.get("/api/market3d/stress-surface", params={"fx_steps": 3, "yield_steps": 3}).json()
    assert baseline["has_positions"] is True
    baseline_point = next(g["total_pnl_inr"] for g in baseline["grid"] if g["fx_shock_pct"] == 0.0 and g["yield_shock_bps"] == 100.0)

    extraction = _upload_bond_chart(client)
    extraction_id = extraction["id"]
    bonds = client.get("/api/bonds").json()
    current_yield = next(b for b in bonds if b["isin"] == isin)["current_yield_pct"]
    client.post("/api/cv/correct", json={
        "extraction_id": extraction_id,
        "corrected_fields": [{"instrument": isin, "metric": "yield", "value": current_yield + 2.0, "unit": "pct", "confidence": 0.9, "source_region": None}],
    })
    client.post("/api/cv/commit", json={"extraction_id": extraction_id, "target": "bond_yield", "instrument_id": isin})

    after = client.get("/api/market3d/stress-surface", params={"fx_steps": 3, "yield_steps": 3}).json()
    after_point = next(g["total_pnl_inr"] for g in after["grid"] if g["fx_shock_pct"] == 0.0 and g["yield_shock_bps"] == 100.0)

    # The +100bp-shock P&L point on the stress surface should differ once the underlying bond
    # yield itself has been corrected -- this is what proves the 3D surface actually reads
    # through the override rather than caching stale baseline data.
    assert after_point != baseline_point

    client.delete("/api/cv/overrides")


def test_reset_overrides_restores_baseline(client):
    isin = "IN0020240001"
    bonds_before = client.get("/api/bonds").json()
    original_yield = next(b for b in bonds_before if b["isin"] == isin)["current_yield_pct"]

    extraction = _upload_bond_chart(client)
    client.post("/api/cv/correct", json={
        "extraction_id": extraction["id"],
        "corrected_fields": [{"instrument": isin, "metric": "yield", "value": original_yield + 3.0, "unit": "pct", "confidence": 0.9, "source_region": None}],
    })
    client.post("/api/cv/commit", json={"extraction_id": extraction["id"], "target": "bond_yield", "instrument_id": isin})

    mid = client.get("/api/bonds").json()
    assert next(b for b in mid if b["isin"] == isin)["current_yield_pct"] == original_yield + 3.0

    r = client.delete("/api/cv/overrides")
    assert r.status_code == 200
    assert r.json()["cleared"] >= 1

    restored = client.get("/api/bonds").json()
    assert next(b for b in restored if b["isin"] == isin)["current_yield_pct"] == original_yield
    assert next(b for b in restored if b["isin"] == isin)["is_cv_corrected"] is False


def test_commit_by_tenor_resolves_to_closest_real_bond(client):
    """Regression: committing a yield-curve extraction whose recognized label is a TENOR
    ("10Y") rather than a real ISIN must map to whichever seeded bond's current
    years-to-maturity is closest (see services/market_view.py::find_bond_by_tenor) and
    actually apply the override to that bond -- not raise 'Unknown bond 10Y'."""
    extraction = _upload_bond_chart(client, isin_hint_text="10Y G-Sec 7.50%")
    client.post("/api/cv/correct", json={
        "extraction_id": extraction["id"],
        "corrected_fields": [{"instrument": "10Y", "metric": "yield", "value": 7.5, "unit": "pct", "confidence": 0.9, "source_region": None}],
    })
    r = client.post("/api/cv/commit", json={"extraction_id": extraction["id"], "target": "bond_yield", "instrument_id": "10Y"})
    assert r.status_code == 200
    body = r.json()
    assert body["instrument_id"] == "10Y"
    assert body["resolved_via_tenor_mapping"] is True
    assert body["resolved_isin"]  # a real ISIN, not "10Y" itself
    assert body["new_value"] == 7.5

    bonds = client.get("/api/bonds").json()
    resolved_bond = next(b for b in bonds if b["isin"] == body["resolved_isin"])
    assert resolved_bond["current_yield_pct"] == 7.5
    assert resolved_bond["is_cv_corrected"] is True

    client.delete("/api/cv/overrides")


def test_commit_by_unmappable_tenor_fails_gracefully_without_inventing_a_bond(client):
    """A tenor with no reasonably-close bond in the book must be honestly reported as
    unavailable -- never silently forced onto an unrelated bond, and never the old bare
    'Unknown bond' message. 50Y is used because it stays outside every seeded bond's
    tolerance band for the demo book's entire multi-year lifetime (unlike a tenor close to
    an existing bond's maturity, which can flip from unmappable to mappable in weeks as
    real time passes -- see test_market_view.py for the date-independent version of this
    same check with fixed, controlled inputs)."""
    extraction = _upload_bond_chart(client, isin_hint_text="50Y G-Sec 7.80%")
    client.post("/api/cv/correct", json={
        "extraction_id": extraction["id"],
        "corrected_fields": [{"instrument": "50Y", "metric": "yield", "value": 7.8, "unit": "pct", "confidence": 0.9, "source_region": None}],
    })
    r = client.post("/api/cv/commit", json={"extraction_id": extraction["id"], "target": "bond_yield", "instrument_id": "50Y"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "50Y" in detail
    assert "mapping unavailable" in detail.lower()


def test_fx_override_propagates_to_quotes_and_positions(client):
    pair = "USDINR"
    quotes_before = client.get("/api/fx/quotes").json()
    original_rate = next(q for q in quotes_before if q["pair"] == pair)["rate"]

    img = np.full((200, 400, 3), 255, dtype=np.uint8)
    cv2.putText(img, "USD/INR 99.99", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    extraction = client.post("/api/cv/extract", files={"file": ("chart.png", io.BytesIO(buf.tobytes()), "image/png")}).json()

    new_rate = original_rate + 5.0
    client.post("/api/cv/correct", json={
        "extraction_id": extraction["id"],
        "corrected_fields": [{"instrument": pair, "metric": "spot", "value": new_rate, "unit": "INR per unit", "confidence": 0.9, "source_region": None}],
    })
    r = client.post("/api/cv/commit", json={"extraction_id": extraction["id"], "target": "fx", "instrument_id": pair})
    assert r.status_code == 200
    assert r.json()["new_value"] == new_rate

    quotes_after = client.get("/api/fx/quotes").json()
    q_after = next(q for q in quotes_after if q["pair"] == pair)
    assert q_after["rate"] == new_rate
    assert q_after["is_cv_corrected"] is True

    positions = client.get("/api/fx/positions").json()
    pos = next((p for p in positions if p["pair"] == pair), None)
    if pos is not None:
        assert pos["current_rate"] == new_rate

    client.delete("/api/cv/overrides")
