from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class Trade(Base, TimestampMixin):
    """A row in the SIMULATED trade blotter. Never connects to real execution venues."""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)  # "FX" | "BOND"
    instrument_id: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)  # "BUY" | "SELL"
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    notional: Mapped[float] = mapped_column(Float, nullable=False)
    trade_type: Mapped[str] = mapped_column(String, nullable=False, default="SPOT")
    status: Mapped[str] = mapped_column(String, nullable=False, default="SIMULATED")
    position_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
