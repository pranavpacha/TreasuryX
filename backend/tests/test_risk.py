import numpy as np
import pytest

from app.finance.risk_metrics import RiskError, historical_var_es, max_drawdown


def test_var_es_known_distribution():
    # 100 observations, uniform -1% to +1% in 0.02% steps roughly
    returns = np.linspace(-0.05, 0.04, 100)
    result = historical_var_es(returns, portfolio_value=1_000_000, confidence=0.95)
    assert result.var_amount > 0
    assert result.expected_shortfall >= result.var_amount  # ES should be >= VaR (worse tail avg)


def test_var_scales_with_portfolio_value():
    returns = np.random.default_rng(1).normal(0, 0.01, 500)
    r1 = historical_var_es(returns, portfolio_value=1_000_000, confidence=0.95)
    r2 = historical_var_es(returns, portfolio_value=2_000_000, confidence=0.95)
    assert r2.var_amount == pytest.approx(r1.var_amount * 2, rel=1e-9)


def test_var_higher_confidence_gives_higher_var():
    returns = np.random.default_rng(2).normal(0, 0.01, 500)
    r95 = historical_var_es(returns, portfolio_value=1_000_000, confidence=0.95)
    r99 = historical_var_es(returns, portfolio_value=1_000_000, confidence=0.99)
    assert r99.var_amount >= r95.var_amount


def test_var_insufficient_data_raises():
    with pytest.raises(RiskError):
        historical_var_es(np.array([0.01, -0.01]), portfolio_value=1_000_000)


def test_var_invalid_confidence_raises():
    with pytest.raises(RiskError):
        historical_var_es(np.random.default_rng(3).normal(0, 0.01, 50), portfolio_value=1_000_000, confidence=1.5)


def test_max_drawdown_simple_case():
    pnl = np.array([0, 10, 20, 5, -5, 15])
    # peak=20 at idx2, trough=-5 at idx4 -> drawdown = -5 - 20 = -25
    assert max_drawdown(pnl) == pytest.approx(-25.0)


def test_max_drawdown_monotonic_increase_is_zero():
    pnl = np.array([0, 5, 10, 15])
    assert max_drawdown(pnl) == pytest.approx(0.0)
