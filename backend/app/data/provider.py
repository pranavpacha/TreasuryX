"""
MarketDataProvider abstraction: TreasuryX can run entirely on DemoDataProvider
(offline) or be pointed at a live provider. All providers return the same shape
of DTOs so the rest of the app never branches on data source.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class FxQuote:
    pair: str
    date: str
    rate: float
    bid: float
    ask: float
    source: str  # "DEMO" or provider name
    is_demo: bool


@dataclass(frozen=True)
class YieldPoint:
    date: str
    tenor: str
    years: float
    yield_pct: float
    source: str
    is_demo: bool


@dataclass(frozen=True)
class BondStatic:
    isin: str
    name: str
    face: float
    coupon_rate: float
    maturity_date: str
    frequency: int
    issue_date: str
    current_yield: float


class MarketDataProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def get_fx_history(self, pair: str, lookback_days: int = 400) -> list[FxQuote]: ...

    @abstractmethod
    def get_all_fx_latest(self) -> list[FxQuote]: ...

    @abstractmethod
    def get_yield_curve(self, as_of: str | None = None) -> list[YieldPoint]: ...

    @abstractmethod
    def get_yield_curve_history(self, tenor: str, lookback_days: int = 400) -> list[YieldPoint]: ...

    @abstractmethod
    def list_available_curve_dates(self) -> list[str]: ...

    @abstractmethod
    def get_bonds(self) -> list[BondStatic]: ...

    @abstractmethod
    def get_bond_yield_history(self, isin: str, lookback_days: int = 400) -> list[tuple[str, float]]: ...
