import { Metric, Panel } from "../../components/Common";
import { SingleUploadLab } from "../../components/CvLabShared";
import type { QualityResult } from "../../services/visionApi";
import { analyzeQuality } from "../../services/visionApi";

const STATUS_TONE: Record<string, "up" | "down" | "neutral"> = { ok: "up", warn: "neutral", poor: "down", unknown: "neutral" };
const VERDICT_TONE: Record<string, "up" | "down" | "neutral"> = { good: "up", fair: "neutral", poor: "down" };

export default function ImageQualityAnalyzer() {
  return (
    <div>
      <Panel title="Image Quality Analyzer">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Before extraction spends time on a screenshot that was never going to OCR well, this measures
          blur (Laplacian variance), noise (Immerkaer estimator), contrast, skew, 90° rotation, JPEG
          blocking and uneven illumination directly from the pixels, and recommends — then applies —
          suitable preprocessing. Enhancement is re-measured, never assumed to have worked.
        </p>
      </Panel>
      <SingleUploadLab<QualityResult> title="Upload Screenshot" description="Any financial chart, table or report screenshot." run={analyzeQuality}>
        {(result) => result && (
          <>
            <div className="grid grid-4" style={{ marginBottom: 12 }}>
              <Metric label="Quality Score" value={`${result.before.quality_score}/100`} />
              <Metric label="Verdict" value={result.before.verdict.toUpperCase()} tone={VERDICT_TONE[result.before.verdict]} />
              <Metric label="Resolution" value={`${result.before.measurements.width}×${result.before.measurements.height}`} />
              <Metric label="Operations Applied" value={String(result.applied_operations.length)} />
            </div>
            <Panel title="Per-check Results">
              <table className="data-table">
                <thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead>
                <tbody>
                  {result.before.checks.map((c, i) => (
                    <tr key={i}><td style={{ textAlign: "left" }}>{c.check}</td><td className={STATUS_TONE[c.status]}>{c.status.toUpperCase()}</td><td style={{ textAlign: "left" }}>{c.detail}</td></tr>
                  ))}
                </tbody>
              </table>
            </Panel>
            {result.before.recommendations.length > 0 && (
              <Panel title="Recommended Preprocessing (applied below)">
                <ul style={{ fontSize: 11, color: "var(--text-mid)", margin: 0, paddingLeft: 18 }}>
                  {result.before.recommendations.map((r, i) => <li key={i}><strong>{r.op}</strong> — {r.why}</li>)}
                </ul>
              </Panel>
            )}
            <div className="grid grid-2" style={{ marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Before</div>
                <img src={result.images.before} alt="before" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
              </div>
              <div>
                <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>After{result.applied_operations.length === 0 ? " (no change needed)" : ""}</div>
                <img src={result.images.after} alt="after" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
              </div>
            </div>
            {result.applied_operations.length > 0 && (
              <Panel title="Before / After Measurements">
                <table className="data-table">
                  <thead><tr><th>Metric</th><th>Before</th><th>After</th></tr></thead>
                  <tbody>
                    {result.comparison.map((c, i) => <tr key={i}><td style={{ textAlign: "left" }}>{c.metric}</td><td>{String(c.before)}</td><td>{String(c.after)}</td></tr>)}
                  </tbody>
                </table>
              </Panel>
            )}
            <div className="disclaimer-bar">⚠ {result.caveat}</div>
          </>
        )}
      </SingleUploadLab>
    </div>
  );
}
