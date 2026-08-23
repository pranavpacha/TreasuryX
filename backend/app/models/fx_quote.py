from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FxQuoteCache(Base):
    """Optional local cache of FX quotes (for a future live-provider integration).
    In demo mode, quotes are served directly from the DemoDataProvider CSVs and this
    table is not required, but is present so a live provider can persist snapshots."""
    __tablename__ = "fx_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String, nullable=False, index=True)
    date: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    bid: Mapped[float] = mapped_column(Float, nullable=False)
    ask: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="DEMO")
