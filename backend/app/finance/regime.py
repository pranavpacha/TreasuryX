"""
Rule-based market-regime classification (decision-support signal, NOT a prediction).

This is intentionally a documented, deterministic rule set -- not a trained ML model --
so its behaviour is fully explainable, which matters more for a Treasury decision-support
tool than raw predictive accuracy. See docs/finance_methodology.md for the full rule table.

Inputs are recent (already-realized, backward-looking) statistics only: no future data
is used, avoiding look-ahead bias.
"""
from __future__ import annotations

from dataclasses import dataclass

VOL_HIGH_THRESHOLD_ANNUALIZED = 0.10  # 10% annualized FX vol
CURVE_SLOPE_STEEP_BPS = 20.0  # 10Y-2Y slope change considered a steepening/flattening signal
FX_TREND_THRESHOLD = 0.01  # 1% cumulative move over lookback considered a trend


@dataclass(frozen=True)
class RegimeResult:
    regime: str
    reasons: list[str]


def classify_regime(
    fx_annualized_vol: float,
    fx_cum_return: float,
    curve_slope_bps: float,
    curve_slope_change_bps: float,
) -> RegimeResult:
    """
    Rules (evaluated in order, first match wins for the primary label; all matched
    reasons are still reported):

    1. HIGH-VOLATILITY: fx_annualized_vol > 10%
    2. CURVE-STEEPENING / CURVE-FLATTENING: |curve_slope_change_bps| > 20bps
    3. RATES-UP / RATES-DOWN: driven by sign of curve_slope_change_bps when curve is
       shifting broadly (both ends moving together) -- approximated here via slope level
    4. RISK-OFF: FX cumulative return < -1% (base currency weakening sharply) combined
       with rising vol
    5. RISK-ON: FX cumulative return > +1% with contained vol
    6. NORMAL: none of the above triggered
    """
    reasons: list[str] = []

    if fx_annualized_vol > VOL_HIGH_THRESHOLD_ANNUALIZED:
        reasons.append(f"FX annualized volatility {fx_annualized_vol:.1%} > {VOL_HIGH_THRESHOLD_ANNUALIZED:.0%} threshold")
        primary = "HIGH-VOLATILITY"
    elif curve_slope_change_bps > CURVE_SLOPE_STEEP_BPS:
        reasons.append(f"10Y-2Y slope widened by {curve_slope_change_bps:.0f}bp")
        primary = "CURVE-STEEPENING"
    elif curve_slope_change_bps < -CURVE_SLOPE_STEEP_BPS:
        reasons.append(f"10Y-2Y slope narrowed by {curve_slope_change_bps:.0f}bp")
        primary = "CURVE-FLATTENING"
    elif fx_cum_return < -FX_TREND_THRESHOLD:
        reasons.append(f"Base currency cumulative return {fx_cum_return:.2%} < -{FX_TREND_THRESHOLD:.0%}")
        primary = "RISK-OFF"
    elif fx_cum_return > FX_TREND_THRESHOLD:
        reasons.append(f"Base currency cumulative return {fx_cum_return:.2%} > +{FX_TREND_THRESHOLD:.0%}")
        primary = "RISK-ON"
    else:
        reasons.append("No threshold breached over lookback window")
        primary = "NORMAL"

    return RegimeResult(regime=primary, reasons=reasons)
