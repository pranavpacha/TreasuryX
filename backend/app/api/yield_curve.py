from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.data.provider import MarketDataProvider
from app.dependencies import get_provider

router = APIRouter(prefix="/api/yield-curve", tags=["yield-curve"])


@router.get("/dates")
def available_dates(provider: MarketDataProvider = Depends(get_provider)):
    return provider.list_available_curve_dates()


@router.get("")
def get_curve(as_of: str | None = None, provider: MarketDataProvider = Depends(get_provider)):
    try:
        points = provider.get_yield_curve(as_of)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return [{"tenor": p.tenor, "years": p.years, "yield_pct": p.yield_pct, "date": p.date} for p in points]


@router.get("/compare")
def compare_curves(date1: str, date2: str, provider: MarketDataProvider = Depends(get_provider)):
    try:
        c1 = provider.get_yield_curve(date1)
        c2 = provider.get_yield_curve(date2)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    m1 = {p.tenor: p.yield_pct for p in c1}
    m2 = {p.tenor: p.yield_pct for p in c2}
    tenors = [p.tenor for p in sorted(c1, key=lambda p: p.years)]
    diffs = [{"tenor": t, "date1_pct": m1.get(t), "date2_pct": m2.get(t), "shift_bps": round((m2.get(t, 0) - m1.get(t, 0)) * 100, 2)} for t in tenors]

    slope1 = m1.get("10Y", 0) - m1.get("2Y", 0)
    slope2 = m2.get("10Y", 0) - m2.get("2Y", 0)
    slope_change_bps = round((slope2 - slope1) * 100, 2)
    classification = "STEEPENING" if slope_change_bps > 2 else ("FLATTENING" if slope_change_bps < -2 else "STABLE")

    return {
        "date1": date1, "date2": date2, "points": diffs,
        "slope_10y_2y_date1_pct": round(slope1, 4), "slope_10y_2y_date2_pct": round(slope2, 4),
        "slope_change_bps": slope_change_bps, "classification": classification,
    }
