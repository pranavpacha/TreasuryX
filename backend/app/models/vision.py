from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class VisionProposal(Base, TimestampMixin):
    """A market value read by a CV feature, WAITING for an analyst. It changes nothing until approved:
    approval writes a MarketOverride through services/commit.py (the same path as the existing
    Financial Image Intelligence commit), rejection just closes the proposal."""
    __tablename__ = "vision_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, nullable=False)            # chart_digitization | screenshot_comparison | video | ocr | document
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)  # filename / job id
    target: Mapped[str] = mapped_column(String, nullable=False)            # bond_yield | fx
    instrument_id: Mapped[str] = mapped_column(String, nullable=False)     # ISIN, tenor ("10Y") or FX pair
    proposed_value: Mapped[float] = mapped_column(Float, nullable=False)
    previous_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending | approved | rejected
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String, nullable=True)
    applied_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_isin: Mapped[str | None] = mapped_column(String, nullable=True)


class VisionEvent(Base, TimestampMixin):
    """Intelligence event raised by a CV feature (video change, visual anomaly, comparison result) for analyst review.
    Events are observations about SCREENS; they never modify market data."""
    __tablename__ = "vision_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="info")
    title: Mapped[str] = mapped_column(String, nullable=False)
    detail_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")  # open | acknowledged | dismissed
