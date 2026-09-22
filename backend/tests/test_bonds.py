import pytest

from app.finance.bonds import (
    BondError,
    accrued_interest,
    bond_price,
    clean_price,
    duration_based_price_change,
    duration_convexity_dv01,
    exact_reprice_change,
    macaulay_duration,
    ytm,
)


def test_par_bond_prices_at_par():
    # Coupon rate == yield => price should equal face value exactly (par bond)
    price = bond_price(face=100, coupon_rate=0.07, yield_rate=0.07, years_to_maturity=10, frequency=2)
    assert price == pytest.approx(100.0, abs=1e-8)


def test_premium_bond_priced_above_par_when_coupon_gt_yield():
    price = bond_price(face=100, coupon_rate=0.08, yield_rate=0.06, years_to_maturity=10, frequency=2)
    assert price > 100


def test_discount_bond_priced_below_par_when_coupon_lt_yield():
    price = bond_price(face=100, coupon_rate=0.05, yield_rate=0.07, years_to_maturity=10, frequency=2)
    assert price < 100


def test_bond_price_manual_reference_2yr_annual():
    # Manual calc: face=100, coupon=6% annual, yield=5%, 2y, freq=1
    # P = 6/1.05 + 106/1.05^2 = 5.714285... + 96.145... = 101.8594...
    expected = 6 / 1.05 + 106 / 1.05 ** 2
    price = bond_price(face=100, coupon_rate=0.06, yield_rate=0.05, years_to_maturity=2, frequency=1)
    assert price == pytest.approx(expected, rel=1e-9)


def test_bond_price_invalid_inputs():
    with pytest.raises(BondError):
        bond_price(face=-100, coupon_rate=0.05, yield_rate=0.05, years_to_maturity=5, frequency=2)
    with pytest.raises(BondError):
        bond_price(face=100, coupon_rate=0.05, yield_rate=0.05, years_to_maturity=-1, frequency=2)


def test_bond_price_near_maturity_still_has_one_period():
    # Regression: a semi-annual bond with 0.2yr left rounds to round(0.2*2)=0 periods under
    # naive round()-only logic, which would wrongly report a live bond as "already matured".
    # A bond that hasn't matured always has at least its final coupon+principal payment due.
    price = bond_price(face=100, coupon_rate=0.07, yield_rate=0.07, years_to_maturity=0.2, frequency=2)
    assert price == pytest.approx(100.0, abs=1e-6)  # par bond: coupon == yield


def test_bond_price_at_exact_maturity_raises():
    with pytest.raises(BondError):
        bond_price(face=100, coupon_rate=0.05, yield_rate=0.05, years_to_maturity=0, frequency=2)


def test_accrued_and_clean_dirty_relationship():
    dirty = bond_price(face=100, coupon_rate=0.07, yield_rate=0.07, years_to_maturity=10, frequency=2, settle_frac=0.5)
    accrued = accrued_interest(face=100, coupon_rate=0.07, frequency=2, settle_frac=0.5)
    clean = clean_price(face=100, coupon_rate=0.07, yield_rate=0.07, years_to_maturity=10, frequency=2, settle_frac=0.5)
    assert clean == pytest.approx(dirty - accrued)
    assert accrued == pytest.approx(100 * 0.07 / 2 * 0.5)


def test_ytm_recovers_known_yield():
    true_yield = 0.065
    price = bond_price(face=100, coupon_rate=0.07, yield_rate=true_yield, years_to_maturity=7, frequency=2)
    solved = ytm(price=price, face=100, coupon_rate=0.07, years_to_maturity=7, frequency=2)
    assert solved == pytest.approx(true_yield, abs=1e-8)


def test_ytm_par_bond():
    solved = ytm(price=100.0, face=100, coupon_rate=0.06, years_to_maturity=5, frequency=2)
    assert solved == pytest.approx(0.06, abs=1e-6)


def test_ytm_invalid_price_raises():
    with pytest.raises(BondError):
        ytm(price=-5, face=100, coupon_rate=0.06, years_to_maturity=5, frequency=2)


def test_macaulay_duration_zero_coupon_equals_maturity():
    # A "zero coupon" approximated with tiny coupon should have duration ~ maturity
    dur = macaulay_duration(face=100, coupon_rate=0.0001, yield_rate=0.05, years_to_maturity=10, frequency=2)
    assert dur == pytest.approx(10.0, abs=0.05)


def test_modified_duration_less_than_macaulay_for_positive_yield():
    result = duration_convexity_dv01(face=100, coupon_rate=0.07, yield_rate=0.07, years_to_maturity=10, frequency=2)
    assert result.modified_duration < result.macaulay_years
    assert result.modified_duration == pytest.approx(result.macaulay_years / (1 + 0.07 / 2), rel=1e-4)


def test_convexity_is_positive_for_plain_vanilla_bond():
    result = duration_convexity_dv01(face=100, coupon_rate=0.07, yield_rate=0.07, years_to_maturity=10, frequency=2)
    assert result.convexity > 0


def test_dv01_matches_manual_bump_reprice():
    face, coupon, y, mat, freq = 100, 0.07, 0.07, 10, 2
    result = duration_convexity_dv01(face, coupon, y, mat, freq)
    p_dn = bond_price(face, coupon, y - 1e-4, mat, freq)
    p_up = bond_price(face, coupon, y + 1e-4, mat, freq)
    manual_dv01 = (p_dn - p_up) / 2
    assert result.dv01 == pytest.approx(manual_dv01, rel=1e-6)


def test_duration_approx_close_to_exact_for_small_shock():
    face, coupon, y, mat, freq = 100, 0.07, 0.07, 10, 2
    result = duration_convexity_dv01(face, coupon, y, mat, freq)
    dy = 0.0025  # 25bp
    approx = duration_based_price_change(result.modified_duration, result.convexity, result.price, dy)
    exact = exact_reprice_change(face, coupon, y, mat, freq, dy)
    # Duration+convexity approximation should be close but not identical to exact reprice
    assert approx == pytest.approx(exact, abs=0.05)


def test_duration_approx_diverges_from_exact_for_large_shock():
    face, coupon, y, mat, freq = 100, 0.07, 0.07, 10, 2
    result = duration_convexity_dv01(face, coupon, y, mat, freq)
    dy = 0.05  # 500bp -- large shock where 2nd-order approx breaks down more visibly
    approx = duration_based_price_change(result.modified_duration, result.convexity, result.price, dy)
    exact = exact_reprice_change(face, coupon, y, mat, freq, dy)
    assert approx != pytest.approx(exact, rel=1e-3)
