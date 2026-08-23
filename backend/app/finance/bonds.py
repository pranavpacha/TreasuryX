"""
Fixed-coupon government bond analytics: pricing, YTM, duration, convexity, DV01.

Conventions (documented simplifications for an educational pricer)
--------------------------------------------------------------------
- Face value: par = 100 (or a supplied face value).
- Coupon: paid `frequency` times per year, coupon_rate is the ANNUAL coupon rate.
- Yield: `yield_rate` is an annual (nominal, compounded `frequency` times/yr) yield.
- Day-count: periods are treated as equal-length (Act/Act-style fractional periods
  via `settle_frac`), NOT a full Act/Act or 30/360 calendar implementation.
- Clean price = price assuming valuation exactly on a coupon date (settle_frac=0),
  OR dirty price minus accrued interest when settle_frac > 0.
- Duration / Modified Duration / Convexity / DV01 are computed assuming valuation
  ON a coupon date (settle_frac=0) to keep the formulas standard and testable;
  this is the conventional simplification used in most teaching bond pricers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


class BondError(ValueError):
    pass


def _num_periods(years_to_maturity: float, frequency: int) -> int:
    n = round(years_to_maturity * frequency)
    if n < 1:
        raise BondError("Bond has no remaining coupon periods (already matured)")
    return int(n)


def _cash_flows(face: float, coupon_rate: float, frequency: int, n: int) -> np.ndarray:
    coupon = face * coupon_rate / frequency
    cfs = np.full(n, coupon, dtype=float)
    cfs[-1] += face
    return cfs


def bond_price(
    face: float,
    coupon_rate: float,
    yield_rate: float,
    years_to_maturity: float,
    frequency: int = 2,
    settle_frac: float = 0.0,
) -> float:
    """Present value of a fixed-coupon bond (dirty price if settle_frac > 0).

    Price = sum_{k=1..n} CF_k / (1 + y/f)^(k - settle_frac)

    `settle_frac` in [0, 1) is how far the valuation date sits into the CURRENT
    coupon period (0 = on a coupon date, 0.5 = halfway to the next coupon).
    """
    if face <= 0:
        raise BondError("Face value must be positive")
    if frequency <= 0:
        raise BondError("Coupon frequency must be positive")
    if years_to_maturity <= 0:
        raise BondError("Years to maturity must be positive")
    if yield_rate <= -1:
        raise BondError("Yield rate is not economically valid (<=-100%)")
    if not (0.0 <= settle_frac < 1.0):
        raise BondError("settle_frac must be in [0, 1)")

    n = _num_periods(years_to_maturity, frequency)
    cfs = _cash_flows(face, coupon_rate, frequency, n)
    periods = np.arange(1, n + 1) - settle_frac
    disc = (1 + yield_rate / frequency) ** periods
    return float(np.sum(cfs / disc))


def accrued_interest(face: float, coupon_rate: float, frequency: int, settle_frac: float) -> float:
    """Accrued interest = coupon-per-period * fraction of period elapsed."""
    coupon = face * coupon_rate / frequency
    return coupon * settle_frac


def clean_price(
    face: float, coupon_rate: float, yield_rate: float, years_to_maturity: float,
    frequency: int = 2, settle_frac: float = 0.0,
) -> float:
    dirty = bond_price(face, coupon_rate, yield_rate, years_to_maturity, frequency, settle_frac)
    return dirty - accrued_interest(face, coupon_rate, frequency, settle_frac)


def ytm(
    price: float, face: float, coupon_rate: float, years_to_maturity: float, frequency: int = 2,
) -> float:
    """Solve for the annual yield that reprices the bond to `price` (dirty, settle_frac=0)
    using Brent's method (robust bracketed root-finder, no derivative needed).

    Raises BondError if the price is not economically achievable (e.g. <= 0, or
    no sign change found in a wide bracket) or the solver fails to converge.
    """
    if price <= 0:
        raise BondError("Price must be positive")

    def f(y: float) -> float:
        return bond_price(face, coupon_rate, y, years_to_maturity, frequency) - price

    lo, hi = -0.99, 5.0
    f_lo, f_hi = f(lo), f(hi)
    if f_lo * f_hi > 0:
        raise BondError(
            "No solution found for YTM in bracket [-99%, 500%] -- check price/coupon inputs"
        )
    try:
        result = brentq(f, lo, hi, xtol=1e-10, maxiter=200)
    except (RuntimeError, ValueError) as exc:
        raise BondError(f"YTM did not converge: {exc}") from exc
    return float(result)


@dataclass(frozen=True)
class DurationResult:
    macaulay_years: float
    modified_duration: float
    convexity: float
    dv01: float
    price: float


def macaulay_duration(
    face: float, coupon_rate: float, yield_rate: float, years_to_maturity: float, frequency: int = 2,
) -> float:
    """Macaulay duration (years) = weighted-average time to cash flows, weights = PV(CF)/Price.
    Valuation assumed on a coupon date (t=0)."""
    n = _num_periods(years_to_maturity, frequency)
    cfs = _cash_flows(face, coupon_rate, frequency, n)
    periods = np.arange(1, n + 1)
    disc = (1 + yield_rate / frequency) ** periods
    pv = cfs / disc
    price = float(np.sum(pv))
    weighted_time_periods = float(np.sum(periods * pv)) / price
    return weighted_time_periods / frequency


def duration_convexity_dv01(
    face: float, coupon_rate: float, yield_rate: float, years_to_maturity: float,
    frequency: int = 2, bump: float = 1e-4,
) -> DurationResult:
    """Modified duration, convexity and DV01 via numerical bump-and-reprice
    (central finite differences) against `bond_price`, guaranteeing consistency
    with the pricing model actually used (rather than a separately-derived
    closed-form that could silently diverge from it).

      P0    = price(y)
      P_up  = price(y + bump)
      P_dn  = price(y - bump)

      Modified Duration  = -(P_up - P_dn) / (2 * bump * P0)      [years]
      Convexity          = (P_up + P_dn - 2*P0) / (bump^2 * P0)  [years^2]
      DV01               = (P_dn - P_up) / 2                     [price impact of 1bp,
                                                                    bump is expressed in
                                                                    decimal yield units]

    `bump` defaults to 1e-4 (1 basis point).
    """
    p0 = bond_price(face, coupon_rate, yield_rate, years_to_maturity, frequency)
    p_up = bond_price(face, coupon_rate, yield_rate + bump, years_to_maturity, frequency)
    p_dn = bond_price(face, coupon_rate, yield_rate - bump, years_to_maturity, frequency)

    mod_dur = -(p_up - p_dn) / (2 * bump * p0)
    convexity = (p_up + p_dn - 2 * p0) / (bump ** 2 * p0)
    dv01_per_bp = (p_dn - p_up) / 2 * (1e-4 / bump)

    return DurationResult(
        macaulay_years=macaulay_duration(face, coupon_rate, yield_rate, years_to_maturity, frequency),
        modified_duration=mod_dur,
        convexity=convexity,
        dv01=dv01_per_bp,
        price=p0,
    )


def duration_based_price_change(modified_duration: float, convexity: float, price: float, dy: float) -> float:
    """Second-order (duration + convexity) approximation of price change for a yield
    move `dy` (decimal, e.g. 0.0025 for +25bp):

      dP/P ~= -ModDur * dy + 0.5 * Convexity * dy^2
    """
    return price * (-modified_duration * dy + 0.5 * convexity * dy ** 2)


def exact_reprice_change(
    face: float, coupon_rate: float, yield_rate: float, years_to_maturity: float, frequency: int, dy: float,
) -> float:
    """Exact price change from full repricing at the shocked yield -- used to show
    students the gap between the duration/convexity approximation and reality."""
    p0 = bond_price(face, coupon_rate, yield_rate, years_to_maturity, frequency)
    p1 = bond_price(face, coupon_rate, yield_rate + dy, years_to_maturity, frequency)
    return p1 - p0
