from __future__ import annotations

from pydantic import BaseModel, Field


class PositionCreate(BaseModel):
    instrument_type: str = Field(pattern="^(FX|BOND)$")
    instrument_id: str
    side: str = Field(pattern="^(BUY|SELL)$")
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class PositionOut(BaseModel):
    id: int
    instrument_type: str
    instrument_id: str
    quantity: float
    entry_price: float
    status: str

    class Config:
        from_attributes = True


class TradeOut(BaseModel):
    id: int
    instrument_type: str
    instrument_id: str
    side: str
    quantity: float
    price: float
    notional: float
    trade_type: str
    status: str
    created_at: str

    class Config:
        from_attributes = True
