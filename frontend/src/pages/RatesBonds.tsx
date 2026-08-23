import { useState } from "react";
import { SeriesLineChart } from "../charts/SeriesLineChart";
import { Badge, ErrorState, LoadingState, Panel, Tooltip, fmtInr, fmtNumber, toneFor } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchBondHistory, fetchBondPositions, fetchBonds, postBondTrade } from "../services/api";

export default function RatesBonds() {
  const bonds = useApi(fetchBonds);
  const positions = useApi(fetchBondPositions);
  const [selected, setSelected] = useState<string | null>(null);
  const history = useApi(() => (selected ? fetchBondHistory(selected, 250) : Promise.resolve([])), [selected]);

  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState("10000000");
  const [msg, setMsg] = useState<string | null>(null);

  const selectedBond = bonds.data?.find((b) => b.isin === selected);

  const submitTrade = async () => {
    if (!selected || !selectedBond) return;
    try {
      const t = await postBondTrade({ instrument_id: selected, side, quantity: Number(qty), price: selectedBond.clean_price });
      setMsg(`SIMULATED trade booked: ${t.side} face ${fmtNumber(t.quantity, 0)} of ${selected} @ ${t.price}`);
      positions.reload();
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  return (
    <div>
      <Panel title="Government Bonds (G-Secs, DEMO)">
        {bonds.loading && <LoadingState />}
        {bonds.error && <ErrorState message={bonds.error} />}
        {bonds.data && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ISIN</th><th>Name</th><th>Coupon %</th><th>Maturity</th><th>Yrs to Mat.</th>
                <th>Yield %</th><th>Clean Price</th>
                <th>Mod. Duration <Tooltip text="Modified duration (years): approx % price change per 1 unit change in yield, computed via bump-and-reprice against the pricing model" /></th>
                <th>Convexity</th>
                <th>DV01 / 100 face <Tooltip text="Price impact of a 1 basis point yield move, per 100 face value" /></th>
              </tr>
            </thead>
            <tbody>
              {bonds.data.map((b) => (
                <tr key={b.isin} onClick={() => setSelected(b.isin)} style={{ cursor: "pointer", fontWeight: b.isin === selected ? 700 : 400 }}>
                  <td>{b.isin}</td><td style={{ textAlign: "left" }}>{b.name}</td>
                  <td>{b.coupon_rate_pct.toFixed(2)}</td><td>{b.maturity_date}</td><td>{b.years_to_maturity.toFixed(2)}</td>
                  <td>{b.current_yield_pct.toFixed(3)}</td><td>{b.clean_price.toFixed(3)}</td>
                  <td>{b.modified_duration.toFixed(3)}</td><td>{b.convexity.toFixed(2)}</td><td>{b.dv01_per_100_face.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {selected && (
        <div className="grid grid-2">
          <Panel title={`${selected} — Yield & Price History (DEMO)`}>
            {history.loading && <LoadingState />}
            {history.data && history.data.length > 0 && <SeriesLineChart data={history.data} xKey="date" yKey="yield_pct" color="var(--warn)" />}
          </Panel>
          <Panel title="Simulate Bond Trade">
            <div className="field"><label>ISIN</label><input value={selected} disabled /></div>
            <div className="field">
              <label>Side</label>
              <select value={side} onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}>
                <option value="BUY">BUY</option><option value="SELL">SELL</option>
              </select>
            </div>
            <div className="field"><label>Face value quantity (INR)</label><input value={qty} onChange={(e) => setQty(e.target.value)} /></div>
            <div className="field"><label>Execution clean price</label><input value={selectedBond?.clean_price.toFixed(3) ?? ""} disabled /></div>
            <button className="primary" onClick={submitTrade}>Book Simulated Trade</button>
            <div style={{ marginTop: 8 }}><Badge kind="sim">SIMULATED — no real execution venue is contacted</Badge></div>
            {msg && <div style={{ marginTop: 8, fontSize: 12 }}>{msg}</div>}
          </Panel>
        </div>
      )}

      <Panel title="Open Bond Positions & MTM">
        {positions.loading && <LoadingState />}
        {positions.data && positions.data.length === 0 && <div className="empty-state">No open bond positions.</div>}
        {positions.data && positions.data.length > 0 && (
          <table className="data-table">
            <thead><tr><th>ISIN</th><th>Face Qty</th><th>Clean Price</th><th>Yield %</th><th>Mod. Duration</th><th>DV01 (INR)</th><th>Market Value</th></tr></thead>
            <tbody>
              {positions.data.map((p) => (
                <tr key={p.isin}>
                  <td>{p.isin}</td><td>{fmtNumber(p.quantity_face, 0)}</td><td>{p.clean_price.toFixed(3)}</td>
                  <td>{p.current_yield_pct.toFixed(3)}</td><td>{p.modified_duration.toFixed(3)}</td>
                  <td className={toneFor(p.dv01_inr)}>{fmtInr(p.dv01_inr)}</td><td>{fmtInr(p.market_value_inr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
