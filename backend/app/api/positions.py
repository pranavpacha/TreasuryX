from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.models.position import Position
from app.models.trade import Trade
from app.risk.aggregator import get_bond_positions
from app.schemas.positions import PositionCreate, TradeOut

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("/bonds")
def list_bond_positions(db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    views = get_bond_positions(db, provider)
    return [
        {
            "isin": v.isin, "name": v.name, "quantity_face": v.quantity, "clean_price": round(v.price, 4),
            "current_yield_pct": v.current_yield, "modified_duration": round(v.modified_duration, 4),
            "convexity": round(v.convexity, 4), "dv01_inr": round(v.dv01, 2),
            "market_value_inr": round(v.market_value, 2),
        }
        for v in views
    ]


@router.post("/bonds/trade", response_model=TradeOut, status_code=201)
def trade_bond(trade_in: PositionCreate, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    if trade_in.instrument_type != "BOND":
        raise HTTPException(400, "Use /api/positions/bonds/trade only for BOND instruments")
    valid_isins = {b.isin for b in provider.get_bonds()}
    if trade_in.instrument_id not in valid_isins:
        raise HTTPException(400, f"Unknown ISIN {trade_in.instrument_id}")

    signed_qty = trade_in.quantity if trade_in.side == "BUY" else -trade_in.quantity
    position = Position(
        instrument_type="BOND", instrument_id=trade_in.instrument_id,
        quantity=signed_qty, entry_price=trade_in.price, status="OPEN",
    )
    db.add(position)
    db.flush()

    trade = Trade(
        instrument_type="BOND", instrument_id=trade_in.instrument_id, side=trade_in.side,
        quantity=trade_in.quantity, price=trade_in.price, notional=trade_in.quantity * trade_in.price / 100,
        trade_type="OUTRIGHT", status="SIMULATED", position_id=position.id,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return TradeOut(
        id=trade.id, instrument_type=trade.instrument_type, instrument_id=trade.instrument_id,
        side=trade.side, quantity=trade.quantity, price=trade.price, notional=trade.notional,
        trade_type=trade.trade_type, status=trade.status, created_at=trade.created_at.isoformat(),
    )


@router.get("/blotter", response_model=list[TradeOut])
def trade_blotter(limit: int = 100, db: Session = Depends(get_db)):
    trades = db.query(Trade).order_by(desc(Trade.created_at)).limit(limit).all()
    return [
        TradeOut(
            id=t.id, instrument_type=t.instrument_type, instrument_id=t.instrument_id,
            side=t.side, quantity=t.quantity, price=t.price, notional=t.notional,
            trade_type=t.trade_type, status=t.status, created_at=t.created_at.isoformat(),
        )
        for t in trades
    ]
