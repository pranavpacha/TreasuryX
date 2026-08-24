from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data.provider import MarketDataProvider
from app.database import get_db
from app.dependencies import get_provider
from app.finance.scenario_engine import BondPositionInput, FxPositionInput, ShockInput, run_scenario
from app.models.position import Position
from app.models.scenario import ScenarioRun
from app.schemas.scenario import ScenarioRequest, ScenarioResponse
from app.services.market_view import effective_bonds, effective_fx_quotes

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


@router.post("/run", response_model=ScenarioResponse)
def run_scenario_endpoint(
    req: ScenarioRequest, db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_provider),
):
    latest_fx = {q.pair: q.rate for q in effective_fx_quotes(db, provider)}
    bonds_by_isin = {b.isin: b for b in effective_bonds(db, provider)}

    fx_inputs = []
    for pos in db.query(Position).filter(Position.instrument_type == "FX", Position.status == "OPEN").all():
        rate = latest_fx.get(pos.instrument_id)
        if rate is None:
            continue
        fx_inputs.append(FxPositionInput(pair=pos.instrument_id, notional_base=pos.quantity, entry_rate=pos.entry_price, current_rate=rate))

    bond_inputs = []
    for pos in db.query(Position).filter(Position.instrument_type == "BOND", Position.status == "OPEN").all():
        b = bonds_by_isin.get(pos.instrument_id)
        if b is None:
            continue
        years = max(0.05, (date.fromisoformat(b.maturity_date) - date.today()).days / 365.25)
        bond_inputs.append(BondPositionInput(
            isin=b.isin, face=b.face, coupon_rate=b.coupon_rate, current_yield=b.current_yield / 100.0,
            years_to_maturity=years, frequency=b.frequency, quantity=pos.quantity,
        ))

    shock = ShockInput(
        fx_shock_pct=req.fx_shock_pct, parallel_yield_shock_bps=req.parallel_yield_shock_bps,
        curve_tilt_bps=req.curve_tilt_bps, per_bond_yield_shock_bps=req.per_bond_yield_shock_bps,
    )
    result = run_scenario(fx_inputs, bond_inputs, shock)

    method_notes = [
        "FX P&L = (shocked_rate - current_rate) * notional_base, incremental to current MTM.",
        "Bond P&L uses EXACT full repricing of the bond pricing model at the shocked yield "
        "(parallel shock + tilt around a 5Y pivot + any per-bond override), not just the duration approximation.",
        "Scenario is fully deterministic: no random numbers or AI-generated values are used.",
    ]

    scenario_row = ScenarioRun(
        label=req.label,
        inputs_json=req.model_dump(),
        outputs_json={
            "fx_pnl_by_pair": result.fx_pnl_by_pair, "bond_pnl_by_isin": result.bond_pnl_exact_by_isin,
            "total_pnl": result.total_pnl,
        },
        total_pnl=result.total_pnl,
    )
    db.add(scenario_row)
    db.commit()
    db.refresh(scenario_row)

    return ScenarioResponse(
        id=scenario_row.id, label=req.label, inputs=req.model_dump(),
        fx_pnl_by_pair=result.fx_pnl_by_pair, bond_pnl_by_isin=result.bond_pnl_exact_by_isin,
        total_fx_pnl=result.total_fx_pnl, total_bond_pnl=result.total_bond_pnl, total_pnl=result.total_pnl,
        shocked_fx_rates=result.shocked_fx_rates, shocked_bond_yields={k: round(v * 100, 4) for k, v in result.shocked_bond_yields.items()},
        method_notes=method_notes,
    )


@router.get("/history", response_model=list[ScenarioResponse])
def scenario_history(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(ScenarioRun).order_by(ScenarioRun.id.desc()).limit(limit).all()
    out = []
    for r in rows:
        out.append(ScenarioResponse(
            id=r.id, label=r.label, inputs=r.inputs_json,
            fx_pnl_by_pair=r.outputs_json.get("fx_pnl_by_pair", {}),
            bond_pnl_by_isin=r.outputs_json.get("bond_pnl_by_isin", {}),
            total_fx_pnl=sum(r.outputs_json.get("fx_pnl_by_pair", {}).values()),
            total_bond_pnl=sum(r.outputs_json.get("bond_pnl_by_isin", {}).values()),
            total_pnl=r.total_pnl, shocked_fx_rates={}, shocked_bond_yields={}, method_notes=[],
        ))
    return out
