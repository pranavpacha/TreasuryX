import numpy as np
import pytest

from app.finance.fx import fx_pnl, historical_volatility, log_returns, simple_returns


def test_fx_pnl_long_profit():
    r = fx_pnl(entry_rate=83.0, current_rate=84.0, notional_base=1_000_000)
    assert r.pnl_quote_ccy == pytest.approx(1_000_000.0)
    assert r.return_pct == pytest.approx(1.0 / 83.0)


def test_fx_pnl_long_loss():
    r = fx_pnl(entry_rate=83.0, current_rate=82.0, notional_base=1_000_000)
    assert r.pnl_quote_ccy == pytest.approx(-1_000_000.0)


def test_fx_pnl_short_profit_when_rate_falls():
    r = fx_pnl(entry_rate=83.0, current_rate=82.0, notional_base=-1_000_000)
    assert r.pnl_quote_ccy == pytest.approx(1_000_000.0)


def test_fx_pnl_short_loss_when_rate_rises():
    r = fx_pnl(entry_rate=83.0, current_rate=84.0, notional_base=-1_000_000)
    assert r.pnl_quote_ccy == pytest.approx(-1_000_000.0)


def test_fx_pnl_invalid_rate_raises():
    with pytest.raises(ValueError):
        fx_pnl(entry_rate=0, current_rate=84.0, notional_base=1000)


def test_log_returns_known_values():
    prices = np.array([100.0, 110.0, 121.0])
    rets = log_returns(prices)
    assert rets == pytest.approx(np.log([1.1, 1.1]))


def test_simple_returns_known_values():
    prices = np.array([100.0, 110.0, 99.0])
    rets = simple_returns(prices)
    assert rets == pytest.approx([0.10, -0.10])


def test_historical_volatility_zero_variance():
    prices = np.array([100.0] * 30)
    assert historical_volatility(prices) == pytest.approx(0.0)


def test_historical_volatility_positive_for_noisy_series():
    rng = np.random.default_rng(42)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    vol = historical_volatility(prices, annualize=True)
    assert vol > 0
    daily_vol = historical_volatility(prices, annualize=False)
    assert vol == pytest.approx(daily_vol * np.sqrt(252))


def test_historical_volatility_insufficient_data():
    assert historical_volatility(np.array([100.0])) == 0.0
