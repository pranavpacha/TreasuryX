from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.fx import historical_volatility, log_returns
from app.finance.regime import classify_regime
from app.finance.risk_metrics import historical_var_es, max_drawdown
from app.risk.aggregator import get_bond_positions, get_fx_positions, portfolio_daily_returns

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/summary")
def risk_summary(
    confidence: float = settings.default_var_confidence,
    lookback_days: int = settings.default_var_lookback_days,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
):
    fx_views = get_fx_positions(db, provider)
    bond_views = get_bond_positions(db, provider)

    total_fx_exposure = sum(abs(v.notional_base * v.current_rate) for v in fx_views)
    total_fx_pnl = sum(v.pnl for v in fx_views)
    total_bond_dv01 = sum(v.dv01 for v in bond_views)
    total_bond_value = sum(v.market_value for v in bond_views)

    portfolio_value = sum(abs(v.notional_base * v.current_rate) for v in fx_views) + total_bond_value

    returns = portfolio_daily_returns(db, provider, lookback_days)
    var_es = None
    var_warning = None
    if len(returns) >= 20 and portfolio_value > 0:
        result = historical_var_es(returns, portfolio_value, confidence)
        var_es = {
            "var_amount_inr": round(result.var_amount, 2), "es_amount_inr": round(result.expected_shortfall, 2),
            "confidence": result.confidence, "horizon_days": result.horizon_days,
            "lookback_obs": result.lookback_obs, "method": result.method,
        }
    else:
        var_warning = "Insufficient position history or no open positions to compute historical VaR (need >=20 daily observations)."

    cum_pnl = np.cumsum(returns * portfolio_value) if len(returns) else np.array([])
    drawdown = max_drawdown(cum_pnl) if len(cum_pnl) else 0.0

    # Regime classification inputs from USDINR + curve
    fx_hist = [q.rate for q in provider.get_fx_history("USDINR", 60)]
    fx_vol = historical_volatility(np.array(fx_hist)) if len(fx_hist) > 2 else 0.0
    fx_rets = log_returns(np.array(fx_hist))
    fx_cum_return = float(np.sum(fx_rets[-20:])) if len(fx_rets) >= 20 else 0.0

    dates = provider.list_available_curve_dates()
    curve_now = {p.tenor: p.yield_pct for p in provider.get_yield_curve(dates[-1])}
    curve_prior = {p.tenor: p.yield_pct for p in provider.get_yield_curve(dates[max(0, len(dates) - 21)])}
    slope_now = curve_now.get("10Y", 0) - curve_now.get("2Y", 0)
    slope_prior = curve_prior.get("10Y", 0) - curve_prior.get("2Y", 0)
    slope_change_bps = (slope_now - slope_prior) * 100

    regime = classify_regime(fx_vol, fx_cum_return, slope_now * 100, slope_change_bps)

    return {
        "as_of": dates[-1] if dates else None,
        "fx_exposure_inr": round(total_fx_exposure, 2),
        "fx_pnl_inr": round(total_fx_pnl, 2),
        "bond_market_value_inr": round(total_bond_value, 2),
        "bond_dv01_inr_per_bp": round(total_bond_dv01, 2),
        "total_pnl_inr": round(total_fx_pnl, 2),
        "portfolio_value_inr": round(portfolio_value, 2),
        "var": var_es,
        "var_warning": var_warning,
        "max_drawdown_inr": round(float(drawdown), 2),
        "regime": regime.regime,
        "regime_reasons": regime.reasons,
        "risk_limits": {
            "fx_exposure_limit_inr": 1_000_000_000,
            "fx_exposure_utilization_pct": round(min(100, total_fx_exposure / 1_000_000_000 * 100), 1),
            "bond_dv01_limit_inr": 200_000,
            "bond_dv01_utilization_pct": round(min(100, abs(total_bond_dv01) / 200_000 * 100), 1),
        },
    }
