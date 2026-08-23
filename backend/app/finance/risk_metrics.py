"""
Historical VaR and Expected Shortfall.

Methodology
-----------
- Uses HISTORICAL simple returns (not parametric/normal assumption).
- No look-ahead bias: callers must pass only returns observed strictly BEFORE the
  evaluation date (enforced by the caller slicing the price history before computing
  returns -- see `risk/aggregator.py`).
- 1-day horizon. VaR/ES are reported as POSITIVE loss numbers in currency units.
- Sign convention: a loss is a negative return; VaR is the (positive) magnitude of the
  loss at the given confidence level's lower tail.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class RiskError(ValueError):
    pass


@dataclass(frozen=True)
class VarResult:
    confidence: float
    horizon_days: int
    lookback_obs: int
    var_amount: float
    expected_shortfall: float
    method: str = "historical"


def historical_var_es(
    returns: np.ndarray, portfolio_value: float, confidence: float = 0.95, horizon_days: int = 1,
) -> VarResult:
    """1-day historical VaR and Expected Shortfall on a portfolio value.

    VaR_alpha  = -Percentile(returns, 100*(1-alpha)) * portfolio_value
    ES_alpha   = -mean(returns <= Percentile(returns, 100*(1-alpha))) * portfolio_value

    `returns` should be simple daily returns of the portfolio (or a proxy series).
    Requires at least 20 observations for a minimally meaningful empirical tail.
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    if not (0.5 < confidence < 1.0):
        raise RiskError("confidence must be between 0.5 and 1.0")
    if len(returns) < 20:
        raise RiskError(f"Need at least 20 return observations for historical VaR, got {len(returns)}")
    if portfolio_value < 0:
        raise RiskError("portfolio_value must be non-negative")

    tail_pct = (1 - confidence) * 100
    cutoff = float(np.percentile(returns, tail_pct, method="lower"))
    tail_losses = returns[returns <= cutoff]
    if len(tail_losses) == 0:
        tail_losses = np.array([cutoff])

    var_amount = -cutoff * portfolio_value * np.sqrt(horizon_days)
    es_amount = -float(np.mean(tail_losses)) * portfolio_value * np.sqrt(horizon_days)

    return VarResult(
        confidence=confidence,
        horizon_days=horizon_days,
        lookback_obs=len(returns),
        var_amount=max(var_amount, 0.0),
        expected_shortfall=max(es_amount, 0.0),
    )


def max_drawdown(cumulative_pnl: np.ndarray) -> float:
    """Maximum peak-to-trough drawdown of a cumulative P&L / equity series."""
    cumulative_pnl = np.asarray(cumulative_pnl, dtype=float)
    if len(cumulative_pnl) == 0:
        return 0.0
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = cumulative_pnl - running_max
    return float(np.min(drawdowns))
