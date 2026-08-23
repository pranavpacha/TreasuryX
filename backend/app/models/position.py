from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class Position(Base, TimestampMixin):
    """A simulated Treasury position (FX or bond). No real-money trading."""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)  # "FX" | "BOND"
    instrument_id: Mapped[str] = mapped_column(String, nullable=False)  # pair or ISIN
    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # signed: + long, - short
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)  # rate or yield at entry
    status: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")
