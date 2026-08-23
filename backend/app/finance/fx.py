"""
FX analytics: mark-to-market P&L, returns, and historical volatility.

Quote convention
-----------------
All pairs are quoted as BASE/QUOTE, e.g. USD/INR = INR per 1 USD.
A "long" position means long the BASE currency (bought USD, will sell later).
A "short" position means short the BASE currency (sold USD, must buy back later).

Position sign convention
-------------------------
`notional_base` is signed: positive = long base currency, negative = short base currency.
This keeps a single P&L formula valid for both directions (see fx_pnl).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FxPnlResult:
    entry_rate: float
    current_rate: float
    notional_base: float
    pnl_quote_ccy: float
    return_pct: float


def fx_pnl(entry_rate: float, current_rate: float, notional_base: float) -> FxPnlResult:
    """Mark-to-market P&L on a spot FX position, in quote-currency terms.

    P&L = (current_rate - entry_rate) * notional_base

    A positive `notional_base` (long base ccy) profits when the rate rises.
    A negative `notional_base` (short base ccy) profits when the rate falls.
    """
    if entry_rate <= 0 or current_rate <= 0:
        raise ValueError("FX rates must be positive")
    pnl = (current_rate - entry_rate) * notional_base
    ret = (current_rate - entry_rate) / entry_rate
    return FxPnlResult(
        entry_rate=entry_rate,
        current_rate=current_rate,
        notional_base=notional_base,
        pnl_quote_ccy=pnl,
        return_pct=ret,
    )


def log_returns(prices: np.ndarray) -> np.ndarray:
    """Log returns r_t = ln(P_t / P_{t-1}). Used for volatility (additive, better-behaved
    than simple returns for aggregation over time)."""
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 2:
        return np.array([])
    if np.any(prices <= 0):
        raise ValueError("Prices must be positive to compute log returns")
    return np.diff(np.log(prices))


def simple_returns(prices: np.ndarray) -> np.ndarray:
    """Simple returns r_t = (P_t - P_{t-1}) / P_{t-1}. Used for P&L / VaR aggregation
    since simple returns compose linearly with notional exposure."""
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 2:
        return np.array([])
    return np.diff(prices) / prices[:-1]


TRADING_DAYS_PER_YEAR = 252


def historical_volatility(prices: np.ndarray, annualize: bool = True, window: int | None = None) -> float:
    """Historical (realized) volatility from a price series.

    Methodology:
      1. Compute log returns over the observation window (most recent `window` prices).
      2. Daily volatility = sample standard deviation of those returns (ddof=1).
      3. If `annualize`, scale by sqrt(252) trading days (square-root-of-time rule,
         assumes i.i.d. returns -- a standard simplification).

    Returns 0.0 if fewer than 2 observations are available.
    """
    prices = np.asarray(prices, dtype=float)
    if window is not None and len(prices) > window + 1:
        prices = prices[-(window + 1):]
    rets = log_returns(prices)
    if len(rets) < 2:
        return 0.0
    daily_vol = float(np.std(rets, ddof=1))
    if annualize:
        return daily_vol * np.sqrt(TRADING_DAYS_PER_YEAR)
    return daily_vol
