"""Idempotent startup seeding: bond reference data, a couple of illustrative demo
positions (so the terminal isn't empty on first run), and demo market events."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.data.demo_provider import get_demo_provider
from app.models.bond import Bond
from app.models.market_event import MarketEvent
from app.models.position import Position

DEMO_EVENTS = [
    ("RBI MPC holds repo rate steady; commentary seen as neutral-to-dovish.", "RATES", "INFO"),
    ("USD/INR trades in a tight range amid quiet cross-border flows.", "FX", "INFO"),
    ("10Y G-Sec yield ticks higher on modest supply concerns.", "RATES", "WARNING"),
    ("EUR/USD volatility picks up ahead of ECB commentary.", "FX", "INFO"),
]


def seed_all(db: Session) -> None:
    provider = get_demo_provider()

    if db.query(Bond).count() == 0:
        for b in provider.get_bonds():
            db.add(Bond(
                isin=b.isin, name=b.name, face=b.face, coupon_rate=b.coupon_rate,
                maturity_date=b.maturity_date, frequency=b.frequency, issue_date=b.issue_date,
            ))

    if db.query(Position).count() == 0:
        latest_fx = {q.pair: q.rate for q in provider.get_all_fx_latest()}
        db.add(Position(instrument_type="FX", instrument_id="USDINR",
                         quantity=5_000_000, entry_price=latest_fx.get("USDINR", 83.2) - 0.35, status="OPEN"))
        db.add(Position(instrument_type="FX", instrument_id="EURINR",
                         quantity=-2_000_000, entry_price=latest_fx.get("EURINR", 90.1) + 0.20, status="OPEN"))
        bonds = provider.get_bonds()
        if bonds:
            db.add(Position(instrument_type="BOND", instrument_id=bonds[0].isin,
                             quantity=10_000_000, entry_price=100.0, status="OPEN"))
            if len(bonds) > 2:
                db.add(Position(instrument_type="BOND", instrument_id=bonds[2].isin,
                                 quantity=5_000_000, entry_price=99.5, status="OPEN"))

    if db.query(MarketEvent).count() == 0:
        for headline, category, severity in DEMO_EVENTS:
            db.add(MarketEvent(headline=headline, category=category, severity=severity))

    db.commit()
