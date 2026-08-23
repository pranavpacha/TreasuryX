"""
Deterministic scenario / stress-testing engine.

Given a set of FX and yield shocks plus the current portfolio (FX positions +
bond holdings), recompute shocked market levels, reprice every position, and
aggregate P&L. Entirely deterministic -- no randomness, no ML, no AI-generated
numbers, as required by the project spec (section 18).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.finance.bonds import duration_based_price_change, duration_convexity_dv01, exact_reprice_change
from app.finance.fx import fx_pnl


@dataclass
class FxPositionInput:
    pair: str
    notional_base: float
    entry_rate: float
    current_rate: float


@dataclass
class BondPositionInput:
    isin: str
    face: float
    coupon_rate: float
    current_yield: float
    years_to_maturity: float
    frequency: int
    quantity: float  # number of bonds (face-value units) held, signed


@dataclass
class ShockInput:
    fx_shock_pct: dict[str, float] = field(default_factory=dict)  # pair -> +/- fraction, e.g. 0.02
    parallel_yield_shock_bps: float = 0.0
    curve_tilt_bps: float = 0.0  # positive = steepening (long end up more), negative = flattening
    per_bond_yield_shock_bps: dict[str, float] = field(default_factory=dict)  # isin -> extra bps


@dataclass
class ScenarioResult:
    fx_pnl_by_pair: dict[str, float]
    bond_pnl_by_isin: dict[str, float]
    bond_pnl_exact_by_isin: dict[str, float]
    total_fx_pnl: float
    total_bond_pnl: float
    total_pnl: float
    shocked_fx_rates: dict[str, float]
    shocked_bond_yields: dict[str, float]


def run_scenario(
    fx_positions: list[FxPositionInput],
    bond_positions: list[BondPositionInput],
    shock: ShockInput,
) -> ScenarioResult:
    fx_pnl_by_pair: dict[str, float] = {}
    shocked_fx_rates: dict[str, float] = {}
    for pos in fx_positions:
        shock_pct = shock.fx_shock_pct.get(pos.pair, 0.0)
        shocked_rate = pos.current_rate * (1 + shock_pct)
        shocked_fx_rates[pos.pair] = shocked_rate
        base_pnl = fx_pnl(pos.entry_rate, pos.current_rate, pos.notional_base).pnl_quote_ccy
        shocked_pnl = fx_pnl(pos.entry_rate, shocked_rate, pos.notional_base).pnl_quote_ccy
        incremental = shocked_pnl - base_pnl
        fx_pnl_by_pair[pos.pair] = fx_pnl_by_pair.get(pos.pair, 0.0) + incremental

    bond_pnl_by_isin: dict[str, float] = {}
    bond_pnl_exact_by_isin: dict[str, float] = {}
    shocked_bond_yields: dict[str, float] = {}
    # Curve tilt: long maturities move more than short. Pivot at 5Y for simplicity.
    for pos in bond_positions:
        tilt = shock.curve_tilt_bps * ((pos.years_to_maturity - 5.0) / 10.0)
        extra = shock.per_bond_yield_shock_bps.get(pos.isin, 0.0)
        dy_bps = shock.parallel_yield_shock_bps + tilt + extra
        dy = dy_bps / 10000.0
        shocked_yield = pos.current_yield + dy
        shocked_bond_yields[pos.isin] = shocked_yield

        dur = duration_convexity_dv01(pos.face, pos.coupon_rate, pos.current_yield, pos.years_to_maturity, pos.frequency)
        approx_dp = duration_based_price_change(dur.modified_duration, dur.convexity, dur.price, dy)
        exact_dp = exact_reprice_change(pos.face, pos.coupon_rate, pos.current_yield, pos.years_to_maturity, pos.frequency, dy)

        units = pos.quantity / pos.face  # number of face-value blocks
        bond_pnl_by_isin[pos.isin] = bond_pnl_by_isin.get(pos.isin, 0.0) + approx_dp * units
        bond_pnl_exact_by_isin[pos.isin] = bond_pnl_exact_by_isin.get(pos.isin, 0.0) + exact_dp * units

    total_fx = sum(fx_pnl_by_pair.values())
    total_bond = sum(bond_pnl_exact_by_isin.values())

    return ScenarioResult(
        fx_pnl_by_pair=fx_pnl_by_pair,
        bond_pnl_by_isin=bond_pnl_by_isin,
        bond_pnl_exact_by_isin=bond_pnl_exact_by_isin,
        total_fx_pnl=total_fx,
        total_bond_pnl=total_bond,
        total_pnl=total_fx + total_bond,
        shocked_fx_rates=shocked_fx_rates,
        shocked_bond_yields=shocked_bond_yields,
    )
