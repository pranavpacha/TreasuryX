import { useMemo, useState } from "react";
import { ErrorState, LoadingState, Panel } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchFxVolSurface, fetchStressSurface, fetchYieldSurface } from "../services/api";
import { Treasury3DControls, useTreasury3DState } from "../three/GraphicsControls";
import { SurfacePlot } from "../three/SurfacePlot";

const TENOR_ORDER = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"];

function YieldSurfaceTab() {
  const { data, loading, error, reload } = useApi(() => fetchYieldSurface(24));
  const state = useTreasury3DState(0.7);
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
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
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <button onClick={reload} title="Re-fetch from the live Treasury engine — pulls in any CV correction, trade, or scenario run since this page loaded">Refresh Data</button>
      </div>
      <Treasury3DControls
        state={state}
        dataMapping={{ source: "GET /api/market3d/yield-surface (live yield-curve history, CV-corrected values included)", xMapping: "maturity tenor", yMapping: "yield (%)", zMapping: "observation date" }}
        onThresholdLabel="High-yield threshold"
      />
      <SurfacePlot
        xLabels={grid.tenors} yLabels={grid.dates} values={grid.values}
        xAxisName="Maturity (tenor)" yAxisName="Yield (%)" zAxisName="Observation date"
        formatValue={(v) => `${v.toFixed(3)}%`} colorMode="sequential"
        renderMode={state.renderMode} projectionMode={state.projectionMode} shaderThreshold={state.threshold}
        rotationXDeg={state.rotationXDeg} rotationYDeg={state.rotationYDeg} rotationZDeg={state.rotationZDeg}
        verticalScale={state.verticalScale} displayMode={state.displayMode} showNormals={state.showNormals}
        viewMode={state.viewMode} onSelectPoint={(r, c) => setSelected({ r, c })}
        onMatrices={state.setMatrices}
      />
      {selected && (
        <div className="panel" style={{ marginTop: 8 }}>
          <div className="panel-title">Selected Point</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left" }}>Tenor</td><td>{grid.tenors[selected.c]}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Observation date</td><td>{grid.dates[selected.r]}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Yield</td><td>{grid.values[selected.r][selected.c].toFixed(3)}%</td></tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FxVolSurfaceTab() {
  const { data, loading, error, reload } = useApi(fetchFxVolSurface);
  const state = useTreasury3DState(0.6);
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
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
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <button onClick={reload} title="Re-fetch from the live Treasury engine — pulls in any CV correction, trade, or scenario run since this page loaded">Refresh Data</button>
      </div>
      <Treasury3DControls
        state={state}
        dataMapping={{ source: "GET /api/market3d/fx-vol-surface (rolling annualized volatility per pair, live demo FX history)", xMapping: "lookback window (days)", yMapping: "annualized volatility (%)", zMapping: "FX pair" }}
        onThresholdLabel="High-volatility threshold"
      />
      <SurfacePlot
        xLabels={grid.windows.map((w) => `${w}d`)} yLabels={grid.pairs} values={grid.values}
        xAxisName="Lookback window (days)" yAxisName="Annualized volatility (%)" zAxisName="FX pair"
        formatValue={(v) => `${v.toFixed(2)}%`} colorMode="sequential"
        renderMode={state.renderMode} projectionMode={state.projectionMode} shaderThreshold={state.threshold}
        rotationXDeg={state.rotationXDeg} rotationYDeg={state.rotationYDeg} rotationZDeg={state.rotationZDeg}
        verticalScale={state.verticalScale} displayMode={state.displayMode} showNormals={state.showNormals}
        viewMode={state.viewMode} onSelectPoint={(r, c) => setSelected({ r, c })}
        onMatrices={state.setMatrices}
      />
      {selected && (
        <div className="panel" style={{ marginTop: 8 }}>
          <div className="panel-title">Selected Point</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left" }}>FX pair</td><td>{grid.pairs[selected.r]}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Lookback window</td><td>{grid.windows[selected.c]}d</td></tr>
              <tr><td style={{ textAlign: "left" }}>Annualized volatility</td><td>{grid.values[selected.r][selected.c].toFixed(2)}%</td></tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StressHeatmap({ grid, selected, onSelect }: {
  grid: { fxShocks: number[]; yieldShocks: number[]; values: number[][] };
  selected: { r: number; c: number } | null;
  onSelect: (r: number, c: number) => void;
}) {
  const flat = grid.values.flat();
  const maxAbs = Math.max(1, ...flat.map((v) => Math.abs(v)));
  return (
    <table className="data-table" style={{ tableLayout: "fixed" }}>
      <thead>
        <tr>
          <th style={{ width: 70 }}>Rate \ FX</th>
          {grid.fxShocks.map((f) => <th key={f}>{f > 0 ? "+" : ""}{f}%</th>)}
        </tr>
      </thead>
      <tbody>
        {grid.yieldShocks.map((y, r) => (
          <tr key={y}>
            <td style={{ textAlign: "left", fontWeight: 700 }}>{y > 0 ? "+" : ""}{y}bp</td>
            {grid.fxShocks.map((f, c) => {
              const v = grid.values[r][c];
              const intensity = Math.abs(v) / maxAbs;
              const isSel = selected?.r === r && selected?.c === c;
              return (
                <td
                  key={f}
                  onClick={() => onSelect(r, c)}
                  title={`FX shock ${f > 0 ? "+" : ""}${f}%, rate shock ${y > 0 ? "+" : ""}${y}bp: ₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`}
                  style={{
                    cursor: "pointer",
                    background: v >= 0 ? `rgba(47,191,113,${0.1 + intensity * 0.6})` : `rgba(229,72,77,${0.1 + intensity * 0.6})`,
                    outline: isSel ? "2px solid var(--accent)" : "none",
                    outlineOffset: -2,
                    fontSize: 10,
                  }}
                >
                  {(v / 1000).toFixed(0)}K
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StressSurfaceTab() {
  const { data, loading, error, reload } = useApi(() => fetchStressSurface(9, 9));
  const state = useTreasury3DState(0.55);
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
  const [view, setView] = useState<"3d" | "heatmap">("3d");
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
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 4 }}>
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 4, overflow: "hidden" }}>
          <button onClick={() => setView("3d")} style={{ border: "none", borderRadius: 0, fontSize: 11, background: view === "3d" ? "var(--accent)" : "var(--bg-2)", color: view === "3d" ? "white" : "var(--text-mid)" }}>3D Surface</button>
          <button onClick={() => setView("heatmap")} style={{ border: "none", borderRadius: 0, fontSize: 11, background: view === "heatmap" ? "var(--accent)" : "var(--bg-2)", color: view === "heatmap" ? "white" : "var(--text-mid)" }}>2D Heatmap</button>
        </div>
        <button onClick={reload} title="Re-fetch from the live Treasury engine — pulls in any CV correction, trade, or scenario run since this page loaded">Refresh Data</button>
      </div>
      {view === "heatmap" ? (
        <>
          <StressHeatmap grid={grid} selected={selected} onSelect={(r, c) => setSelected({ r, c })} />
          <div style={{ fontSize: 10, color: "var(--text-lo)", marginTop: 6 }}>
            Same stress-engine data as the 3D surface — rows are parallel yield shocks, columns are USD/INR shocks, cell color/value is total portfolio P&L. Click a cell, or switch to <button onClick={() => setView("3d")} style={{ fontSize: 10, padding: "1px 4px" }}>3D Surface</button> to see it rendered as a rotatable surface.
          </div>
        </>
      ) : (
        <>
          <Treasury3DControls
            state={state}
            dataMapping={{ source: "GET /api/market3d/stress-surface (real scenario engine, current open positions + any CV-corrected market levels)", xMapping: "USD/INR shock (%)", yMapping: "total portfolio P&L (INR)", zMapping: "parallel yield shock (bps)" }}
            onThresholdLabel="Loss threshold"
          />
          <SurfacePlot
            xLabels={grid.fxShocks.map((f) => `${f > 0 ? "+" : ""}${f}%`)}
            yLabels={grid.yieldShocks.map((y) => `${y > 0 ? "+" : ""}${y}bp`)}
            values={grid.values}
            xAxisName="USD/INR shock (%)" yAxisName="Total P&L (INR)" zAxisName="Parallel yield shock (bps)"
            formatValue={(v) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`}
            colorMode="diverging"
            renderMode={state.renderMode} projectionMode={state.projectionMode} shaderThreshold={state.threshold}
            rotationXDeg={state.rotationXDeg} rotationYDeg={state.rotationYDeg} rotationZDeg={state.rotationZDeg}
            verticalScale={state.verticalScale} displayMode={state.displayMode} showNormals={state.showNormals}
            viewMode={state.viewMode} onSelectPoint={(r, c) => setSelected({ r, c })}
            onMatrices={state.setMatrices}
          />
        </>
      )}
      {selected && (
        <div className="panel" style={{ marginTop: 8 }}>
          <div className="panel-title">Selected Point</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left" }}>FX shock</td><td>{grid.fxShocks[selected.c] > 0 ? "+" : ""}{grid.fxShocks[selected.c]}%</td></tr>
              <tr><td style={{ textAlign: "left" }}>Rate shock</td><td>{grid.yieldShocks[selected.r] > 0 ? "+" : ""}{grid.yieldShocks[selected.r]}bp</td></tr>
              <tr><td style={{ textAlign: "left" }}>Portfolio P&amp;L</td><td>₹{grid.values[selected.r][selected.c].toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td></tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const TABS = [
  { key: "yield", label: "3D Yield Surface", render: YieldSurfaceTab },
  { key: "vol", label: "3D FX Volatility Surface", render: FxVolSurfaceTab },
  { key: "stress", label: "3D Portfolio Stress Surface", render: StressSurfaceTab },
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
        <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 10 }}>
          Interactive 3D rendering of real Treasury data — a genuine WebGL/GLSL pipeline (transformations,
          camera, projection, depth, lighting, shading), not a canned chart library. Switch to <strong>Risk
          View</strong> to see the same data rendered through a hand-written GLSL shader instead of the
          standard material.
        </p>
        <Active />
      </Panel>
    </div>
  );
}
