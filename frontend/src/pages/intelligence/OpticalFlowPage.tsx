import { useState } from "react";
import { ErrorState, LoadingState, Metric, Panel } from "../../components/Common";
import type { FlowResult } from "../../services/visionApi";
import { analyzeFlow } from "../../services/visionApi";

export default function OpticalFlowPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<FlowResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (files.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeFlow(files));
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Panel title="Optical Flow">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Upload 2–10 screenshots of the same market screen in time order (consecutive frames of a
          live-updating chart or terminal). Dense Farneback flow and sparse Lucas-Kanade tracking (with
          a forward-backward consistency check) show where and how far pixels moved between frames.
          Optical flow measures <strong>visual movement only</strong> — it does not by itself establish
          market direction (a re-scaled axis or a scrolled window also produces motion).
        </p>
      </Panel>
      <Panel title="Upload Frames (in order)">
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
          <input type="file" accept=".png,.jpg,.jpeg,.webp" multiple onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
          <button className="primary" disabled={files.length < 2 || loading} onClick={run}>Run ({files.length} frame{files.length !== 1 ? "s" : ""})</button>
        </div>
        {loading && <LoadingState label="Computing flow…" />}
        {error && <ErrorState message={error} />}
      </Panel>
      {result && (
        <>
          <div className="grid grid-3" style={{ marginBottom: 12 }}>
            <Metric label="Frame Pairs" value={String(result.pairs.length)} />
            <Metric label="Mean Motion (px)" value={String(result.overall.mean_of_mean_magnitudes_px)} />
            <Metric label="Most Motion Between" value={`#${(result.overall.most_motion_pair as number[])[0]} → #${(result.overall.most_motion_pair as number[])[1]}`} />
          </div>
          {result.pairs.map((p, i) => (
            <Panel key={i} title={`Frame ${p.pair[0]} → ${p.pair[1]}`}>
              <div className="grid grid-4" style={{ marginBottom: 10 }}>
                <Metric label="Mean Magnitude" value={`${p.summary.mean_magnitude_px}px`} />
                <Metric label="Max Magnitude" value={`${p.summary.max_magnitude_px}px`} />
                <Metric label="Moving Pixels" value={`${p.summary.moving_pixel_share_pct}%`} />
                <Metric label="LK Moving Tracks" value={`${p.summary.lk_moving_tracks}/${p.summary.lk_corners}`} />
              </div>
              <div className="grid grid-2">
                <div>
                  <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Flow field (color = direction/magnitude)</div>
                  <img src={p.images.flow_color} alt="flow" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
                </div>
                <div>
                  <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Motion vectors (green = dense, orange = tracked corners)</div>
                  <img src={p.images.vectors} alt="vectors" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
                </div>
              </div>
              {p.curve_shift && (
                <p style={{ fontSize: 11, color: "var(--text-mid)", marginTop: 8 }}>
                  Plotted-line vertical shift: {(p.curve_shift as { median_shift_px: number }).median_shift_px}px — {(p.curve_shift as { note: string }).note}
                </p>
              )}
            </Panel>
          ))}
          <div className="disclaimer-bar">⚠ {result.caveat}</div>
          <Panel title="Methods"><ul style={{ fontSize: 11, color: "var(--text-mid)", margin: 0, paddingLeft: 18 }}>{result.methods.map((m, i) => <li key={i}>{m}</li>)}</ul></Panel>
        </>
      )}
    </div>
  );
}
