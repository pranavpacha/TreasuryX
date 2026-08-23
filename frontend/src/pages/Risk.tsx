import { useState } from "react";
import { ErrorState, LoadingState, Metric, Panel, Tooltip, fmtInr, toneFor } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchRiskSummary } from "../services/api";

export default function Risk() {
  const [confidence, setConfidence] = useState(0.95);
  const [lookback, setLookback] = useState(250);
  const { data, loading, error, reload } = useApi(() => fetchRiskSummary(confidence, lookback), [confidence, lookback]);

  return (
    <div>
      <Panel title="Risk Parameters" right={
        <div style={{ display: "flex", gap: 8 }}>
          <select value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}>
            <option value={0.95}>95% confidence</option>
            <option value={0.99}>99% confidence</option>
          </select>
          <select value={lookback} onChange={(e) => setLookback(Number(e.target.value))}>
            <option value={120}>120d lookback</option>
            <option value={250}>250d lookback</option>
          </select>
          <button onClick={reload}>Refresh</button>
        </div>
      }>
        <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
          Historical VaR / Expected Shortfall use only past (already-observed) daily returns of the reconstructed portfolio value
          up to the current date — no look-ahead bias.
        </p>
      </Panel>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && (
        <>
          <div className="grid grid-4">
            <Panel title="Historical VaR">
              {data.var ? (
                <Metric label={`${data.var.confidence * 100}% / ${data.var.horizon_days}d`} value={fmtInr(data.var.var_amount_inr)} sub={`historical, ${data.var.lookback_obs} obs`} />
              ) : <div className="empty-state">{data.var_warning}</div>}
            </Panel>
            <Panel title="Expected Shortfall">
              {data.var ? (
                <Metric label="Avg loss beyond VaR" value={fmtInr(data.var.es_amount_inr)} tone="down" />
              ) : <div className="empty-state">N/A</div>}
            </Panel>
            <Panel title="Max Drawdown">
              <Metric label="Reconstructed P&L series" value={fmtInr(data.max_drawdown_inr)} tone={toneFor(data.max_drawdown_inr)} />
            </Panel>
            <Panel title="Market Regime">
              <Metric label="Rule-based classification" value={data.regime} />
              <div style={{ fontSize: 10.5, color: "var(--text-lo)", marginTop: 4 }}>{data.regime_reasons.join("; ")}</div>
            </Panel>
          </div>

          <div className="grid grid-2">
            <Panel title="Exposures">
              <table className="data-table">
                <tbody>
                  <tr><td>FX Exposure (abs, INR)</td><td>{fmtInr(data.fx_exposure_inr)}</td></tr>
                  <tr><td>FX P&L</td><td className={toneFor(data.fx_pnl_inr)}>{fmtInr(data.fx_pnl_inr)}</td></tr>
                  <tr><td>Bond Market Value</td><td>{fmtInr(data.bond_market_value_inr)}</td></tr>
                  <tr><td>Bond DV01 <Tooltip text="Aggregate price impact of a 1bp parallel yield move across bond positions" /></td><td>{fmtInr(data.bond_dv01_inr_per_bp)}</td></tr>
                  <tr><td>Portfolio Value</td><td>{fmtInr(data.portfolio_value_inr)}</td></tr>
                </tbody>
              </table>
            </Panel>
            <Panel title="Risk Limit Utilization">
              <table className="data-table">
                <thead><tr><th>Limit</th><th>Used</th><th>Limit</th><th>Util %</th></tr></thead>
                <tbody>
                  <tr>
                    <td>FX Exposure</td><td>{fmtInr(data.fx_exposure_inr)}</td><td>{fmtInr(data.risk_limits.fx_exposure_limit_inr)}</td>
                    <td className={data.risk_limits.fx_exposure_utilization_pct > 90 ? "down" : "neutral"}>{data.risk_limits.fx_exposure_utilization_pct}%</td>
                  </tr>
                  <tr>
                    <td>Bond DV01</td><td>{fmtInr(data.bond_dv01_inr_per_bp)}</td><td>{fmtInr(data.risk_limits.bond_dv01_limit_inr)}</td>
                    <td className={data.risk_limits.bond_dv01_utilization_pct > 90 ? "down" : "neutral"}>{data.risk_limits.bond_dv01_utilization_pct}%</td>
                  </tr>
                </tbody>
              </table>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
