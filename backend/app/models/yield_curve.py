from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class YieldCurvePointCache(Base):
    """Optional local cache mirroring the demo/live yield-curve series (see FxQuoteCache)."""
    __tablename__ = "yield_curve_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tenor: Mapped[str] = mapped_column(String, nullable=False)
    years: Mapped[float] = mapped_column(Float, nullable=False)
    yield_pct: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="DEMO")
