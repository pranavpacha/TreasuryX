# Finance Methodology

All formulas below are implemented in `backend/app/finance/` and independently unit-tested in
`backend/tests/`. Where a simplification was necessary for a laptop-scale educational build, it is
called out explicitly — see also [assumptions.md](assumptions.md).

## FX P&L (`finance/fx.py::fx_pnl`)

Quote convention: pairs are BASE/QUOTE (e.g. USD/INR = INR per 1 USD). Position sign: positive
`notional_base` = long base currency, negative = short.

```
P&L (quote ccy) = (current_rate - entry_rate) * notional_base
return_pct      = (current_rate - entry_rate) / entry_rate
```

A short position (`notional_base < 0`) automatically profits when the rate falls, tested explicitly
in `test_fx.py::test_fx_pnl_short_profit_when_rate_falls`.

## Volatility (`finance/fx.py::historical_volatility`)

1. **Log returns**: `r_t = ln(P_t / P_{t-1})` over the observation window.
2. **Daily volatility** = sample standard deviation of those returns (`ddof=1`).
3. **Annualization** (optional): `daily_vol * sqrt(252)` — the square-root-of-time rule, which
   assumes i.i.d. returns (a standard simplification, not strictly true for real FX).

Every place volatility is displayed in the UI labels whether it's daily or annualized (never mixed
silently).

## Bond Pricing (`finance/bonds.py::bond_price`)

```
Price = Σ_{k=1..n} CF_k / (1 + y/f)^(k - settle_frac)
```
where `f` = coupon frequency/year, `n` = remaining coupon periods, `y` = annual (nominal,
compounded `f`×/yr) yield, `settle_frac ∈ [0,1)` = how far into the current coupon period the
valuation date sits. `settle_frac = 0` (valuation exactly on a coupon date) gives the **clean**
price directly; `settle_frac > 0` gives the **dirty** price, and
`clean = dirty - accrued_interest`, where `accrued_interest = (face * coupon_rate / f) * settle_frac`.

**Simplification**: periods are treated as equal-length (a fractional-period convention), not a full
Act/Act or 30/360 calendar day-count. This is explicitly an educational simplification.

## YTM (`finance/bonds.py::ytm`)

Solved via Brent's method (`scipy.optimize.brentq`) over a wide bracket `y ∈ [-99%, 500%]`.
Raises `BondError` if no sign change is found in that bracket (no valid yield) or if the solver
doesn't converge — never silently returns a wrong number.

## Duration, Convexity, DV01 (`finance/bonds.py::duration_convexity_dv01`)

- **Macaulay duration** (years): `(1/f) * Σ_k [k * CF_k/(1+y/f)^k] / Price` — computed analytically.
- **Modified Duration, Convexity, DV01**: computed via **numerical bump-and-reprice** (central finite
  differences) directly against `bond_price`, at a 1bp bump:
  ```
  ModDur     = -(P(y+bump) - P(y-bump)) / (2 * bump * P(y))
  Convexity  = (P(y+bump) + P(y-bump) - 2*P(y)) / (bump^2 * P(y))
  DV01       = (P(y-bump) - P(y+bump)) / 2
  ```
  This was a deliberate design choice: deriving Modified Duration/Convexity as separate closed-form
  formulas risks a subtle mismatch with whatever pricing convention `bond_price` actually uses.
  Bump-and-reprice guarantees Modified Duration/Convexity/DV01 are *always* consistent with the
  pricing function, and it's directly testable against a manual two-point reprice
  (`test_bonds.py::test_dv01_matches_manual_bump_reprice`). The analytic Macaulay Duration is then
  cross-checked against Modified Duration via `ModDur = Macaulay / (1 + y/f)`
  (`test_bonds.py::test_modified_duration_less_than_macaulay_for_positive_yield`).

## Bond Stress P&L: Approximation vs. Exact (`finance/bonds.py`)

- **Duration + convexity approximation**: `dP ≈ Price * (-ModDur*dy + 0.5*Convexity*dy²)`
  (`duration_based_price_change`).
- **Exact repricing**: full re-evaluation of `bond_price` at the shocked yield
  (`exact_reprice_change`).

The scenario engine (below) always reports the **exact** repricing P&L, but both are tested against
each other to show where the 2nd-order approximation starts to diverge for large shocks
(`test_bonds.py::test_duration_approx_diverges_from_exact_for_large_shock`).

## Historical VaR & Expected Shortfall (`finance/risk_metrics.py::historical_var_es`)

- **Method**: historical (empirical), not parametric/normal.
- **No look-ahead**: callers (see `risk/aggregator.py::portfolio_daily_returns`) only ever pass
  returns reconstructed from *already-observed* past market data up to the current "as of" date —
  positions' current quantities are held fixed and only historical price/yield levels vary.
- 1-day horizon by default; `VaR_alpha = -percentile(returns, (1-alpha)*100) * portfolio_value`,
  scaled by `sqrt(horizon_days)`. `ES_alpha = -mean(returns in the tail beyond VaR) * portfolio_value`.
- Requires ≥20 observations; raises `RiskError` otherwise rather than returning a misleading number.

## Scenario Engine (`finance/scenario_engine.py::run_scenario`)

Fully deterministic — given FX shocks (%, per pair) and yield shocks (parallel bps + a curve "tilt"
pivoted at 5Y, +extra per-bond override), it recomputes shocked FX rates / bond yields and reprices
every position **exactly** (full `bond_price` re-evaluation, not just the duration approximation).
No randomness, no ML, no LLM-generated numbers anywhere in this path. Every run via
`POST /api/scenario/run` is persisted (`ScenarioRun` table) with its inputs, outputs, and method
notes for audit (`GET /api/scenario/history`).

## Market Regime Classification (`finance/regime.py::classify_regime`)

A **documented, rule-based** classifier (not a trained/ML model): thresholds on recent FX
annualized volatility, cumulative FX return, and 10Y-2Y curve slope change label the regime as one
of `NORMAL / RISK-ON / RISK-OFF / HIGH-VOLATILITY / CURVE-STEEPENING / CURVE-FLATTENING`. Always
described in the UI as a "decision-support signal," never a prediction.
