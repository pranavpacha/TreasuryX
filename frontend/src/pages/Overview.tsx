import { Badge, ErrorState, LoadingState, Metric, Panel, fmtInr, toneFor } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchOverview } from "../services/api";

export default function Overview() {
  const { data, loading, error } = useApi(fetchOverview);

  if (loading) return <LoadingState label="Loading Treasury overview…" />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  return (
    <div>
      <div className="disclaimer-bar">{data.disclaimer}</div>

      <div className="grid grid-4">
        <Panel title="Portfolio P&L">
          <Metric
            label={`Total P&L (as of ${data.as_of})`}
            value={fmtInr(data.risk.total_pnl_inr)}
            tone={toneFor(data.risk.total_pnl_inr)}
            sub="Mark-to-market, open FX + bond positions"
          />
        </Panel>
        <Panel title="1-Day Historical VaR (95%)">
          {data.risk.var ? (
            <Metric
              label="Value at Risk"
              value={fmtInr(data.risk.var.var_amount_inr)}
              sub={`${data.risk.var.confidence * 100}% confidence, ${data.risk.var.horizon_days}d, ${data.risk.var.lookback_obs} obs, historical`}
            />
          ) : (
            <div className="empty-state">{data.risk.var_warning}</div>
          )}
        </Panel>
        <Panel title="Bond DV01">
          <Metric
            label="Portfolio DV01"
            value={fmtInr(data.risk.bond_dv01_inr_per_bp)}
            unit="/ 1bp"
            sub="Price impact of a 1 basis point parallel yield move"
          />
        </Panel>
        <Panel title="Market Regime">
          <Metric label="Decision-support signal" value={data.risk.regime} tone="neutral" sub={data.risk.regime_reasons[0]} />
        </Panel>
      </div>

      <div className="grid grid-2">
        <Panel title="FX Snapshot (DEMO)">
          <table className="data-table">
            <thead><tr><th>Pair</th><th>Rate</th></tr></thead>
            <tbody>
              {data.fx_snapshot.map((q) => (
                <tr key={q.pair}><td>{q.pair}</td><td>{q.rate.toFixed(4)}</td></tr>
              ))}
            </tbody>
          </table>
        </Panel>
        <Panel title="Yield Curve Snapshot (DEMO)">
          <table className="data-table">
            <thead><tr><th>Tenor</th><th>Yield %</th></tr></thead>
            <tbody>
              {data.curve_snapshot.map((p) => (
                <tr key={p.tenor}><td>{p.tenor}</td><td>{p.yield_pct.toFixed(3)}</td></tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>

      <div className="grid grid-2">
        <Panel title="Risk Limit Utilization">
          <table className="data-table">
            <tbody>
              <tr><td>FX Exposure</td><td>{fmtInr(data.risk.fx_exposure_inr)} / {fmtInr(data.risk.risk_limits.fx_exposure_limit_inr)}</td><td>{data.risk.risk_limits.fx_exposure_utilization_pct}%</td></tr>
              <tr><td>Bond DV01</td><td>{fmtInr(data.risk.bond_dv01_inr_per_bp)} / {fmtInr(data.risk.risk_limits.bond_dv01_limit_inr)}</td><td>{data.risk.risk_limits.bond_dv01_utilization_pct}%</td></tr>
            </tbody>
          </table>
        </Panel>
        <Panel title="Latest Market Intelligence">
          {data.market_events.map((e, i) => (
            <div key={i} style={{ padding: "6px 0", borderBottom: i < data.market_events.length - 1 ? "1px solid var(--bg-2)" : "none" }}>
              <Badge kind={e.severity === "WARNING" ? "warn" : "info"}>{e.category}</Badge>{" "}
              <span style={{ fontSize: 12 }}>{e.headline}</span>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  );
}
