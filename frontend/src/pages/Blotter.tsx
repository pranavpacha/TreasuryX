import { Badge, ErrorState, LoadingState, Panel, fmtInr } from "../components/Common";
import { useApi } from "../hooks/useApi";
import { fetchTradeBlotter } from "../services/api";

export default function Blotter() {
  const { data, loading, error } = useApi(fetchTradeBlotter);

  return (
    <Panel title="Trade Blotter">
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && data.length === 0 && <div className="empty-state">No trades booked yet.</div>}
      {data && data.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th><th>Instrument</th><th>Side</th><th>Quantity</th><th>Price</th>
              <th>Notional</th><th>Type</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <tr key={t.id}>
                <td>{new Date(t.created_at).toLocaleString()}</td>
                <td>{t.instrument_id}</td>
                <td className={t.side === "BUY" ? "up" : "down"}>{t.side}</td>
                <td>{t.quantity.toLocaleString()}</td>
                <td>{t.price.toFixed(4)}</td>
                <td>{fmtInr(t.notional)}</td>
                <td>{t.trade_type}</td>
                <td><Badge kind="sim">{t.status}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
