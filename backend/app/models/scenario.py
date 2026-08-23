from __future__ import annotations

from sqlalchemy import JSON, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin


class ScenarioRun(Base, TimestampMixin):
    """Auditable record of every scenario/stress run: inputs, method, outputs."""
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    inputs_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    outputs_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Float, nullable=False)
