"""
Effective market view: baseline DemoDataProvider values with any active MarketOverride applied
on top. Every part of the app that needs "the current yield/rate" (bond analytics, risk,
scenario base levels, the 3D yield surface's latest point) should go through this module rather
than reading the provider directly, so a CV-committed correction is visible everywhere
consistently.
"""
from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from app.data.provider import BondStatic, FxQuote, MarketDataProvider
from app.services.overrides import get_overrides_map


def effective_bonds(db: Session, provider: MarketDataProvider) -> list[BondStatic]:
    overrides = get_overrides_map(db, "BOND", "yield_pct")
    bonds = provider.get_bonds()
    if not overrides:
        return bonds
    return [
        replace(b, current_yield=overrides[b.isin]) if b.isin in overrides else b
        for b in bonds
    ]


def effective_bond(db: Session, provider: MarketDataProvider, isin: str) -> BondStatic | None:
    override = get_overrides_map(db, "BOND", "yield_pct").get(isin)
    bond = next((b for b in provider.get_bonds() if b.isin == isin), None)
    if bond is None:
        return None
    return replace(bond, current_yield=override) if override is not None else bond


def effective_fx_quotes(db: Session, provider: MarketDataProvider) -> list[FxQuote]:
    overrides = get_overrides_map(db, "FX", "rate")
    quotes = provider.get_all_fx_latest()
    if not overrides:
        return quotes
    out = []
    for q in quotes:
        if q.pair in overrides:
            rate = overrides[q.pair]
            spread = q.ask - q.bid
            out.append(replace(q, rate=rate, bid=rate - spread / 2, ask=rate + spread / 2, source="CV_CORRECTED"))
        else:
            out.append(q)
    return out


def effective_fx_rate(db: Session, provider: MarketDataProvider, pair: str) -> float | None:
    override = get_overrides_map(db, "FX", "rate").get(pair)
    if override is not None:
        return override
    quote = next((q for q in provider.get_all_fx_latest() if q.pair == pair), None)
    return quote.rate if quote else None
