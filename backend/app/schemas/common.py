from __future__ import annotations

from pydantic import BaseModel


class MetricValue(BaseModel):
    """Every displayed metric carries a label, unit, value, and provenance --
    see UX rule in section 24 of the project spec: never show a bare number."""
    label: str
    value: float
    unit: str
    as_of: str
    source: str = "DEMO"
    method: str | None = None
    is_demo: bool = True
