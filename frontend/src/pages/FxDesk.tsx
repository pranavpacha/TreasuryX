import { useState } from "react";
import { SeriesLineChart } from "../charts/SeriesLineChart";
import { Badge, ErrorState, LoadingState, Panel, Tooltip, fmtInr, fmtNumber, toneFor } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchFxHistory, fetchFxPositions, fetchFxQuotes, postFxTrade } from "../services/api";

const PAIRS = ["USDINR", "EURINR", "GBPINR", "EURUSD"];

export default function FxDesk() {
  const [selectedPair, setSelectedPair] = useState("USDINR");
  const quotes = useApi(fetchFxQuotes);
  const history = useApi(() => fetchFxHistory(selectedPair, 180), [selectedPair]);
  const positions = useApi(fetchFxPositions);

  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState("1000000");
  const [tradeMsg, setTradeMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const currentRate = quotes.data?.find((q) => q.pair === selectedPair)?.rate ?? 0;

  const submitTrade = async () => {
    setSubmitting(true);
    setTradeMsg(null);
    try {
      const trade = await postFxTrade({ instrument_id: selectedPair, side, quantity: Number(qty), price: currentRate });
      setTradeMsg(`SIMULATED trade booked: ${trade.side} ${fmtNumber(trade.quantity, 0)} ${selectedPair} @ ${trade.price}`);
      positions.reload();
    } catch (e) {
      setTradeMsg((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <Panel title="FX Quotes (DEMO)">
        {quotes.loading && <LoadingState />}
        {quotes.error && <ErrorState message={quotes.error} />}
        {quotes.data && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Pair</th><th>Rate</th><th>Bid</th><th>Ask</th><th>Spread</th>
                <th>1D Return</th><th>Ann. Vol (60d) <Tooltip text="Historical volatility: std dev of daily log returns, annualized with sqrt(252)" /></th>
              </tr>
            </thead>
            <tbody>
              {quotes.data.map((q) => (
                <tr key={q.pair} onClick={() => setSelectedPair(q.pair)} style={{ cursor: "pointer", fontWeight: q.pair === selectedPair ? 700 : 400 }}>
                  <td>{q.pair}</td>
                  <td>{q.rate.toFixed(4)}</td>
                  <td>{q.bid.toFixed(4)}</td>
                  <td>{q.ask.toFixed(4)}</td>
                  <td>{q.spread.toFixed(4)}</td>
                  <td className={toneFor(q.day_return_pct)}>{(q.day_return_pct * 100).toFixed(3)}%</td>
                  <td>{(q.annualized_vol_pct * 100).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <div className="grid grid-2">
        <Panel title={`${selectedPair} — 180D History (DEMO)`}>
          {history.loading && <LoadingState />}
          {history.data && <SeriesLineChart data={history.data} xKey="date" yKey="rate" />}
        </Panel>

        <Panel title="Simulate FX Trade">
          <div className="field">
            <label>Pair</label>
            <select value={selectedPair} onChange={(e) => setSelectedPair(e.target.value)}>
              {PAIRS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Side</label>
            <select value={side} onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}>
              <option value="BUY">BUY (long base ccy)</option>
              <option value="SELL">SELL (short base ccy)</option>
            </select>
          </div>
          <div className="field">
            <label>Notional (base currency units)</label>
            <input value={qty} onChange={(e) => setQty(e.target.value)} />
          </div>
          <div className="field">
            <label>Execution rate (current demo spot)</label>
            <input value={currentRate.toFixed(4)} disabled />
          </div>
          <button className="primary" disabled={submitting} onClick={submitTrade}>Book Simulated Trade</button>
          <div style={{ marginTop: 8 }}><Badge kind="sim">SIMULATED — no real execution venue is contacted</Badge></div>
          {tradeMsg && <div style={{ marginTop: 8, fontSize: 12 }}>{tradeMsg}</div>}
        </Panel>
      </div>

      <Panel title="Open FX Positions & MTM P&L">
        {positions.loading && <LoadingState />}
        {positions.data && positions.data.length === 0 && <div className="empty-state">No open FX positions.</div>}
        {positions.data && positions.data.length > 0 && (
          <table className="data-table">
            <thead><tr><th>Pair</th><th>Notional (base)</th><th>Entry Rate</th><th>Current Rate</th><th>Return</th><th>MTM P&L (INR)</th></tr></thead>
            <tbody>
              {positions.data.map((p) => (
                <tr key={p.pair}>
                  <td>{p.pair}</td>
                  <td>{fmtNumber(p.notional_base, 0)}</td>
                  <td>{p.entry_rate.toFixed(4)}</td>
                  <td>{p.current_rate.toFixed(4)}</td>
                  <td className={toneFor(p.return_pct)}>{(p.return_pct * 100).toFixed(3)}%</td>
                  <td className={toneFor(p.pnl_inr)}>{fmtInr(p.pnl_inr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
