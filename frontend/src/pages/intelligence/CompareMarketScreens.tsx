import { Badge, Metric, Panel } from "../../components/Common";
import { DualUploadLab, ImageGrid } from "../../components/CvLabShared";
import { ProposalReview } from "../../components/ProposalReview";
import type { CompareResult, ProposalItem } from "../../services/visionApi";
import { compareScreens } from "../../services/visionApi";

const VERDICT_LABEL: Record<string, string> = {
  identical: "Identical", near_identical: "Near-identical", visual_change: "Visual change (no instrument values changed)",
  value_change: "Market value changed", layout_change: "Layout shifted (no value change)", layout_and_value_change: "Layout shifted AND a value changed",
};
const VERDICT_TONE: Record<string, "info" | "warn" | "sim"> = { value_change: "warn", layout_and_value_change: "warn" };

export default function CompareMarketScreens() {
  return (
    <div>
      <Panel title="Compare Market Screens">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Upload two Treasury/market screenshots — e.g. today's and yesterday's rates screen, two
          brokers' quote sheets, or a report before/after revision. The two images are registered with
          SIFT keypoint matching + RANSAC homography, compared with SSIM and pixel differencing, and
          every changed region is OCR'd so a genuine instrument value change can be told apart from a
          layout shift (window resize, scroll, re-rendered theme) — a layout change never gets
          reported as a value change, and vice versa.
        </p>
      </Panel>
      <DualUploadLab<CompareResult> title="Upload Two Screens" description="Both images are registered, diffed and OCR'd. Changed regions are typed as a value, label, chart-line or visual change." run={(a, b) => compareScreens(a, b!)}>
        {(result) => result && <CompareView result={result} />}
      </DualUploadLab>
    </div>
  );
}

function CompareView({ result }: { result: CompareResult }) {
  const candidates: ProposalItem[] = result.value_changes
    .filter((v) => v.unit === "pct")
    .map((v) => ({ target: "bond_yield" as const, instrument_id: v.instrument, value: v.value_b, confidence: v.confidence, note: `Changed from ${v.value_a} to ${v.value_b} between the two screenshots` }));

  return (
    <>
      <div className="grid grid-4" style={{ marginBottom: 12 }}>
        <Metric label="Verdict" value={VERDICT_LABEL[result.verdict] ?? result.verdict} tone={VERDICT_TONE[result.verdict] ? "down" : "neutral"} />
        <Metric label="Mean SSIM" value={result.mean_ssim.toFixed(3)} sub="1.0 = pixel-identical" />
        <Metric label="Changed Pixels" value={`${result.changed_pixels_pct.toFixed(2)}%`} />
        <Metric label="Registration" value={result.layout.registered ? `OK (${result.layout.inliers} inliers)` : "Failed"} sub={result.layout.reason} />
      </div>

      {result.value_changes.length > 0 && (
        <Panel title="Instrument Value Changes (by label, not position)">
          <table className="data-table">
            <thead><tr><th>Instrument</th><th>Metric</th><th>Screen A</th><th>Screen B</th><th>Δ</th><th>Confidence</th></tr></thead>
            <tbody>
              {result.value_changes.map((v, i) => (
                <tr key={i}>
                  <td style={{ textAlign: "left" }}>{v.instrument}{v.flagged && <Badge kind="warn">FLAGGED</Badge>}</td>
                  <td>{v.metric}</td><td>{v.value_a}</td><td>{v.value_b}</td>
                  <td>{v.delta_bps !== null ? `${v.delta_bps > 0 ? "+" : ""}${v.delta_bps} bp` : v.delta}</td>
                  <td>{(v.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      {result.regions.length > 0 && (
        <Panel title={`Changed Regions (${result.regions.length})`}>
          <table className="data-table">
            <thead><tr><th>Kind</th><th>Area %</th><th>Min SSIM</th><th>Text A</th><th>Text B</th></tr></thead>
            <tbody>
              {result.regions.slice(0, 12).map((r, i) => (
                <tr key={i}><td style={{ textAlign: "left" }}>{r.kind.replace(/_/g, " ")}</td><td>{r.area_share_pct}%</td><td>{r.min_ssim}</td><td style={{ textAlign: "left" }}>{r.text_a || "—"}</td><td style={{ textAlign: "left" }}>{r.text_b || "—"}</td></tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      <ImageGrid images={result.images} labels={{ screen_a: "Screen A", screen_b_aligned: "Screen B (registered)", changes_overlay: "Changed regions", abs_difference: "Pixel difference heatmap", ssim_dissimilarity: "SSIM dissimilarity heatmap", sift_matches: "SIFT keypoint matches" }} />

      {result.notes.length > 0 && <div className="disclaimer-bar">{result.notes.map((n, i) => <div key={i}>⚠ {n}</div>)}</div>}
      <Panel title="Interpretation"><p style={{ fontSize: 11, color: "var(--text-mid)" }}>{result.interpretation}</p></Panel>
      {candidates.length > 0 && <ProposalReview source="screenshot_comparison" candidates={candidates} />}
    </>
  );
}
