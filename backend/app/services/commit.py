"""
Single code path that turns a validated market value into Treasury state (a MarketOverride row) and
reports what it changed. Used by BOTH the original Financial Image Intelligence commit
(api/cv.py) and the analyst-approved vision proposals (api/vision_review.py), so there is exactly
one way a CV-derived number can reach bond valuation, positions, risk and stress testing.

validate_market_value() never writes. apply_market_value() writes only after the caller has the
user's explicit approval.
"""
from __future__ import annotations

import math
from datetime import date

from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.finance.bonds import duration_convexity_dv01
from app.risk.aggregator import get_bond_positions, get_fx_positions
from app.services.market_view import effective_bond, effective_fx_rate, find_bond_by_tenor, tenor_to_years
from app.services.overrides import set_override

PLAUSIBLE_YIELD_PCT = (0.0, 25.0)
YIELD_JUMP_WARN_BP = 150.0
FX_JUMP_WARN_PCT = 3.0


class MarketValueError(ValueError):
    pass


def normalize_instrument(target: str, instrument_id: str) -> str:
    """OCR reads 'USD/INR'; the engine keys FX pairs as 'USDINR'. Bond ids/tenors are only trimmed."""
    s = instrument_id.strip()
    return s.upper().replace("/", "").replace(" ", "") if target == "fx" else s


def _resolve_bond(provider: MarketDataProvider, instrument_id: str):
    bond = next((b for b in provider.get_bonds() if b.isin == instrument_id), None)
    via_tenor = False
    if bond is None:
        years = tenor_to_years(instrument_id)
        if years is not None:
            bond = find_bond_by_tenor(provider.get_bonds(), years, date.today())
            via_tenor = bond is not None
    return bond, via_tenor


def validate_market_value(db: Session, provider: MarketDataProvider, target: str, instrument_id: str, value: float) -> dict:
    """Returns {ok, errors, warnings, requires_confirmation, previous_value, resolved_isin, ...}. Never writes."""
    instrument_id = normalize_instrument(target, instrument_id)
    errors: list[str] = []
    warnings: list[str] = []
    out: dict = {"target": target, "instrument_id": instrument_id, "value": value, "resolved_isin": None, "resolved_via_tenor": False, "previous_value": None, "unit": None}
    if value is None or isinstance(value, bool) or not math.isfinite(float(value)):
        return {**out, "ok": False, "errors": ["value is not a finite number"], "warnings": [], "requires_confirmation": False}
    value = float(value)
    if target == "bond_yield":
        out["unit"] = "pct"
        bond, via = _resolve_bond(provider, instrument_id)
        if bond is None:
            errors.append(f"'{instrument_id}' maps to no instrument in the pricing engine (no bond within tolerance of that tenor) -- mapping unavailable.")
        else:
            cur = effective_bond(db, provider, bond.isin).current_yield
            out.update(resolved_isin=bond.isin, resolved_via_tenor=via, previous_value=cur, delta_bps=round((value - cur) * 100, 1))
            if value < 0:
                errors.append("a negative yield is not accepted from image extraction")
            elif not (PLAUSIBLE_YIELD_PCT[0] <= value <= PLAUSIBLE_YIELD_PCT[1]):
                warnings.append(f"{value}% is outside the plausible yield range {PLAUSIBLE_YIELD_PCT} -- possibly a misread (e.g. a dropped decimal point).")
            if abs(value - cur) * 100 > YIELD_JUMP_WARN_BP:
                warnings.append(f"moves the yield by {abs(value - cur) * 100:.0f} bp from the current {cur:.4f}% (> {YIELD_JUMP_WARN_BP:.0f} bp).")
    elif target == "fx":
        out["unit"] = "INR per unit"
        cur = effective_fx_rate(db, provider, instrument_id)
        if cur is None:
            errors.append(f"unknown FX pair '{instrument_id}'")
        else:
            out.update(previous_value=cur, delta=round(value - cur, 6))
            if value <= 0:
                errors.append("FX rate must be positive")
            elif abs(value / cur - 1) * 100 > FX_JUMP_WARN_PCT:
                warnings.append(f"moves the rate {abs(value / cur - 1) * 100:.1f}% from the current {cur} (> {FX_JUMP_WARN_PCT}%).")
    else:
        errors.append(f"unsupported target '{target}'")
    return {**out, "ok": not errors, "errors": errors, "warnings": warnings, "requires_confirmation": bool(warnings) and not errors}


def apply_market_value(db: Session, provider: MarketDataProvider, target: str, instrument_id: str, value: float, source: str, cv_extraction_id: int | None = None) -> dict:
    """Writes the MarketOverride and returns before/after analytics (same shape the original commit returned)."""
    value = float(value)
    instrument_id = normalize_instrument(target, instrument_id)
    if target == "fx":
        previous = effective_fx_rate(db, provider, instrument_id)
        if previous is None:
            raise MarketValueError(f"Unknown FX pair {instrument_id}")
        set_override(db, "FX", instrument_id, "rate", value, source=source, cv_extraction_id=cv_extraction_id)
        affected = [{"pair": p.pair, "notional_base": p.notional_base, "pnl_inr": round(p.pnl, 2)} for p in get_fx_positions(db, provider) if p.pair == instrument_id]
        return {"instrument_id": instrument_id, "field": "spot rate", "previous_value": previous, "new_value": value, "delta": round(value - previous, 4), "affected_open_positions": affected}

    if target == "bond_yield":
        bond, via_tenor = _resolve_bond(provider, instrument_id)
        if bond is None:
            raise MarketValueError(f"Recognized tenor '{instrument_id}' (yield {value}%) has no closely-matching instrument in the Treasury pricing engine -- mapping unavailable for this tenor.")
        years = max(0.05, (date.fromisoformat(bond.maturity_date) - date.today()).days / 365.25)
        previous = effective_bond(db, provider, bond.isin).current_yield
        before = duration_convexity_dv01(bond.face, bond.coupon_rate, previous / 100.0, years, bond.frequency)
        after = duration_convexity_dv01(bond.face, bond.coupon_rate, value / 100.0, years, bond.frequency)
        set_override(db, "BOND", bond.isin, "yield_pct", value, source=source, cv_extraction_id=cv_extraction_id)
        affected = [{"isin": p.isin, "quantity_face": p.quantity, "market_value_before_inr": None, "market_value_after_inr": round(p.market_value, 2), "dv01_after_inr": round(p.dv01, 2)}
                    for p in get_bond_positions(db, provider) if p.isin == bond.isin]
        return {"instrument_id": instrument_id, "resolved_isin": bond.isin, "resolved_via_tenor_mapping": via_tenor, "field": "yield",
                "previous_value": previous, "new_value": value, "delta_bps": round((value - previous) * 100, 1),
                "clean_price_before": round(before.price, 4), "clean_price_after": round(after.price, 4), "modified_duration_after": round(after.modified_duration, 4),
                "convexity_after": round(after.convexity, 4), "dv01_per_100_face_after": round(after.dv01, 6), "affected_open_positions": affected}
    raise MarketValueError(f"Unsupported commit target {target}")
