"""
Aggregates open positions against market data into exposures, MTM P&L, and a
historical portfolio-value series used for VaR / Expected Shortfall.

No look-ahead bias: the historical portfolio series is reconstructed strictly from
past (already-observed) market data up to the current "as of" date -- each day's
value uses only that day's market levels and the CURRENT static position quantities,
never future information.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.finance.bonds import bond_price, duration_convexity_dv01
from app.finance.fx import fx_pnl, simple_returns
from app.models.bond import Bond
from app.models.position import Position
from app.services.market_view import effective_bonds, effective_fx_quotes


@dataclass
class FxPositionView:
    pair: str
    notional_base: float
    entry_rate: float
    current_rate: float
    pnl: float
    return_pct: float


@dataclass
class BondPositionView:
    isin: str
    name: str
    quantity: float
    face: float
    coupon_rate: float
    current_yield: float
    price: float
    modified_duration: float
    convexity: float
    dv01: float
    macaulay_years: float
    market_value: float


def get_fx_positions(db: Session, provider: MarketDataProvider) -> list[FxPositionView]:
    latest = {q.pair: q.rate for q in effective_fx_quotes(db, provider)}
    views = []
    for pos in db.query(Position).filter(Position.instrument_type == "FX", Position.status == "OPEN").all():
        current_rate = latest.get(pos.instrument_id)
        if current_rate is None:
            continue
        r = fx_pnl(entry_rate=pos.entry_price, current_rate=current_rate, notional_base=pos.quantity)
        views.append(FxPositionView(
            pair=pos.instrument_id, notional_base=pos.quantity, entry_rate=pos.entry_price,
            current_rate=current_rate, pnl=r.pnl_quote_ccy, return_pct=r.return_pct,
        ))
    return views


def get_bond_positions(db: Session, provider: MarketDataProvider) -> list[BondPositionView]:
    bonds_by_isin = {b.isin: b for b in effective_bonds(db, provider)}
    views = []
    for pos in db.query(Position).filter(Position.instrument_type == "BOND", Position.status == "OPEN").all():
        b = bonds_by_isin.get(pos.instrument_id)
        if b is None:
            continue
        from datetime import date
        maturity = date.fromisoformat(b.maturity_date)
        years_to_maturity = max(0.01, (maturity - date.today()).days / 365.25)
        y = b.current_yield / 100.0
        result = duration_convexity_dv01(b.face, b.coupon_rate, y, years_to_maturity, b.frequency)
        units = pos.quantity / b.face
        views.append(BondPositionView(
            isin=b.isin, name=b.name, quantity=pos.quantity, face=b.face, coupon_rate=b.coupon_rate,
            current_yield=b.current_yield, price=result.price, modified_duration=result.modified_duration,
            convexity=result.convexity, dv01=result.dv01 * units, macaulay_years=result.macaulay_years,
            market_value=result.price * units,
        ))
    return views


def reconstruct_portfolio_value_history(db: Session, provider: MarketDataProvider, lookback_days: int = 250) -> np.ndarray:
    """Rebuild daily portfolio value over the lookback window, holding today's
    position quantities constant, using each day's actual historical FX rate /
    bond yield (never a future value)."""
    fx_positions = db.query(Position).filter(Position.instrument_type == "FX", Position.status == "OPEN").all()
    bond_positions = db.query(Position).filter(Position.instrument_type == "BOND", Position.status == "OPEN").all()
    bonds_by_isin = {b.isin: b for b in provider.get_bonds()}

    fx_hist: dict[str, dict[str, float]] = {}
    dates: set[str] = set()
    for pos in fx_positions:
        hist = provider.get_fx_history(pos.instrument_id, lookback_days)
        fx_hist[pos.instrument_id] = {q.date: q.rate for q in hist}
        dates.update(fx_hist[pos.instrument_id].keys())

    bond_hist: dict[str, dict[str, float]] = {}
    for pos in bond_positions:
        rows = provider.get_bond_yield_history(pos.instrument_id, lookback_days)
        bond_hist[pos.instrument_id] = {d: y for d, y in rows}
        dates.update(bond_hist[pos.instrument_id].keys())

    if not dates:
        return np.array([])

    sorted_dates = sorted(dates)
    values = []
    for d in sorted_dates:
        total = 0.0
        for pos in fx_positions:
            rate = fx_hist.get(pos.instrument_id, {}).get(d)
            if rate is not None:
                total += rate * pos.quantity
        for pos in bond_positions:
            y = bond_hist.get(pos.instrument_id, {}).get(d)
            b = bonds_by_isin.get(pos.instrument_id)
            if y is not None and b is not None:
                from datetime import date as date_cls
                maturity = date_cls.fromisoformat(b.maturity_date)
                today_val = date_cls.fromisoformat(d)
                ytm_yrs = max(0.05, (maturity - today_val).days / 365.25)
                price = bond_price(b.face, b.coupon_rate, y, ytm_yrs, b.frequency)
                total += price * (pos.quantity / b.face)
        values.append(total)
    return np.array(values)


def portfolio_daily_returns(db: Session, provider: MarketDataProvider, lookback_days: int = 250) -> np.ndarray:
    values = reconstruct_portfolio_value_history(db, provider, lookback_days)
    return simple_returns(values)
