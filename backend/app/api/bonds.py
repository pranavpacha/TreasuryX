from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.bonds import BondError, clean_price, duration_convexity_dv01, ytm
from app.services.market_view import effective_bond, effective_bonds
from app.services.overrides import get_overrides_map

router = APIRouter(prefix="/api/bonds", tags=["bonds"])


def _years_to_maturity(maturity_date: str) -> float:
    m = date.fromisoformat(maturity_date)
    return max(0.01, (m - date.today()).days / 365.25)


@router.get("")
def list_bonds(db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    overridden = set(get_overrides_map(db, "BOND", "yield_pct").keys())
    out = []
    for b in effective_bonds(db, provider):
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
            "is_cv_corrected": b.isin in overridden,
        })
    return out


@router.get("/{isin}/history")
def bond_history(isin: str, lookback_days: int = 250, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    rows = provider.get_bond_yield_history(isin, lookback_days)
    if not rows:
        raise HTTPException(404, f"No history for {isin}")
    bond = effective_bond(db, provider, isin)
    if bond is None:
        raise HTTPException(404, f"Unknown bond {isin}")
    ytm_yrs = _years_to_maturity(bond.maturity_date)
    out = []
    for d, y in rows:
        price = clean_price(bond.face, bond.coupon_rate, y, ytm_yrs, bond.frequency)
        out.append({"date": d, "yield_pct": round(y * 100, 4), "clean_price": round(price, 4)})
    # If a CV-corrected current yield is active, append it as the latest point so the chart
    # visibly reflects the applied correction.
    override = get_overrides_map(db, "BOND", "yield_pct").get(isin)
    if override is not None:
        price = clean_price(bond.face, bond.coupon_rate, override / 100.0, ytm_yrs, bond.frequency)
        out.append({"date": date.today().isoformat(), "yield_pct": round(override, 4), "clean_price": round(price, 4), "is_cv_corrected": True})
    return out


@router.get("/{isin}/ytm")
def bond_ytm(isin: str, price: float, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    bond = effective_bond(db, provider, isin)
    if bond is None:
        raise HTTPException(404, f"Unknown bond {isin}")
    ytm_yrs = _years_to_maturity(bond.maturity_date)
    try:
        y = ytm(price, bond.face, bond.coupon_rate, ytm_yrs, bond.frequency)
    except BondError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"isin": isin, "price": price, "solved_ytm_pct": round(y * 100, 4)}
