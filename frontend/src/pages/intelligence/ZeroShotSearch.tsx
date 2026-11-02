import { useEffect, useState } from "react";
import { Badge, ErrorState, LoadingState, Panel } from "../../components/Common";
import type { ClipStatus, ZeroShotResult } from "../../services/visionApi";
import { fetchClipStatus, zeroShotSearch } from "../../services/visionApi";

const EXAMPLES = ["a government securities yield curve", "a USD/INR exchange-rate chart", "a bond valuation table", "a portfolio risk report", "a candlestick price chart"];

export default function ZeroShotSearch() {
  const [clip, setClip] = useState<ClipStatus | null>(null);
  const [query, setQuery] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<ZeroShotResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { fetchClipStatus().then(setClip); }, []);

  const run = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setQuery(q);
    try {
      setResult(await zeroShotSearch(q, files, true));
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Panel title="Zero-Shot Financial Image Search">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Describe what you're looking for in plain English; the search ranks a gallery of synthetic
          reference screenshots (plus anything you upload) by match to your description. Uses a real
          CLIP model when available ({clip?.available ? "available in this environment" : "not available here — see status below"}),
          with a transparent keyword-heuristic fallback otherwise — the response always says which ran.
        </p>
        {clip && !clip.available && <div className="disclaimer-bar">⚠ CLIP unavailable: {clip.reason}. {clip.how_to_enable}</div>}
      </Panel>
      <Panel title="Search">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          {EXAMPLES.map((ex) => <button key={ex} onClick={() => run(ex)} disabled={loading}>{ex}</button>)}
        </div>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input style={{ flex: 1 }} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. a chart showing a steepening yield curve" onKeyDown={(e) => e.key === "Enter" && run(query)} />
          <button className="primary" onClick={() => run(query)} disabled={loading}>Search</button>
        </div>
        <div style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
          Optionally add your own candidate images: <input type="file" accept=".png,.jpg,.jpeg,.webp" multiple onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
        </div>
        {loading && <LoadingState label="Searching…" />}
        {error && <ErrorState message={error} />}
      </Panel>
      {result && (
        <>
          <Panel title={`Results — ${result.backend === "clip" ? "CLIP" : "Fallback keyword heuristic"}`}>
            <Badge kind={result.clip_ran ? "info" : "warn"}>{result.clip_ran ? "CLIP RAN" : "CLIP DID NOT RUN"}</Badge>
            <p style={{ fontSize: 11, color: "var(--text-mid)", marginTop: 6 }}>{result.score_meaning}</p>
          </Panel>
          <div className="grid grid-4">
            {result.results.slice(0, 16).map((r) => (
              <div key={r.name}>
                <img src={r.thumbnail} alt={r.name} style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3 }} />
                <div style={{ fontSize: 10.5, marginTop: 3 }}>#{r.rank} · {r.score.toFixed(3)}</div>
                <div style={{ fontSize: 9.5, color: "var(--text-mid)" }}>{r.synthetic_reference ? r.name.split(":")[1] : r.name}</div>
              </div>
            ))}
          </div>
          <div className="disclaimer-bar">{result.limitations.map((l, i) => <div key={i}>⚠ {l}</div>)}</div>
        </>
      )}
    </div>
  );
}
