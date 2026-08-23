from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.risk import risk_summary
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.models.market_event import MarketEvent

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("")
def overview(db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    fx = provider.get_all_fx_latest()
    dates = provider.list_available_curve_dates()
    curve = provider.get_yield_curve(dates[-1]) if dates else []
    bonds = provider.get_bonds()
    risk = risk_summary(db=db, provider=provider)
    events = db.query(MarketEvent).order_by(desc(MarketEvent.created_at)).limit(8).all()

    return {
        "as_of": dates[-1] if dates else None,
        "fx_snapshot": [{"pair": q.pair, "rate": q.rate} for q in fx],
        "curve_snapshot": [{"tenor": p.tenor, "yield_pct": p.yield_pct} for p in curve],
        "selected_bond": {
            "isin": bonds[0].isin, "name": bonds[0].name, "current_yield_pct": bonds[0].current_yield,
        } if bonds else None,
        "risk": risk,
        "market_events": [
            {"headline": e.headline, "category": e.category, "severity": e.severity, "created_at": e.created_at.isoformat()}
            for e in events
        ],
        "is_demo": True,
        "disclaimer": "Educational/simulated Treasury analytics platform. No real-money trading. "
                       "Outputs are for academic and demonstration purposes only.",
    }
