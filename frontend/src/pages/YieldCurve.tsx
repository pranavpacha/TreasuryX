import { useEffect, useState } from "react";
import { MultiCurveChart } from "../charts/MultiCurveChart";
import { Badge, ErrorState, LoadingState, Panel } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchYieldCurve, fetchYieldCurveCompare, fetchYieldCurveDates } from "../services/api";

export default function YieldCurve() {
  const dates = useApi(fetchYieldCurveDates);
  const [date1, setDate1] = useState<string>("");
  const [date2, setDate2] = useState<string>("");

  useEffect(() => {
    if (dates.data && dates.data.length > 0) {
      setDate1(dates.data[Math.max(0, dates.data.length - 21)]);
      setDate2(dates.data[dates.data.length - 1]);
    }
  }, [dates.data]);

  const curve1 = useApi(() => (date1 ? fetchYieldCurve(date1) : Promise.resolve([])), [date1]);
  const compare = useApi(() => (date1 && date2 ? fetchYieldCurveCompare(date1, date2) : Promise.resolve(null)), [date1, date2]);

  const chartData = curve1.data?.map((p) => {
    const c2 = compare.data?.points.find((x: { tenor: string }) => x.tenor === p.tenor);
    return { tenor: p.tenor, [date1]: p.yield_pct, [date2]: c2?.date2_pct };
  }) ?? [];

  return (
    <div>
      <Panel title="Yield Curve — Date Selection & Comparison" right={
        dates.data ? (
          <div style={{ display: "flex", gap: 8 }}>
            <select value={date1} onChange={(e) => setDate1(e.target.value)}>{dates.data.map((d) => <option key={d} value={d}>{d}</option>)}</select>
            <span style={{ color: "var(--text-mid)" }}>vs</span>
            <select value={date2} onChange={(e) => setDate2(e.target.value)}>{dates.data.map((d) => <option key={d} value={d}>{d}</option>)}</select>
          </div>
        ) : null
      }>
        {(curve1.loading || dates.loading) && <LoadingState />}
        {curve1.error && <ErrorState message={curve1.error} />}
        {chartData.length > 0 && (
          <MultiCurveChart
            data={chartData}
            xKey="tenor"
            series={[
              { key: date1, color: "var(--text-mid)", label: date1 },
              { key: date2, color: "var(--accent)", label: date2 },
            ]}
          />
        )}
      </Panel>

      {compare.data && (
        <div className="grid grid-2">
          <Panel title="Curve Shift Detail (bps)">
            <table className="data-table">
              <thead><tr><th>Tenor</th><th>{date1} %</th><th>{date2} %</th><th>Shift (bps)</th></tr></thead>
              <tbody>
                {compare.data.points.map((p: { tenor: string; date1_pct: number; date2_pct: number; shift_bps: number }) => (
                  <tr key={p.tenor}>
                    <td>{p.tenor}</td><td>{p.date1_pct?.toFixed(3)}</td><td>{p.date2_pct?.toFixed(3)}</td>
                    <td className={p.shift_bps > 0 ? "up" : p.shift_bps < 0 ? "down" : "neutral"}>{p.shift_bps > 0 ? "+" : ""}{p.shift_bps}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          <Panel title="Curve Classification">
            <div style={{ marginBottom: 10 }}>
              <Badge kind={compare.data.classification === "STABLE" ? "info" : "warn"}>{compare.data.classification}</Badge>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
              10Y-2Y slope moved from {compare.data.slope_10y_2y_date1_pct.toFixed(3)}% to {compare.data.slope_10y_2y_date2_pct.toFixed(3)}%
              &nbsp;({compare.data.slope_change_bps > 0 ? "+" : ""}{compare.data.slope_change_bps}bp).
              Classified STEEPENING if slope widens &gt;2bp, FLATTENING if it narrows &gt;2bp, else STABLE.
            </p>
          </Panel>
        </div>
      )}
    </div>
  );
}
