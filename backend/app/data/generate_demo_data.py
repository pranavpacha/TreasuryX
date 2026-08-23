"""
Generates clearly-labeled DEMO/SIMULATED market data so TreasuryX can run fully
offline. This is NOT real market data -- it is a deterministic (fixed-seed)
synthetic random walk anchored at plausible, round starting levels, used only
for demonstration purposes.

Run: python -m app.data.generate_demo_data
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).parent / "demo_data"
OUT_DIR.mkdir(exist_ok=True)

SEED = 20260101
N_DAYS = 400
END_DATE = date(2026, 8, 21)  # last "as-of" date for demo data (a Friday-ish anchor)

FX_PAIRS = {
    "USDINR": {"start": 83.20, "daily_vol": 0.0035},
    "EURINR": {"start": 90.10, "daily_vol": 0.0045},
    "GBPINR": {"start": 105.40, "daily_vol": 0.0050},
    "EURUSD": {"start": 1.0830, "daily_vol": 0.0060},
}

TENORS_YEARS = {
    "1M": 1 / 12, "3M": 0.25, "6M": 0.5, "1Y": 1.0,
    "2Y": 2.0, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0,
}
# Plausible starting INR G-Sec-style curve levels (demo only)
CURVE_START = {"1M": 6.55, "3M": 6.60, "6M": 6.68, "1Y": 6.75, "2Y": 6.85, "5Y": 6.95, "10Y": 7.05, "30Y": 7.20}
CURVE_DAILY_VOL_BPS = {"1M": 1.0, "3M": 1.2, "6M": 1.5, "1Y": 2.0, "2Y": 2.5, "5Y": 3.0, "10Y": 3.2, "30Y": 3.5}


def business_dates(end: date, n: int) -> list[date]:
    dates = []
    d = end
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d -= timedelta(days=1)
    return sorted(dates)


MEAN_REVERSION_KAPPA = 0.03  # pulls the walk back toward its anchor level each day


def generate_fx() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    dates = business_dates(END_DATE, N_DAYS)
    rows = []
    for pair, cfg in FX_PAIRS.items():
        anchor = cfg["start"]
        prices = [anchor]
        shocks = rng.normal(0, cfg["daily_vol"], len(dates) - 1)
        for shock in shocks:
            prev = prices[-1]
            reverting_return = MEAN_REVERSION_KAPPA * (anchor - prev) / anchor + shock
            prices.append(prev * (1 + reverting_return))
        for d, p in zip(dates, prices):
            spread = p * 0.0004
            rows.append({
                "date": d.isoformat(), "pair": pair, "rate": round(p, 4),
                "bid": round(p - spread / 2, 4), "ask": round(p + spread / 2, 4),
            })
    return pd.DataFrame(rows)


def generate_yield_curve() -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 1)
    dates = business_dates(END_DATE, N_DAYS)
    rows = []
    history = {t: [] for t in TENORS_YEARS}
    for t in TENORS_YEARS:
        vol_pct_points = CURVE_DAILY_VOL_BPS[t] / 100.0  # bps/day -> percentage-point/day std
        anchor = CURVE_START[t]
        level = anchor
        path = [level]
        for _ in range(len(dates) - 1):
            shock = rng.normal(0, vol_pct_points)
            reverting = MEAN_REVERSION_KAPPA * (anchor - level)
            level = max(0.5, level + reverting + shock)
            path.append(level)
        history[t] = path
    for i, d in enumerate(dates):
        for t in TENORS_YEARS:
            rows.append({"date": d.isoformat(), "tenor": t, "years": TENORS_YEARS[t], "yield_pct": round(history[t][i], 4)})
    return pd.DataFrame(rows)


def generate_bonds() -> list[dict]:
    return [
        {"isin": "IN0020240001", "name": "GS 7.10% 2029", "face": 100.0, "coupon_rate": 0.0710,
         "maturity_date": "2029-04-08", "frequency": 2, "issue_date": "2024-04-08", "current_yield": 7.02},
        {"isin": "IN0020240002", "name": "GS 7.18% 2033", "face": 100.0, "coupon_rate": 0.0718,
         "maturity_date": "2033-07-24", "frequency": 2, "issue_date": "2024-07-24", "current_yield": 7.05},
        {"isin": "IN0020240003", "name": "GS 7.25% 2036", "face": 100.0, "coupon_rate": 0.0725,
         "maturity_date": "2036-06-22", "frequency": 2, "issue_date": "2024-06-22", "current_yield": 7.10},
        {"isin": "IN0020240004", "name": "GS 6.99% 2026", "face": 100.0, "coupon_rate": 0.0699,
         "maturity_date": "2026-12-15", "frequency": 2, "issue_date": "2021-12-15", "current_yield": 6.80},
        {"isin": "IN0020240005", "name": "GS 7.30% 2053", "face": 100.0, "coupon_rate": 0.0730,
         "maturity_date": "2053-06-19", "frequency": 2, "issue_date": "2023-06-19", "current_yield": 7.18},
    ]


def generate_bond_price_history(bonds: list[dict]) -> pd.DataFrame:
    """Synthesize a plausible daily yield history per bond by jittering around current_yield."""
    rng = np.random.default_rng(SEED + 2)
    dates = business_dates(END_DATE, N_DAYS)
    rows = []
    for b in bonds:
        anchor = b["current_yield"] / 100.0
        path = [anchor]
        for _ in range(len(dates) - 1):
            prev = path[-1]
            reverting = MEAN_REVERSION_KAPPA * (anchor - prev)
            path.append(max(0.005, prev + reverting + rng.normal(0, 0.0003)))
        for d, yld in zip(dates, path):
            rows.append({"date": d.isoformat(), "isin": b["isin"], "yield": round(yld, 6)})
    return pd.DataFrame(rows)


def main():
    fx = generate_fx()
    fx.to_csv(OUT_DIR / "fx_history.csv", index=False)

    curve = generate_yield_curve()
    curve.to_csv(OUT_DIR / "yield_curve_history.csv", index=False)

    bonds = generate_bonds()
    (OUT_DIR / "bonds.json").write_text(json.dumps(bonds, indent=2))

    bond_hist = generate_bond_price_history(bonds)
    bond_hist.to_csv(OUT_DIR / "bond_yield_history.csv", index=False)

    print(f"Wrote demo data to {OUT_DIR}")
    print(f"FX rows: {len(fx)}, Curve rows: {len(curve)}, Bonds: {len(bonds)}, Bond yield rows: {len(bond_hist)}")


if __name__ == "__main__":
    main()
