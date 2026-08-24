import { Panel } from "../components/Common";

const FORMULAS = [
  {
    name: "FX P&L", formula: "P&L = (current_rate − entry_rate) × notional_base",
    inputs: "entry_rate, current_rate, signed notional_base (+long / −short)",
    assumptions: "Quote convention BASE/QUOTE (e.g. USD/INR = INR per USD)",
    example: "Long 5,000,000 USD @ 83.20, now 83.55 → P&L = (83.55−83.20)×5,000,000 = ₹17.5L",
  },
  {
    name: "Historical Volatility", formula: "daily_vol = stdev(ln(Pₜ/Pₜ₋₁)); annualized = daily_vol × √252",
    inputs: "Price series over a lookback window",
    assumptions: "i.i.d. returns (square-root-of-time rule) — a standard simplification",
    example: "See FX Desk page tooltip for the live computed value per pair",
  },
  {
    name: "Bond Price (clean/dirty)", formula: "Price = Σ CFₖ / (1+y/f)^(k−t); accrued = (face×coupon/f)×t; clean = dirty − accrued",
    inputs: "face, coupon_rate, yield, years_to_maturity, frequency f, settle_frac t",
    assumptions: "Equal-length coupon periods (not a full Act/Act/30-360 day-count)",
    example: "See Rates & Bonds page for live-computed prices",
  },
  {
    name: "YTM", formula: "Solve Price(y) = market_price for y via Brent's method",
    inputs: "price, face, coupon_rate, years_to_maturity, frequency",
    assumptions: "Bracket search over y ∈ [−99%, 500%]; raises an error rather than guessing if no solution exists",
    example: "GET /api/bonds/{isin}/ytm?price=...",
  },
  {
    name: "Modified Duration / Convexity / DV01", formula: "Computed via numerical bump-and-reprice: ModDur = −(P(y+bp)−P(y−bp))/(2·bp·P(y)); DV01 = (P(y−bp)−P(y+bp))/2",
    inputs: "The same bond pricing function, bumped by ±1bp",
    assumptions: "Guarantees consistency with the actual pricing model (vs. an independently-derived closed form that could silently diverge)",
    example: "See Rates & Bonds page tooltips",
  },
  {
    name: "Historical VaR / Expected Shortfall", formula: "VaR = −percentile(returns, (1−conf)×100) × portfolio_value; ES = −mean(tail returns beyond VaR) × portfolio_value",
    inputs: "Reconstructed historical portfolio-value returns (no look-ahead), confidence, horizon",
    assumptions: "Empirical/historical, not parametric-normal; needs ≥20 observations",
    example: "See Risk page",
  },
];

export default function Methodology() {
  return (
    <div>
      <Panel title="Financial Calculation Methodology">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          The formula shown for each metric matches the actual implementation in <code>backend/app/finance/</code> —
          see <code>docs/finance_methodology.md</code> for the full derivation and every simplification made.
        </p>
      </Panel>
      {FORMULAS.map((f) => (
        <Panel key={f.name} title={f.name}>
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left", width: 140 }}>Formula</td><td style={{ textAlign: "left" }} className="mono">{f.formula}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Inputs</td><td style={{ textAlign: "left" }}>{f.inputs}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Assumptions</td><td style={{ textAlign: "left" }}>{f.assumptions}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Example</td><td style={{ textAlign: "left" }}>{f.example}</td></tr>
            </tbody>
          </table>
        </Panel>
      ))}
    </div>
  );
}
