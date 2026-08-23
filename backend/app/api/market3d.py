"""
Data endpoints feeding the Three.js 3D visualizations. Every point returned here
is a real value produced by the finance engine / demo data -- no synthetic geometry
unrelated to the numbers (section 6.8 of the spec).
"""
from __future__ import annotations

from datetime import date

import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.fx import historical_volatility
from app.finance.scenario_engine import BondPositionInput, FxPositionInput, ShockInput, run_scenario
from app.models.position import Position

router = APIRouter(prefix="/api/market3d", tags=["market3d"])


@router.get("/yield-surface")
def yield_surface(n_dates: int = 30, provider: MarketDataProvider = Depends(get_provider)):
    dates = provider.list_available_curve_dates()[-n_dates:]
    points = []
    for d in dates:
        for p in provider.get_yield_curve(d):
            points.append({"date": d, "tenor": p.tenor, "years": p.years, "yield_pct": p.yield_pct})
    return {"dates": dates, "points": points}


@router.get("/fx-vol-surface")
def fx_vol_surface(provider: MarketDataProvider = Depends(get_provider)):
    pairs = ["USDINR", "EURINR", "GBPINR", "EURUSD"]
    windows = [10, 20, 30, 60, 90, 120]
    points = []
    for pair in pairs:
        hist = [q.rate for q in provider.get_fx_history(pair, max(windows) + 5)]
        for w in windows:
            if len(hist) > w:
                vol = historical_volatility(np.array(hist[-(w + 1):]))
                points.append({"pair": pair, "window_days": w, "annualized_vol_pct": round(vol * 100, 3)})
    return {"pairs": pairs, "windows": windows, "points": points}


@router.get("/stress-surface")
def stress_surface(
    fx_min: float = -5, fx_max: float = 5, fx_steps: int = 9,
    yield_min: float = -100, yield_max: float = 100, yield_steps: int = 9,
    db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider),
):
    latest_fx = {q.pair: q.rate for q in provider.get_all_fx_latest()}
    bonds_by_isin = {b.isin: b for b in provider.get_bonds()}

    fx_inputs = []
    for pos in db.query(Position).filter(Position.instrument_type == "FX", Position.status == "OPEN").all():
        rate = latest_fx.get(pos.instrument_id)
        if rate is not None:
            fx_inputs.append(FxPositionInput(pair=pos.instrument_id, notional_base=pos.quantity, entry_rate=pos.entry_price, current_rate=rate))

    bond_inputs = []
    for pos in db.query(Position).filter(Position.instrument_type == "BOND", Position.status == "OPEN").all():
        b = bonds_by_isin.get(pos.instrument_id)
        if b is not None:
            years = max(0.05, (date.fromisoformat(b.maturity_date) - date.today()).days / 365.25)
            bond_inputs.append(BondPositionInput(
                isin=b.isin, face=b.face, coupon_rate=b.coupon_rate, current_yield=b.current_yield / 100.0,
                years_to_maturity=years, frequency=b.frequency, quantity=pos.quantity,
            ))

    fx_shocks = np.linspace(fx_min, fx_max, fx_steps) / 100.0
    yield_shocks = np.linspace(yield_min, yield_max, yield_steps)

    grid = []
    for fx_shock in fx_shocks:
        fx_shock_map = {pair: float(fx_shock) for pair in latest_fx.keys()} if fx_inputs else {}
        for y_shock in yield_shocks:
            shock = ShockInput(fx_shock_pct=fx_shock_map, parallel_yield_shock_bps=float(y_shock))
            result = run_scenario(fx_inputs, bond_inputs, shock)
            grid.append({
                "fx_shock_pct": round(float(fx_shock) * 100, 2),
                "yield_shock_bps": round(float(y_shock), 1),
                "total_pnl_inr": round(result.total_pnl, 2),
            })

    return {"grid": grid, "has_positions": bool(fx_inputs or bond_inputs)}
