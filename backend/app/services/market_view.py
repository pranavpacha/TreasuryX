"""
Effective market view: baseline DemoDataProvider values with any active MarketOverride applied
on top. Every part of the app that needs "the current yield/rate" (bond analytics, risk,
scenario base levels, the 3D yield surface's latest point) should go through this module rather
than reading the provider directly, so a CV-committed correction is visible everywhere
consistently.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from app.data.provider import BondStatic, FxQuote, MarketDataProvider
from app.services.overrides import get_overrides_map

TENOR_RE = re.compile(r"^(\d{1,2})([MY])$", re.IGNORECASE)


def tenor_to_years(tenor: str) -> float | None:
    """Parse a tenor label ('3M', '10Y', ...) into fractional years, or None if it isn't
    a recognizable tenor string."""
    m = TENOR_RE.match(tenor.strip().upper())
    if not m:
        return None
    n, unit = m.groups()
    return int(n) / 12.0 if unit == "M" else float(n)


def find_bond_by_tenor(bonds: list[BondStatic], tenor_years: float, as_of: date, tolerance: float = 0.35) -> BondStatic | None:
    """Find the bond whose CURRENT years-to-maturity (relative to `as_of`, never baked in
    as a stale constant) is closest to the requested tenor, but only if it's within a
    generous relative tolerance -- a general, always-recomputed mapping rather than a
    static tenor->ISIN table (which would need editing as bonds approach maturity and
    would silently go wrong, the same class of bug as a hard-coded 'today').

    Returns None (never an invented/best-effort-anyway match) when nothing in the book is
    close enough to be a reasonable stand-in for the requested tenor.
    """
    best: tuple[float, BondStatic] | None = None
    for b in bonds:
        years = (date.fromisoformat(b.maturity_date) - as_of).days / 365.25
        if years <= 0:
            continue
        rel_diff = abs(years - tenor_years) / max(tenor_years, years, 1.0)
        if best is None or rel_diff < best[0]:
            best = (rel_diff, b)
    if best is None or best[0] > tolerance:
        return None
    return best[1]


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
