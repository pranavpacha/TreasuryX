"""
Analyst-review layer for computer-vision output (/api/vision/*):

  proposals : market values read by a CV feature. They are STAGED here and change nothing until an
              analyst approves them; approval goes through services/commit.py -> MarketOverride, the
              same path the Financial Image Intelligence commit uses, so it propagates to bond
              valuation, positions, risk and stress testing. Flagged values need an explicit second
              confirmation. Nothing is ever overwritten silently: every decision is audit-logged.
  events    : intelligence events (video changes, visual anomalies) for review -- observations only.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.vision_common import NpResponse
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.models.audit_log import AuditLog
from app.models.vision import VisionEvent, VisionProposal
from app.services.commit import MarketValueError, apply_market_value, validate_market_value

router = APIRouter(prefix="/api/vision", tags=["vision-review"], default_response_class=NpResponse)

SOURCES = {"chart_digitization", "screenshot_comparison", "video", "ocr", "document"}


# ================================================================ proposals
class ProposalItem(BaseModel):
    target: str = Field(pattern="^(bond_yield|fx)$")
    instrument_id: str = Field(min_length=1, max_length=40)
    value: float
    confidence: float | None = None
    uncertainty: float | None = None
    note: str | None = Field(None, max_length=300)


class ProposalCreate(BaseModel):
    source: str
    source_ref: str | None = Field(None, max_length=200)
    items: list[ProposalItem] = Field(min_length=1, max_length=40)


class ApproveRequest(BaseModel):
    value: float | None = None           # analyst may correct the proposed value before approving
    confirm_flagged: bool = False        # required when validation raised warnings
    note: str | None = Field(None, max_length=300)


class RejectRequest(BaseModel):
    note: str | None = Field(None, max_length=300)


def _proposal_out(p: VisionProposal) -> dict:
    return {"id": p.id, "source": p.source, "source_ref": p.source_ref, "target": p.target, "instrument_id": p.instrument_id, "proposed_value": p.proposed_value,
            "previous_value": p.previous_value, "unit": p.unit, "confidence": p.confidence, "uncertainty": p.uncertainty, "note": p.note, "validation": p.validation_json,
            "status": p.status, "created_at": p.created_at.isoformat(), "decided_at": p.decided_at.isoformat() if p.decided_at else None, "decision_note": p.decision_note,
            "applied_value": p.applied_value, "resolved_isin": p.resolved_isin}


@router.post("/proposals")
def create_proposals(req: ProposalCreate, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    """Stage values for review. Writes ONLY VisionProposal rows -- no MarketOverride, no change to any Treasury number."""
    if req.source not in SOURCES:
        raise HTTPException(400, f"source must be one of {sorted(SOURCES)}")
    created, skipped = [], []
    for it in req.items:
        v = validate_market_value(db, provider, it.target, it.instrument_id, it.value)
        it = it.model_copy(update={"instrument_id": v["instrument_id"]})
        if not v["ok"]:
            skipped.append({"instrument_id": it.instrument_id, "value": it.value, "reason": "; ".join(v["errors"])})
            continue
        dup = db.query(VisionProposal).filter_by(status="pending", target=it.target, instrument_id=it.instrument_id, proposed_value=it.value, source_ref=req.source_ref).first()
        if dup:
            created.append(_proposal_out(dup))
            continue
        row = VisionProposal(source=req.source, source_ref=req.source_ref, target=it.target, instrument_id=it.instrument_id, proposed_value=it.value, previous_value=v["previous_value"],
                             unit=v["unit"], confidence=it.confidence, uncertainty=it.uncertainty, note=it.note, validation_json=v, resolved_isin=v["resolved_isin"])
        db.add(row)
        db.flush()
        db.add(AuditLog(action="VISION_PROPOSE", entity_type="vision_proposal", entity_id=str(row.id), detail_json={"source": req.source, "instrument": it.instrument_id, "value": it.value}))
        created.append(row)
    db.commit()
    return {"created": [c if isinstance(c, dict) else _proposal_out(c) for c in created], "skipped": skipped,
            "message": "Proposals are staged for review. No market value has been changed."}


@router.get("/proposals")
def list_proposals(status: str | None = Query(None, pattern="^(pending|approved|rejected)$"), db: Session = Depends(get_db)):
    q = db.query(VisionProposal)
    if status:
        q = q.filter_by(status=status)
    return [_proposal_out(p) for p in q.order_by(VisionProposal.id.desc()).limit(200).all()]


@router.post("/proposals/{pid}/approve")
def approve_proposal(pid: int, req: ApproveRequest, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    p = db.get(VisionProposal, pid)
    if p is None:
        raise HTTPException(404, "Proposal not found")
    if p.status != "pending":
        raise HTTPException(409, f"Proposal is already {p.status}")
    value = req.value if req.value is not None else p.proposed_value
    v = validate_market_value(db, provider, p.target, p.instrument_id, value)
    if not v["ok"]:
        raise HTTPException(400, "; ".join(v["errors"]))
    if v["requires_confirmation"] and not req.confirm_flagged:
        raise HTTPException(409, detail={"code": "confirmation_required", "warnings": v["warnings"], "message": "This value was flagged; resubmit with confirm_flagged=true to approve it."})
    try:
        analytics = apply_market_value(db, provider, p.target, p.instrument_id, value, source=f"vision:{p.source}")
    except MarketValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    p.status, p.decided_at, p.decision_note, p.applied_value = "approved", datetime.now(timezone.utc), req.note, value
    p.resolved_isin = v["resolved_isin"]
    db.add(AuditLog(action="VISION_APPROVE", entity_type="vision_proposal", entity_id=str(p.id),
                    detail_json={**analytics, "edited_by_analyst": req.value is not None and req.value != p.proposed_value, "confirmed_flagged": req.confirm_flagged, "warnings": v["warnings"]}))
    db.commit()
    return {"proposal": _proposal_out(p), "analytics": analytics}


@router.post("/proposals/{pid}/reject")
def reject_proposal(pid: int, req: RejectRequest, db: Session = Depends(get_db)):
    p = db.get(VisionProposal, pid)
    if p is None:
        raise HTTPException(404, "Proposal not found")
    if p.status != "pending":
        raise HTTPException(409, f"Proposal is already {p.status}")
    p.status, p.decided_at, p.decision_note = "rejected", datetime.now(timezone.utc), req.note
    db.add(AuditLog(action="VISION_REJECT", entity_type="vision_proposal", entity_id=str(p.id), detail_json={"note": req.note}))
    db.commit()
    return _proposal_out(p)


# ================================================================ events
class EventCreate(BaseModel):
    kind: str = Field(max_length=40)
    source: str = Field(max_length=40)
    severity: str = Field("notice", pattern="^(info|notice|alert)$")
    title: str = Field(max_length=200)
    detail: dict = {}
    source_ref: str | None = Field(None, max_length=200)


def _event_out(e: VisionEvent) -> dict:
    return {"id": e.id, "kind": e.kind, "source": e.source, "severity": e.severity, "title": e.title, "detail": e.detail_json, "source_ref": e.source_ref, "status": e.status,
            "created_at": e.created_at.isoformat()}


@router.post("/events")
def create_event(req: EventCreate, db: Session = Depends(get_db)):
    e = VisionEvent(kind=req.kind, source=req.source, severity=req.severity, title=req.title, detail_json=req.detail, source_ref=req.source_ref)
    db.add(e)
    db.commit()
    db.refresh(e)
    return _event_out(e)


@router.get("/events")
def list_events(status: str | None = Query(None, pattern="^(open|acknowledged|dismissed)$"), db: Session = Depends(get_db)):
    q = db.query(VisionEvent)
    if status:
        q = q.filter_by(status=status)
    return [_event_out(e) for e in q.order_by(VisionEvent.id.desc()).limit(200).all()]


@router.post("/events/{eid}/status")
def set_event_status(eid: int, status: str = Query(..., pattern="^(open|acknowledged|dismissed)$"), db: Session = Depends(get_db)):
    e = db.get(VisionEvent, eid)
    if e is None:
        raise HTTPException(404, "Event not found")
    e.status = status
    db.commit()
    return _event_out(e)
