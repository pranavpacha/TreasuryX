import { useMemo, useState } from "react";
import { ErrorState, LoadingState, Panel } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchFxVolSurface, fetchStressSurface, fetchYieldSurface } from "../services/api";
import { GraphicsInfoPanel } from "../three/GraphicsInfoPanel";
import { SurfacePlot } from "../three/SurfacePlot";

const TENOR_ORDER = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"];

function YieldSurfaceTab() {
  const { data, loading, error } = useApi(() => fetchYieldSurface(24));
  const grid = useMemo(() => {
    if (!data) return null;
    const dates = data.dates;
    const tenors = TENOR_ORDER.filter((t) => data.points.some((p) => p.tenor === t));
    const values = dates.map((d) => tenors.map((t) => data.points.find((p) => p.date === d && p.tenor === t)?.yield_pct ?? 0));
    return { dates, tenors, values };
  }, [data]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!grid) return null;
  return (
    <SurfacePlot
      xLabels={grid.tenors} yLabels={grid.dates} values={grid.values}
      xAxisName="Maturity (tenor)" yAxisName="Yield (%)" zAxisName="Observation date"
      formatValue={(v) => `${v.toFixed(3)}%`} colorMode="sequential"
    />
  );
}

function FxVolSurfaceTab() {
  const { data, loading, error } = useApi(fetchFxVolSurface);
  const grid = useMemo(() => {
    if (!data) return null;
    const windows = data.windows.map(String);
    const values = data.pairs.map((pair) => data.windows.map((w) => data.points.find((p) => p.pair === pair && p.window_days === w)?.annualized_vol_pct ?? 0));
    return { windows, pairs: data.pairs, values };
  }, [data]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!grid) return null;
  return (
    <SurfacePlot
      xLabels={grid.windows.map((w) => `${w}d`)} yLabels={grid.pairs} values={grid.values}
      xAxisName="Lookback window (days)" yAxisName="Annualized volatility (%)" zAxisName="FX pair"
      formatValue={(v) => `${v.toFixed(2)}%`} colorMode="sequential"
    />
  );
}

function StressSurfaceTab() {
  const { data, loading, error } = useApi(() => fetchStressSurface(9, 9));
  const grid = useMemo(() => {
    if (!data) return null;
    const fxShocks = Array.from(new Set(data.grid.map((g) => g.fx_shock_pct))).sort((a, b) => a - b);
    const yieldShocks = Array.from(new Set(data.grid.map((g) => g.yield_shock_bps))).sort((a, b) => a - b);
    const values = yieldShocks.map((y) => fxShocks.map((f) => data.grid.find((g) => g.fx_shock_pct === f && g.yield_shock_bps === y)?.total_pnl_inr ?? 0));
    return { fxShocks, yieldShocks, values, hasPositions: data.has_positions };
  }, [data]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!grid) return null;
  if (!grid.hasPositions) return <div className="empty-state">No open positions — book a simulated FX or bond trade to see the P&L stress surface.</div>;
  return (
    <SurfacePlot
      xLabels={grid.fxShocks.map((f) => `${f > 0 ? "+" : ""}${f}%`)}
      yLabels={grid.yieldShocks.map((y) => `${y > 0 ? "+" : ""}${y}bp`)}
      values={grid.values}
      xAxisName="USD/INR shock (%)" yAxisName="Total P&L (INR)" zAxisName="Parallel yield shock (bps)"
      formatValue={(v) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`}
      colorMode="diverging"
    />
  );
}

const TABS = [
  { key: "yield", label: "Yield Curve Surface", render: YieldSurfaceTab },
  { key: "vol", label: "FX Volatility Surface", render: FxVolSurfaceTab },
  { key: "stress", label: "Portfolio Stress Surface", render: StressSurfaceTab },
] as const;

export default function Market3D() {
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("yield");
  const Active = TABS.find((t) => t.key === tab)!.render;

  return (
    <div>
      <Panel title="3D Market Visualization" right={
        <div style={{ display: "flex", gap: 6 }}>
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{ fontWeight: tab === t.key ? 700 : 400, borderColor: tab === t.key ? "var(--accent)" : undefined }}>
              {t.label}
            </button>
          ))}
        </div>
      }>
        <Active />
      </Panel>
      <GraphicsInfoPanel />
    </div>
  );
}
