from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.fx import historical_volatility, log_returns
from app.models.position import Position
from app.models.trade import Trade
from app.risk.aggregator import get_fx_positions
from app.schemas.positions import PositionCreate, TradeOut

router = APIRouter(prefix="/api/fx", tags=["fx"])

SUPPORTED_PAIRS = ["USDINR", "EURINR", "GBPINR", "EURUSD"]


@router.get("/quotes")
def get_quotes(provider: MarketDataProvider = Depends(get_provider)):
    quotes = provider.get_all_fx_latest()
    out = []
    for q in quotes:
        hist = [x.rate for x in provider.get_fx_history(q.pair, 30)]
        ret = log_returns(np.array(hist))
        day_ret = float(ret[-1]) if len(ret) else 0.0
        vol = historical_volatility(np.array([x.rate for x in provider.get_fx_history(q.pair, 60)]))
        out.append({
            "pair": q.pair, "rate": q.rate, "bid": q.bid, "ask": q.ask, "spread": round(q.ask - q.bid, 4),
            "day_return_pct": day_ret, "annualized_vol_pct": vol, "date": q.date,
            "source": q.source, "is_demo": q.is_demo,
        })
    return out


@router.get("/history/{pair}")
def get_history(pair: str, lookback_days: int = 250, provider: MarketDataProvider = Depends(get_provider)):
    if pair not in SUPPORTED_PAIRS:
        raise HTTPException(404, f"Unsupported pair {pair}")
    hist = provider.get_fx_history(pair, lookback_days)
    if not hist:
        raise HTTPException(404, f"No history for {pair}")
    return [{"date": h.date, "rate": h.rate, "bid": h.bid, "ask": h.ask} for h in hist]


@router.get("/positions")
def list_positions(db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    views = get_fx_positions(db, provider)
    return [
        {
            "pair": v.pair, "notional_base": v.notional_base, "entry_rate": v.entry_rate,
            "current_rate": v.current_rate, "pnl_inr": v.pnl, "return_pct": v.return_pct,
        }
        for v in views
    ]


@router.post("/trade", response_model=TradeOut, status_code=201)
def simulate_trade(trade_in: PositionCreate, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    """Booking a SIMULATED FX trade -- no real execution venue is contacted."""
    if trade_in.instrument_type != "FX":
        raise HTTPException(400, "Use /api/fx/trade only for FX instruments")
    if trade_in.instrument_id not in SUPPORTED_PAIRS:
        raise HTTPException(400, f"Unsupported pair {trade_in.instrument_id}")

    signed_qty = trade_in.quantity if trade_in.side == "BUY" else -trade_in.quantity
    position = Position(
        instrument_type="FX", instrument_id=trade_in.instrument_id,
        quantity=signed_qty, entry_price=trade_in.price, status="OPEN",
    )
    db.add(position)
    db.flush()

    trade = Trade(
        instrument_type="FX", instrument_id=trade_in.instrument_id, side=trade_in.side,
        quantity=trade_in.quantity, price=trade_in.price, notional=trade_in.quantity * trade_in.price,
        trade_type="SPOT", status="SIMULATED", position_id=position.id,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return TradeOut(
        id=trade.id, instrument_type=trade.instrument_type, instrument_id=trade.instrument_id,
        side=trade.side, quantity=trade.quantity, price=trade.price, notional=trade.notional,
        trade_type=trade.trade_type, status=trade.status, created_at=trade.created_at.isoformat(),
    )
