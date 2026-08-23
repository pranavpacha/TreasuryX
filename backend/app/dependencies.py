from __future__ import annotations

from app.data.demo_provider import get_demo_provider
from app.data.provider import MarketDataProvider


def get_provider() -> MarketDataProvider:
    return get_demo_provider()
