from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class MarketOverride(Base, TimestampMixin):
    """A manual market-data correction applied on top of the demo provider's baseline value --
    this is how a Computer-Vision-extracted value actually changes what the rest of the
    application sees, instead of being displayed once and forgotten. One row per
    (instrument_type, instrument_id, field); a new commit replaces the previous override for
    that key (latest-wins), and the full history is kept via created_at + the linked
    cv_extraction_id for audit."""
    __tablename__ = "market_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)  # "BOND" | "FX"
    instrument_id: Mapped[str] = mapped_column(String, nullable=False)  # ISIN or pair
    field: Mapped[str] = mapped_column(String, nullable=False)  # "yield_pct" | "rate"
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="cv_extraction")
    cv_extraction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
