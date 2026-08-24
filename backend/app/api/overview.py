from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.risk import risk_summary
from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.models.market_event import MarketEvent
from app.services.market_view import effective_bonds, effective_fx_quotes
from app.services.overrides import list_active_overrides

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("")
def overview(db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider)):
    fx = effective_fx_quotes(db, provider)
    dates = provider.list_available_curve_dates()
    curve = provider.get_yield_curve(dates[-1]) if dates else []
    bonds = effective_bonds(db, provider)
    risk = risk_summary(db=db, provider=provider)
    events = db.query(MarketEvent).order_by(desc(MarketEvent.created_at)).limit(8).all()
    overrides = list_active_overrides(db)

    return {
        "as_of": dates[-1] if dates else None,
        "fx_snapshot": [{"pair": q.pair, "rate": q.rate, "is_cv_corrected": q.source == "CV_CORRECTED"} for q in fx],
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
        "data_status": {
            "mode": "DEMO",
            "last_updated": dates[-1] if dates else None,
            "source": "DemoDataProvider (synthetic, offline)",
            "active_cv_corrections": [
                {"instrument_type": o.instrument_type, "instrument_id": o.instrument_id, "field": o.field, "value": o.value, "applied_at": o.created_at.isoformat()}
                for o in overrides
            ],
        },
        "disclaimer": "Educational/simulated Treasury analytics platform. No real-money trading. "
                       "Outputs are for academic and demonstration purposes only.",
    }
