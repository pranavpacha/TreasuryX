from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.cv_engine.models.infer import classify_image_bytes
from app.cv_engine.pipeline import run_pipeline
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.bonds import duration_convexity_dv01
from app.models.audit_log import AuditLog
from app.models.cv_extraction import CvExtraction
from app.models.market_override import MarketOverride
from app.risk.aggregator import get_bond_positions, get_fx_positions
from app.schemas.cv import CvCommitRequest, CvCorrectionRequest
from app.services.market_view import effective_fx_rate
from app.services.overrides import list_active_overrides, set_override

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

    if req.target == "fx":
        previous = effective_fx_rate(db, provider, req.instrument_id)
        if previous is None:
            raise HTTPException(400, f"Unknown FX pair {req.instrument_id}")
        set_override(db, "FX", req.instrument_id, "rate", value, source="cv_extraction", cv_extraction_id=record.id)

        affected_positions = [
            {"pair": p.pair, "notional_base": p.notional_base, "pnl_inr": round(p.pnl, 2)}
            for p in get_fx_positions(db, provider) if p.pair == req.instrument_id
        ]
        analytics = {
            "instrument_id": req.instrument_id, "field": "spot rate",
            "previous_value": previous, "new_value": value, "delta": round(value - previous, 4),
            "affected_open_positions": affected_positions,
        }

    elif req.target == "bond_yield":
        bond = next((b for b in provider.get_bonds() if b.isin == req.instrument_id), None)
        if bond is None:
            raise HTTPException(400, f"Unknown bond {req.instrument_id}")
        years = max(0.05, (date.fromisoformat(bond.maturity_date) - date.today()).days / 365.25)

        dur_before = duration_convexity_dv01(bond.face, bond.coupon_rate, bond.current_yield / 100.0, years, bond.frequency)
        dur_after = duration_convexity_dv01(bond.face, bond.coupon_rate, value / 100.0, years, bond.frequency)

        set_override(db, "BOND", req.instrument_id, "yield_pct", value, source="cv_extraction", cv_extraction_id=record.id)

        affected_positions = [
            {
                "isin": p.isin, "quantity_face": p.quantity,
                "market_value_before_inr": None, "market_value_after_inr": round(p.market_value, 2),
                "dv01_after_inr": round(p.dv01, 2),
            }
            for p in get_bond_positions(db, provider) if p.isin == req.instrument_id
        ]
        analytics = {
            "instrument_id": req.instrument_id, "field": "yield",
            "previous_value": bond.current_yield, "new_value": value, "delta_bps": round((value - bond.current_yield) * 100, 1),
            "clean_price_before": round(dur_before.price, 4), "clean_price_after": round(dur_after.price, 4),
            "modified_duration_after": round(dur_after.modified_duration, 4),
            "convexity_after": round(dur_after.convexity, 4),
            "dv01_per_100_face_after": round(dur_after.dv01, 6),
            "affected_open_positions": affected_positions,
        }
    else:
        raise HTTPException(400, f"Unsupported commit target {req.target}")

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
