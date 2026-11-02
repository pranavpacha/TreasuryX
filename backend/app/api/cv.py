from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.cv_engine.models.infer import classify_image_bytes
from app.cv_engine.pipeline import run_pipeline
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.models.audit_log import AuditLog
from app.models.cv_extraction import CvExtraction
from app.models.market_override import MarketOverride
from app.schemas.cv import CvCommitRequest, CvCorrectionRequest
from app.services.commit import MarketValueError, apply_market_value
from app.services.overrides import list_active_overrides
from app.services.vision_index import add_to_index

router = APIRouter(prefix="/api/cv", tags=["cv"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]")


def _sanitize_filename(name: str) -> str:
    return SAFE_NAME_RE.sub("_", Path(name).name)[:120]


@router.post("/extract")
async def extract(file: UploadFile, db: Session = Depends(get_db)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {settings.allowed_upload_extensions}")

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(400, f"File too large ({len(content)} bytes). Max {settings.max_upload_size_bytes} bytes.")
    if len(content) == 0:
        raise HTTPException(400, "Uploaded file is empty")

    try:
        result = run_pipeline(content, file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    safe_name = _sanitize_filename(file.filename or "upload")
    stored_name = f"{date.today().isoformat()}_{safe_name}"
    (UPLOAD_DIR / stored_name).write_bytes(content)

    record = CvExtraction(
        original_filename=file.filename or "upload",
        stored_filename=stored_name,
        chart_type=result["chart_type"],
        extracted_json={"fields": result["fields"], "ocr_text_raw": result["ocr_text_raw"], "warnings": result["warnings"]},
        mean_confidence=result["mean_confidence"],
        committed_to_engine=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Best-effort: remember this screenshot's layout embedding so Similarity Search (feature 10)
    # can later find look-alike reports. Indexing must never break extraction.
    try:
        img = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            add_to_index(db, img, file.filename or "upload", origin="financial_image_intelligence")
    except Exception:  # noqa: BLE001
        pass

    return {
        "id": record.id,
        "original_filename": record.original_filename,
        "chart_type": record.chart_type,
        "asset_class": result["asset_class"],
        "image_quality": result["image_quality"],
        "stages": result["stages"],
        "ocr_text_raw": result["ocr_text_raw"],
        "ocr_available": result["ocr_available"],
        "fields": result["fields"],
        "mean_confidence": result["mean_confidence"],
        "warnings": result["warnings"],
        "model_details": classify_image_bytes(content),
    }


@router.post("/correct")
def correct(req: CvCorrectionRequest, db: Session = Depends(get_db)):
    record = db.get(CvExtraction, req.extraction_id)
    if record is None:
        raise HTTPException(404, "Extraction not found")
    record.corrected_json = {"fields": [f.model_dump() for f in req.corrected_fields]}
    db.add(AuditLog(action="CV_CORRECT", entity_type="cv_extraction", entity_id=str(record.id),
                     detail_json=record.corrected_json))
    db.commit()
    return {"id": record.id, "status": "corrected"}


@router.post("/commit")
def commit(req: CvCommitRequest, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    """Feed a (possibly human-corrected) extracted value into the Treasury analytics engine.

    This is a REAL state change, not a one-off calculation: it writes a MarketOverride row
    (see app/services/overrides.py) that every other part of the app -- Rates & Bonds, Risk,
    Scenario, and the 3D Portfolio Stress Surface -- reads through
    app/services/market_view.py. A committed correction is visible everywhere immediately,
    exactly like a real market-data correction would be.
    """
    record = db.get(CvExtraction, req.extraction_id)
    if record is None:
        raise HTTPException(404, "Extraction not found")

    fields = (record.corrected_json or record.extracted_json).get("fields", [])
    match = next((f for f in fields if req.instrument_id.upper() in (f.get("instrument") or "").upper()), None)
    if match is None or match.get("value") is None:
        raise HTTPException(400, "No matching extracted field found for the given instrument_id")
    value = float(match["value"])

    try:
        analytics = apply_market_value(db, provider, req.target, req.instrument_id, value, source="cv_extraction", cv_extraction_id=record.id)
    except MarketValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    record.committed_to_engine = True
    db.add(AuditLog(action="CV_COMMIT", entity_type="cv_extraction", entity_id=str(record.id), detail_json=analytics))
    db.commit()
    return analytics


@router.get("/overrides")
def list_overrides(db: Session = Depends(get_db)):
    """Every active CV-sourced market correction currently applied on top of demo data."""
    return [
        {"instrument_type": o.instrument_type, "instrument_id": o.instrument_id, "field": o.field,
         "value": o.value, "source": o.source, "applied_at": o.created_at.isoformat()}
        for o in list_active_overrides(db)
    ]


@router.delete("/overrides")
def reset_overrides(db: Session = Depends(get_db)):
    """Clears all CV-sourced market corrections, restoring baseline demo data everywhere."""
    n = db.query(MarketOverride).delete()
    db.commit()
    return {"cleared": n}
