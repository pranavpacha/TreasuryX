from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class CvExtraction(Base, TimestampMixin):
    """Record of one Computer Vision extraction job: uploaded image metadata,
    pipeline stage outputs, and final (possibly human-corrected) structured values."""
    __tablename__ = "cv_extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False)
    chart_type: Mapped[str] = mapped_column(String, nullable=False)  # "yield_curve" | "fx_chart" | "report" | "unknown"
    extracted_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    corrected_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mean_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    committed_to_engine: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
