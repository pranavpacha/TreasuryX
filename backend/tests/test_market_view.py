"""
Pure, date-independent tests for the tenor<->bond fuzzy-matching mechanism used when a CV
extraction recognizes a TENOR ("10Y") rather than a real ISIN (see
app/api/cv.py::commit's bond_yield branch). Unlike the live-API integration tests in
test_integration_cv_to_treasury.py, everything here uses fixed bonds and a fixed `as_of`
date, so it can never become flaky as real-world time passes and the demo bonds age
relative to "today" -- the exact class of bug this mapping was designed to avoid (see the
bond near-maturity rounding fix in finance/bonds.py).
"""
from __future__ import annotations

from datetime import date

from app.data.provider import BondStatic
from app.services.market_view import find_bond_by_tenor, tenor_to_years


def _bond(isin: str, maturity_date: str) -> BondStatic:
    return BondStatic(
        isin=isin, name=isin, face=100.0, coupon_rate=0.07, maturity_date=maturity_date,
        frequency=2, issue_date="2020-01-01", current_yield=7.0,
    )


AS_OF = date(2026, 9, 28)
BONDS = [
    _bond("SHORT", "2026-12-15"),  # ~0.2y from AS_OF
    _bond("MID", "2033-07-24"),    # ~6.8y from AS_OF
    _bond("TEN", "2036-06-22"),    # ~9.7y from AS_OF
    _bond("LONG", "2053-06-19"),   # ~26.7y from AS_OF
]


def test_tenor_to_years_parses_months_and_years():
    assert tenor_to_years("3M") == 0.25
    assert tenor_to_years("6M") == 0.5
    assert tenor_to_years("1Y") == 1.0
    assert tenor_to_years("10Y") == 10.0
    assert tenor_to_years("30y") == 30.0  # case-insensitive


def test_tenor_to_years_rejects_non_tenor_strings():
    assert tenor_to_years("IN0020240001") is None
    assert tenor_to_years("USD/INR") is None
    assert tenor_to_years("") is None


def test_find_bond_by_tenor_matches_closest_bond_within_tolerance():
    match = find_bond_by_tenor(BONDS, tenor_to_years("10Y"), AS_OF)
    assert match is not None
    assert match.isin == "TEN"


def test_find_bond_by_tenor_matches_short_tenor_to_near_maturity_bond():
    match = find_bond_by_tenor(BONDS, tenor_to_years("3M"), AS_OF)
    assert match is not None
    assert match.isin == "SHORT"


def test_find_bond_by_tenor_returns_none_when_nothing_is_close_enough():
    # 50Y is far outside every bond's tolerance band regardless of how BONDS ages.
    assert find_bond_by_tenor(BONDS, tenor_to_years("50Y"), AS_OF) is None


def test_find_bond_by_tenor_excludes_already_matured_bonds():
    matured = [_bond("DEAD", "2020-01-01")]  # matured long before AS_OF
    assert find_bond_by_tenor(matured, tenor_to_years("1Y"), AS_OF) is None


def test_find_bond_by_tenor_never_invents_an_isin():
    # Even when nothing matches, the function must return None, never a bond object
    # constructed from the tenor string itself.
    result = find_bond_by_tenor(BONDS, tenor_to_years("50Y"), AS_OF)
    assert result is None or isinstance(result, BondStatic)
