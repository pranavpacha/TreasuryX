from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.data.provider import MarketDataProvider
from app.dependencies import get_provider
from app.finance.bonds import BondError, clean_price, duration_convexity_dv01, ytm

router = APIRouter(prefix="/api/bonds", tags=["bonds"])


def _years_to_maturity(maturity_date: str) -> float:
    m = date.fromisoformat(maturity_date)
    return max(0.01, (m - date.today()).days / 365.25)


@router.get("")
def list_bonds(provider: MarketDataProvider = Depends(get_provider)):
    out = []
    for b in provider.get_bonds():
        ytm_yrs = _years_to_maturity(b.maturity_date)
        y = b.current_yield / 100.0
        try:
            result = duration_convexity_dv01(b.face, b.coupon_rate, y, ytm_yrs, b.frequency)
        except BondError as exc:
            raise HTTPException(400, str(exc)) from exc
        out.append({
            "isin": b.isin, "name": b.name, "coupon_rate_pct": b.coupon_rate * 100,
            "maturity_date": b.maturity_date, "years_to_maturity": round(ytm_yrs, 2),
            "current_yield_pct": b.current_yield, "clean_price": round(result.price, 4),
            "modified_duration": round(result.modified_duration, 4),
            "macaulay_duration": round(result.macaulay_years, 4),
            "convexity": round(result.convexity, 4),
            "dv01_per_100_face": round(result.dv01, 6),
        })
    return out


@router.get("/{isin}/history")
def bond_history(isin: str, lookback_days: int = 250, provider: MarketDataProvider = Depends(get_provider)):
    rows = provider.get_bond_yield_history(isin, lookback_days)
    if not rows:
        raise HTTPException(404, f"No history for {isin}")
    bond = next((b for b in provider.get_bonds() if b.isin == isin), None)
    if bond is None:
        raise HTTPException(404, f"Unknown bond {isin}")
    ytm_yrs = _years_to_maturity(bond.maturity_date)
    out = []
    for d, y in rows:
        price = clean_price(bond.face, bond.coupon_rate, y, ytm_yrs, bond.frequency)
        out.append({"date": d, "yield_pct": round(y * 100, 4), "clean_price": round(price, 4)})
    return out


@router.get("/{isin}/ytm")
def bond_ytm(isin: str, price: float, provider: MarketDataProvider = Depends(get_provider)):
    bond = next((b for b in provider.get_bonds() if b.isin == isin), None)
    if bond is None:
        raise HTTPException(404, f"Unknown bond {isin}")
    ytm_yrs = _years_to_maturity(bond.maturity_date)
    try:
        y = ytm(price, bond.face, bond.coupon_rate, ytm_yrs, bond.frequency)
    except BondError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"isin": isin, "price": price, "solved_ytm_pct": round(y * 100, 4)}
