from __future__ import annotations

from pydantic import BaseModel


class ExtractedField(BaseModel):
    instrument: str | None = None
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    confidence: float
    source_region: list[int] | None = None  # [x, y, w, h]


class CvExtractionResponse(BaseModel):
    id: int
    original_filename: str
    chart_type: str
    stages: dict  # base64 previews per pipeline stage
    ocr_text_raw: str
    fields: list[ExtractedField]
    mean_confidence: float
    warnings: list[str]


class CvCorrectionRequest(BaseModel):
    extraction_id: int
    corrected_fields: list[ExtractedField]


class CvCommitRequest(BaseModel):
    extraction_id: int
    target: str  # "fx" | "bond_yield" | "yield_curve"
    instrument_id: str
