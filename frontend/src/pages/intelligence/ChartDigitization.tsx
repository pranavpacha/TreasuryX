import { useEffect, useState } from "react";
import { Badge, Metric, Panel } from "../../components/Common";
import { SingleUploadLab } from "../../components/CvLabShared";
import { ProposalReview } from "../../components/ProposalReview";
import type { DigitizeResult, ProposalItem } from "../../services/visionApi";
import { digitizeChart, sampleImageUrl, urlToFile } from "../../services/visionApi";

function downloadText(filename: string, text: string, mime: string) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ChartDigitization() {
  const [sampleLoading, setSampleLoading] = useState<string | null>(null);
  const [autoFile, setAutoFile] = useState<File | null>(null);

  const loadSample = async (kind: string) => {
    setSampleLoading(kind);
    try {
      const f = await urlToFile(sampleImageUrl(kind, { template: 26, variant: 1, scale: 2 }), `${kind}.png`);
      setAutoFile(f);
    } finally {
      setSampleLoading(null);
    }
  };

  return (
    <div>
      <Panel title="Chart Digitization">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Upload a yield-curve or FX line-chart screenshot to reconstruct its underlying numeric series.
          Classical computer vision only (no trained model): axis/grid detection, hue-based curve
          segmentation, OCR tick-label calibration, and least-squares pixel-to-value mapping. Values are{" "}
          <strong>approximate reconstructions from pixels</strong> — every result states its
          uncertainty and limitations, and nothing is applied to Treasury without your approval below.
        </p>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button onClick={() => loadSample("yield_curve")} disabled={!!sampleLoading}>{sampleLoading === "yield_curve" ? "Loading…" : "Try a sample yield curve"}</button>
          <button onClick={() => loadSample("fx_line_chart")} disabled={!!sampleLoading}>{sampleLoading === "fx_line_chart" ? "Loading…" : "Try a sample FX chart"}</button>
        </div>
      </Panel>

      {autoFile ? (
        <AutoRun key={autoFile.name + autoFile.lastModified} file={autoFile} />
      ) : (
        <SingleUploadLab<DigitizeResult> title="Upload Chart" description="PNG/JPEG screenshot of a line chart. The plot area, axes and curve are detected automatically." run={(f) => digitizeChart(f)}>
          {(result) => result && <DigitizeView result={result} />}
        </SingleUploadLab>
      )}
    </div>
  );
}

// Separately mounted runner so a "try a sample" click reuses the exact same upload+render path
// as a manual file pick, instead of a bespoke second code path.
function AutoRun({ file }: { file: File }) {
  const [result, setResult] = useState<DigitizeResult | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    digitizeChart(file).then((r) => { if (!cancelled) setResult(r); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [file]);
  if (loading) return <Panel title="Sample Chart"><div className="loading-state">Processing…</div></Panel>;
  if (!result) return null;
  return <Panel title="Sample Chart Result"><DigitizeView result={result} /></Panel>;
}

function DigitizeView({ result }: { result: DigitizeResult }) {
  const main = result.series[0];
  const candidates: ProposalItem[] = main
    ? main.points
        .filter((p) => p.y_value !== undefined && (p.tenor || p.x_label))
        .map((p) => ({
          target: "bond_yield" as const,
          instrument_id: (p.tenor ?? p.x_label) as string,
          value: Math.round((p.y_value as number) * 1000) / 1000,
          confidence: result.confidence,
          uncertainty: p.y_uncertainty,
        }))
    : [];

  return (
    <>
      <div className="grid grid-4" style={{ marginBottom: 12 }}>
        <Metric label="Chart Kind" value={result.chart_kind} />
        <Metric label="Axes Detected" value={result.axes_found ? "Yes" : "No"} />
        <Metric label="Extraction Confidence" value={result.confidence !== undefined ? `${(result.confidence * 100).toFixed(0)}%` : "—"} />
        <Metric label="Theme" value={result.theme} />
      </div>
      {result.error && <div className="error-state">{result.error}</div>}
      {result.overlay && (
        <div className="grid grid-2" style={{ marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Detected points (magenta = extracted, yellow = tick calibration)</div>
            <img src={result.overlay} alt="overlay" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
          </div>
          <div>
            <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Reconstructed series</div>
            {main && (
              <table className="data-table">
                <thead><tr><th>Label</th><th>Value</th><th>± Uncertainty</th></tr></thead>
                <tbody>
                  {main.points.filter((p) => p.y_value !== undefined).slice(0, 15).map((p, i) => (
                    <tr key={i}><td style={{ textAlign: "left" }}>{p.tenor ?? p.x_label ?? i}</td><td>{p.y_value?.toFixed(4)}</td><td>{p.y_uncertainty?.toFixed(4) ?? "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
            {main && main.n_points > 15 && <p style={{ fontSize: 10.5, color: "var(--text-lo)" }}>+{main.n_points - 15} more points (see CSV export).</p>}
          </div>
        </div>
      )}
      {result.limitations.length > 0 && (
        <div className="disclaimer-bar">
          {result.limitations.map((l, i) => <div key={i}>⚠ {l}</div>)}
        </div>
      )}
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={() => downloadText(`${result.filename || "chart"}.json`, JSON.stringify(result, null, 2), "application/json")}>Export JSON</button>
        <button onClick={() => downloadText(`${result.filename || "chart"}.csv`, result.csv, "text/csv")}>Export CSV</button>
        {!result.ocr_available && <Badge kind="warn">OCR UNAVAILABLE — calibration disabled</Badge>}
      </div>
      {candidates.length > 0 && <ProposalReview source="chart_digitization" candidates={candidates} sourceRef={result.filename} />}
    </>
  );
}
