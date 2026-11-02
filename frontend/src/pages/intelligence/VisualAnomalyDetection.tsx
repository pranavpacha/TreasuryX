import { useState } from "react";
import { Badge, Metric, Panel } from "../../components/Common";
import { SingleUploadLab } from "../../components/CvLabShared";
import type { AnomalyResult } from "../../services/visionApi";
import { analyzeAnomaly, anomalySample } from "../../services/visionApi";

const SEVERITY_TONE = (s: number): "up" | "down" | "neutral" => (s > 0.6 ? "down" : s > 0.3 ? "neutral" : "up");

function AnomalyView({ result }: { result: AnomalyResult }) {
  return (
    <>
      <div className="disclaimer-bar">⚠ {result.disclaimer}</div>
      <div className="grid grid-4" style={{ marginBottom: 12 }}>
        <Metric label="Anomalies Found" value={String(result.n_anomalies)} tone={result.n_anomalies > 0 ? "down" : "up"} />
        <Metric label="Chart Kind" value={result.chart_kind ?? "unknown"} />
        <Metric label="Digitization Confidence" value={result.digitization_confidence !== null ? `${(result.digitization_confidence * 100).toFixed(0)}%` : "—"} />
        <Metric label="Review Required" value={result.review_required ? "Yes" : "No"} tone={result.review_required ? "down" : "up"} />
      </div>
      {result.ground_truth && (
        <Panel title="Ground Truth (synthetic sample)"><p style={{ fontSize: 11 }}>{result.ground_truth.note} Injected: <code>{JSON.stringify(result.ground_truth.injected)}</code></p></Panel>
      )}
      <img src={result.overlay} alt="anomaly overlay" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000", marginBottom: 12 }} />
      {result.anomalies.length > 0 && (
        <Panel title="Findings">
          <table className="data-table">
            <thead><tr><th>Kind</th><th>Severity</th><th>Description</th></tr></thead>
            <tbody>
              {result.anomalies.map((a, i) => (
                <tr key={i}><td style={{ textAlign: "left" }}><Badge kind="warn">{a.kind.toUpperCase()}</Badge></td><td className={SEVERITY_TONE(a.severity)}>{(a.severity * 100).toFixed(0)}%</td><td style={{ textAlign: "left" }}>{a.description}</td></tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
      {result.method_notes.length > 0 && <div className="disclaimer-bar">{result.method_notes.map((n, i) => <div key={i}>{n}</div>)}</div>}
      <Panel title="Detectors used">
        <ul style={{ fontSize: 11, color: "var(--text-mid)", margin: 0, paddingLeft: 18 }}>
          {Object.entries(result.detectors).map(([k, v]) => <li key={k}><strong>{k}</strong>: {v}</li>)}
        </ul>
      </Panel>
    </>
  );
}

export default function VisualAnomalyDetection() {
  const [sample, setSample] = useState<AnomalyResult | null>(null);
  const [sampleLoading, setSampleLoading] = useState<string | null>(null);

  const loadSample = async (kind: "gap" | "spike" | "jump") => {
    setSampleLoading(kind);
    try {
      setSample(await anomalySample("fx_line_chart", kind));
    } finally {
      setSampleLoading(null);
    }
  };

  return (
    <div>
      <Panel title="Visual Anomaly Detection">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Finds unusual <strong>visual structure</strong> in a chart screenshot — gaps in the plotted
          line, spikes that revert, level shifts that don't, and implausible or unreadable OCR values.
          These are properties of the <strong>image</strong>, not confirmed financial events: a real
          market move, a rendering glitch and a plotting bug can all look identical here, so every
          finding is for analyst review, never acted on automatically.
        </p>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button onClick={() => loadSample("gap")} disabled={!!sampleLoading}>{sampleLoading === "gap" ? "Loading…" : "Sample: missing segment"}</button>
          <button onClick={() => loadSample("spike")} disabled={!!sampleLoading}>{sampleLoading === "spike" ? "Loading…" : "Sample: spike"}</button>
          <button onClick={() => loadSample("jump")} disabled={!!sampleLoading}>{sampleLoading === "jump" ? "Loading…" : "Sample: level shift"}</button>
        </div>
      </Panel>
      {sample ? <AnomalyView result={sample} /> : (
        <SingleUploadLab<AnomalyResult> title="Upload Chart" description="A chart screenshot (yield curve or FX line chart works best)." run={analyzeAnomaly}>
          {(result) => result && <AnomalyView result={result} />}
        </SingleUploadLab>
      )}
    </div>
  );
}
