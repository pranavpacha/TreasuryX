"""
DemoDataProvider: reads the pre-generated, clearly-labeled DEMO/SIMULATED CSV/JSON
files (see generate_demo_data.py) so the whole app works with zero internet access.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.data.provider import BondStatic, FxQuote, MarketDataProvider, YieldPoint

DATA_DIR = Path(__file__).parent / "demo_data"


class DemoDataProvider(MarketDataProvider):
    name = "DEMO"

    def __init__(self) -> None:
        self._fx = pd.read_csv(DATA_DIR / "fx_history.csv")
        self._curve = pd.read_csv(DATA_DIR / "yield_curve_history.csv")
        self._bonds = json.loads((DATA_DIR / "bonds.json").read_text())
        self._bond_yield = pd.read_csv(DATA_DIR / "bond_yield_history.csv")

    def get_fx_history(self, pair: str, lookback_days: int = 400) -> list[FxQuote]:
        df = self._fx[self._fx["pair"] == pair].sort_values("date").tail(lookback_days)
        return [
            FxQuote(pair=r.pair, date=r.date, rate=r.rate, bid=r.bid, ask=r.ask, source=self.name, is_demo=True)
            for r in df.itertuples()
        ]

    def get_all_fx_latest(self) -> list[FxQuote]:
        latest_date = self._fx["date"].max()
        df = self._fx[self._fx["date"] == latest_date]
        return [
            FxQuote(pair=r.pair, date=r.date, rate=r.rate, bid=r.bid, ask=r.ask, source=self.name, is_demo=True)
            for r in df.itertuples()
        ]

    def get_yield_curve(self, as_of: str | None = None) -> list[YieldPoint]:
        target = as_of or self._curve["date"].max()
        df = self._curve[self._curve["date"] == target].sort_values("years")
        if df.empty:
            raise ValueError(f"No yield curve data for date {target}")
        return [
            YieldPoint(date=r.date, tenor=r.tenor, years=r.years, yield_pct=r.yield_pct, source=self.name, is_demo=True)
            for r in df.itertuples()
        ]

    def get_yield_curve_history(self, tenor: str, lookback_days: int = 400) -> list[YieldPoint]:
        df = self._curve[self._curve["tenor"] == tenor].sort_values("date").tail(lookback_days)
        return [
            YieldPoint(date=r.date, tenor=r.tenor, years=r.years, yield_pct=r.yield_pct, source=self.name, is_demo=True)
            for r in df.itertuples()
        ]

    def list_available_curve_dates(self) -> list[str]:
        return sorted(self._curve["date"].unique().tolist())

    def get_bonds(self) -> list[BondStatic]:
        return [BondStatic(**b) for b in self._bonds]

    def get_bond_yield_history(self, isin: str, lookback_days: int = 400) -> list[tuple[str, float]]:
        df = self._bond_yield[self._bond_yield["isin"] == isin].sort_values("date").tail(lookback_days)
        return list(zip(df["date"].tolist(), df["yield"].tolist()))


@lru_cache
def get_demo_provider() -> DemoDataProvider:
    return DemoDataProvider()
