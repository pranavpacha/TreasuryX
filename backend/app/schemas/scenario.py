from __future__ import annotations

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    label: str = "Custom scenario"
    fx_shock_pct: dict[str, float] = Field(default_factory=dict)
    parallel_yield_shock_bps: float = 0.0
    curve_tilt_bps: float = 0.0
    per_bond_yield_shock_bps: dict[str, float] = Field(default_factory=dict)


class ScenarioResponse(BaseModel):
    id: int
    label: str
    inputs: dict
    fx_pnl_by_pair: dict[str, float]
    bond_pnl_by_isin: dict[str, float]
    total_fx_pnl: float
    total_bond_pnl: float
    total_pnl: float
    shocked_fx_rates: dict[str, float]
    shocked_bond_yields: dict[str, float]
    method_notes: list[str]
