from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.cv_engine.pipeline import run_pipeline
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.bonds import duration_convexity_dv01
from app.models.audit_log import AuditLog
from app.models.cv_extraction import CvExtraction
from app.schemas.cv import CvCommitRequest, CvCorrectionRequest

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

    return {
        "id": record.id,
        "original_filename": record.original_filename,
        "chart_type": record.chart_type,
        "stages": result["stages"],
        "ocr_text_raw": result["ocr_text_raw"],
        "ocr_available": result["ocr_available"],
        "fields": result["fields"],
        "mean_confidence": result["mean_confidence"],
        "warnings": result["warnings"],
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
    """Feed a (possibly human-corrected) extracted value into the Treasury analytics
    engine and return the resulting analytics -- this closes the CV -> Finance loop."""
    record = db.get(CvExtraction, req.extraction_id)
    if record is None:
        raise HTTPException(404, "Extraction not found")

    fields = (record.corrected_json or record.extracted_json).get("fields", [])
    match = next((f for f in fields if req.instrument_id.upper() in (f.get("instrument") or "").upper()), None)
    if match is None or match.get("value") is None:
        raise HTTPException(400, "No matching extracted field found for the given instrument_id")
    value = float(match["value"])

    if req.target == "fx":
        current = next((q.rate for q in provider.get_all_fx_latest() if q.pair == req.instrument_id), None)
        analytics = {
            "instrument_id": req.instrument_id, "extracted_spot": value, "current_demo_spot": current,
            "diff_vs_demo": None if current is None else round(value - current, 4),
        }
    elif req.target == "bond_yield":
        bond = next((b for b in provider.get_bonds() if b.isin == req.instrument_id), None)
        if bond is None:
            raise HTTPException(400, f"Unknown bond {req.instrument_id}")
        years = max(0.05, (date.fromisoformat(bond.maturity_date) - date.today()).days / 365.25)
        y = value / 100.0
        dur = duration_convexity_dv01(bond.face, bond.coupon_rate, y, years, bond.frequency)
        analytics = {
            "instrument_id": req.instrument_id, "extracted_yield_pct": value,
            "clean_price": round(dur.price, 4), "modified_duration": round(dur.modified_duration, 4),
            "convexity": round(dur.convexity, 4), "dv01_per_100_face": round(dur.dv01, 6),
        }
    else:
        raise HTTPException(400, f"Unsupported commit target {req.target}")

    record.committed_to_engine = True
    db.add(AuditLog(action="CV_COMMIT", entity_type="cv_extraction", entity_id=str(record.id), detail_json=analytics))
    db.commit()
    return analytics
