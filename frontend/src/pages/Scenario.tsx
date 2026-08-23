import { useState } from "react";
import { Panel, fmtInr, toneFor } from "../components/Common";
import type { ScenarioResponse } from "../services/api";
import { runScenario } from "../services/api";

const PRESETS: { label: string; fx: Record<string, number>; parallel: number; tilt: number }[] = [
  { label: "USD/INR +2%", fx: { USDINR: 0.02 }, parallel: 0, tilt: 0 },
  { label: "USD/INR -1%", fx: { USDINR: -0.01 }, parallel: 0, tilt: 0 },
  { label: "10Y +25bp (parallel)", fx: {}, parallel: 25, tilt: 0 },
  { label: "10Y +50bp (parallel)", fx: {}, parallel: 50, tilt: 0 },
  { label: "Curve steepening (+30bp tilt)", fx: {}, parallel: 0, tilt: 30 },
  { label: "Curve flattening (-30bp tilt)", fx: {}, parallel: 0, tilt: -30 },
  { label: "Combined stress: USD/INR +2%, 2Y +10bp, 10Y +50bp", fx: { USDINR: 0.02 }, parallel: 15, tilt: 30 },
];

export default function Scenario() {
  const [fxShockPct, setFxShockPct] = useState(0);
  const [parallelBps, setParallelBps] = useState(0);
  const [tiltBps, setTiltBps] = useState(0);
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [running, setRunning] = useState(false);

  const run = async (label: string, fxPct: Record<string, number>, parallel: number, tilt: number) => {
    setRunning(true);
    try {
      const r = await runScenario({
        label, fx_shock_pct: fxPct, parallel_yield_shock_bps: parallel, curve_tilt_bps: tilt, per_bond_yield_shock_bps: {},
      });
      setResult(r);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <Panel title="Preset Shocks">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {PRESETS.map((p) => (
            <button key={p.label} disabled={running} onClick={() => run(p.label, p.fx, p.parallel, p.tilt)}>{p.label}</button>
          ))}
        </div>
      </Panel>

      <Panel title="Custom Shock">
        <div className="grid grid-3">
          <div className="field"><label>USD/INR shock (%)</label><input type="number" value={fxShockPct} onChange={(e) => setFxShockPct(Number(e.target.value))} /></div>
          <div className="field"><label>Parallel yield shock (bps)</label><input type="number" value={parallelBps} onChange={(e) => setParallelBps(Number(e.target.value))} /></div>
          <div className="field"><label>Curve tilt (bps, +steepen/-flatten)</label><input type="number" value={tiltBps} onChange={(e) => setTiltBps(Number(e.target.value))} /></div>
        </div>
        <button className="primary" disabled={running} onClick={() => run("Custom scenario", { USDINR: fxShockPct / 100 }, parallelBps, tiltBps)}>
          Run Custom Scenario
        </button>
      </Panel>

      {result && (
        <Panel title={`Scenario Result — SCN-${String(result.id).padStart(5, "0")}: ${result.label}`}>
          <div className="grid grid-3" style={{ marginBottom: 12 }}>
            <div className="metric">
              <div className="metric-label">Total P&L</div>
              <div className={`metric-value ${toneFor(result.total_pnl)}`}>{fmtInr(result.total_pnl)}</div>
            </div>
            <div className="metric">
              <div className="metric-label">FX P&L</div>
              <div className={`metric-value ${toneFor(result.total_fx_pnl)}`}>{fmtInr(result.total_fx_pnl)}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Bond P&L (exact reprice)</div>
              <div className={`metric-value ${toneFor(result.total_bond_pnl)}`}>{fmtInr(result.total_bond_pnl)}</div>
            </div>
          </div>

          <table className="data-table" style={{ marginBottom: 12 }}>
            <thead><tr><th>Instrument</th><th>Type</th><th>Shocked Level</th><th>Incremental P&L</th></tr></thead>
            <tbody>
              {Object.entries(result.fx_pnl_by_pair).map(([pair, pnl]) => (
                <tr key={pair}><td>{pair}</td><td>FX</td><td>{result.shocked_fx_rates[pair]?.toFixed(4)}</td><td className={toneFor(pnl)}>{fmtInr(pnl)}</td></tr>
              ))}
              {Object.entries(result.bond_pnl_by_isin).map(([isin, pnl]) => (
                <tr key={isin}><td>{isin}</td><td>Bond</td><td>{result.shocked_bond_yields[isin]?.toFixed(3)}%</td><td className={toneFor(pnl)}>{fmtInr(pnl)}</td></tr>
              ))}
            </tbody>
          </table>

          <div className="panel-title">Methodology / Audit Trail</div>
          <ul style={{ fontSize: 11, color: "var(--text-mid)", margin: 0, paddingLeft: 18 }}>
            {result.method_notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
          <hr className="sep" />
          <div style={{ fontSize: 10.5, color: "var(--text-lo)" }} className="mono">
            Inputs: {JSON.stringify(result.inputs)}
          </div>
        </Panel>
      )}
    </div>
  );
}
