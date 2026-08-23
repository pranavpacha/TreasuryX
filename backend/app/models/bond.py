from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class Bond(Base, TimestampMixin):
    """Government bond static reference data (seeded from the demo provider)."""
    __tablename__ = "bonds"

    isin: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    face: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    coupon_rate: Mapped[float] = mapped_column(Float, nullable=False)
    maturity_date: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    issue_date: Mapped[str] = mapped_column(String, nullable=False)
