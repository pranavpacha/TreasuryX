from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class MarketEvent(Base, TimestampMixin):
    """Market-intelligence event feed shown on the Overview page (demo-seeded)."""
    __tablename__ = "market_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="MARKET")
    severity: Mapped[str] = mapped_column(String, nullable=False, default="INFO")
