"""
Market override service: the mechanism by which a Computer-Vision-extracted value (or any
future manual correction) actually changes what the rest of TreasuryX sees -- bond analytics,
risk, and the 3D yield surface all check for an active override before falling back to the
DemoDataProvider's baseline value. This is what makes "Apply to Treasury" a real state change
instead of a one-off calculation shown once and discarded.
"""
from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.market_override import MarketOverride


def set_override(
    db: Session, instrument_type: str, instrument_id: str, field: str, value: float,
    source: str = "cv_extraction", cv_extraction_id: int | None = None,
) -> MarketOverride:
    """Latest-wins: replace any existing override for this (type, id, field) key."""
    db.execute(
        delete(MarketOverride).where(
            MarketOverride.instrument_type == instrument_type,
            MarketOverride.instrument_id == instrument_id,
            MarketOverride.field == field,
        )
    )
    row = MarketOverride(
        instrument_type=instrument_type, instrument_id=instrument_id, field=field,
        value=value, source=source, cv_extraction_id=cv_extraction_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_override(db: Session, instrument_type: str, instrument_id: str, field: str) -> float | None:
    row = (
        db.query(MarketOverride)
        .filter(
            MarketOverride.instrument_type == instrument_type,
            MarketOverride.instrument_id == instrument_id,
            MarketOverride.field == field,
        )
        .first()
    )
    return row.value if row else None


def get_overrides_map(db: Session, instrument_type: str, field: str) -> dict[str, float]:
    rows = db.query(MarketOverride).filter(
        MarketOverride.instrument_type == instrument_type, MarketOverride.field == field,
    ).all()
    return {r.instrument_id: r.value for r in rows}


def list_active_overrides(db: Session) -> list[MarketOverride]:
    return db.query(MarketOverride).order_by(MarketOverride.created_at.desc()).all()


def clear_override(db: Session, instrument_type: str, instrument_id: str, field: str) -> None:
    db.execute(
        delete(MarketOverride).where(
            MarketOverride.instrument_type == instrument_type,
            MarketOverride.instrument_id == instrument_id,
            MarketOverride.field == field,
        )
    )
    db.commit()
