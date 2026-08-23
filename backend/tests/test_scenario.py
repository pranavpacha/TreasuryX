import pytest

from app.finance.scenario_engine import BondPositionInput, FxPositionInput, ShockInput, run_scenario


def test_fx_scenario_long_position_gains_on_positive_shock():
    fx_pos = [FxPositionInput(pair="USDINR", notional_base=5_000_000, entry_rate=83.0, current_rate=83.5)]
    shock = ShockInput(fx_shock_pct={"USDINR": 0.02})
    result = run_scenario(fx_pos, [], shock)
    expected = 83.5 * 0.02 * 5_000_000
    assert result.fx_pnl_by_pair["USDINR"] == pytest.approx(expected, rel=1e-9)
    assert result.total_fx_pnl == pytest.approx(expected, rel=1e-9)


def test_fx_scenario_short_position_loses_on_positive_shock():
    fx_pos = [FxPositionInput(pair="USDINR", notional_base=-5_000_000, entry_rate=83.0, current_rate=83.5)]
    shock = ShockInput(fx_shock_pct={"USDINR": 0.02})
    result = run_scenario(fx_pos, [], shock)
    assert result.fx_pnl_by_pair["USDINR"] < 0


def test_bond_scenario_yield_up_loses_value_for_long_position():
    bond_pos = [
        BondPositionInput(
            isin="IN0001", face=100, coupon_rate=0.07, current_yield=0.07,
            years_to_maturity=10, frequency=2, quantity=100_000,
        )
    ]
    shock = ShockInput(parallel_yield_shock_bps=25)
    result = run_scenario([], bond_pos, shock)
    assert result.bond_pnl_exact_by_isin["IN0001"] < 0
    assert result.total_bond_pnl < 0


def test_bond_scenario_yield_down_gains_value_for_long_position():
    bond_pos = [
        BondPositionInput(
            isin="IN0001", face=100, coupon_rate=0.07, current_yield=0.07,
            years_to_maturity=10, frequency=2, quantity=100_000,
        )
    ]
    shock = ShockInput(parallel_yield_shock_bps=-25)
    result = run_scenario([], bond_pos, shock)
    assert result.bond_pnl_exact_by_isin["IN0001"] > 0


def test_combined_scenario_totals_add_up():
    fx_pos = [FxPositionInput(pair="USDINR", notional_base=1_000_000, entry_rate=83.0, current_rate=83.0)]
    bond_pos = [
        BondPositionInput(
            isin="IN0001", face=100, coupon_rate=0.07, current_yield=0.07,
            years_to_maturity=10, frequency=2, quantity=50_000,
        )
    ]
    shock = ShockInput(fx_shock_pct={"USDINR": 0.01}, parallel_yield_shock_bps=10)
    result = run_scenario(fx_pos, bond_pos, shock)
    assert result.total_pnl == pytest.approx(result.total_fx_pnl + result.total_bond_pnl, rel=1e-9)


def test_curve_tilt_affects_long_and_short_maturities_differently():
    bond_pos = [
        BondPositionInput(isin="SHORT2Y", face=100, coupon_rate=0.07, current_yield=0.07,
                           years_to_maturity=2, frequency=2, quantity=100_000),
        BondPositionInput(isin="LONG10Y", face=100, coupon_rate=0.07, current_yield=0.07,
                           years_to_maturity=10, frequency=2, quantity=100_000),
    ]
    shock = ShockInput(curve_tilt_bps=30)  # steepening: long end yields rise more
    result = run_scenario([], bond_pos, shock)
    assert result.shocked_bond_yields["LONG10Y"] > result.shocked_bond_yields["SHORT2Y"]
