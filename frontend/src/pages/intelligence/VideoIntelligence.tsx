import { useEffect, useRef, useState } from "react";
import { Badge, ErrorState, LoadingState, Metric, Panel } from "../../components/Common";
import type { JobStatus } from "../../services/visionApi";
import { cancelJob, getJobStatus, startDemoVideo, uploadVideo } from "../../services/visionApi";

const SEVERITY_BADGE: Record<string, "info" | "warn" | "sim"> = { info: "info", notice: "warn", alert: "warn" };

export default function VideoIntelligence() {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed" || job.status === "cancelled") {
      if (pollRef.current) window.clearTimeout(pollRef.current);
      return;
    }
    pollRef.current = window.setTimeout(async () => {
      try {
        setJob(await getJobStatus(job.id));
      } catch {
        /* transient */
      }
    }, 500);
    return () => { if (pollRef.current) window.clearTimeout(pollRef.current); };
  }, [job]);

  const start = async (fn: () => Promise<JobStatus>) => {
    setStarting(true);
    setError(null);
    try {
      setJob(await fn());
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Failed to start video analysis");
    } finally {
      setStarting(false);
    }
  };

  const onFile = (f: File | null) => { if (f) start(() => uploadVideo(f)); };

  return (
    <div>
      <Panel title="Video Intelligence">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Upload a screen recording of a market terminal (or run the simulated demo clip below). The
          video is read frame-by-frame, intelligently sampled (a change-threshold policy — not every
          frame, and not reinforcement learning — skips redundant frames and waits for the screen to
          settle), OCR'd only on the kept frames, and assembled into a chronological event timeline.
          Runs as a cancellable background job.
        </p>
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 8 }}>
          <input type="file" accept=".mp4,.avi,.mov,.webm,.mkv" onChange={(e) => onFile(e.target.files?.[0] ?? null)} disabled={starting} />
          <button onClick={() => start(startDemoVideo)} disabled={starting}>{starting ? "Starting…" : "Run simulated demo clip (no upload)"}</button>
        </div>
        {error && <ErrorState message={error} />}
      </Panel>

      {job && (
        <Panel title={`Job ${job.id} — ${job.status}`} right={job.status === "running" || job.status === "queued" ? <button onClick={() => cancelJob(job.id).then(setJob)}>Cancel</button> : undefined}>
          {(job.status === "queued" || job.status === "running") && (
            <>
              <div style={{ background: "var(--bg-2)", borderRadius: 3, height: 6, overflow: "hidden", marginBottom: 6 }}>
                <div style={{ width: `${job.progress * 100}%`, height: "100%", background: "var(--accent)", transition: "width 0.3s" }} />
              </div>
              <LoadingState label={job.message} />
            </>
          )}
          {job.status === "failed" && <ErrorState message={job.error ?? "Job failed"} />}
          {job.status === "cancelled" && <div className="empty-state">Cancelled.</div>}
          {job.status === "done" && job.result && <VideoResultView result={job.result} />}
        </Panel>
      )}
    </div>
  );
}

function VideoResultView({ result }: { result: NonNullable<JobStatus["result"]> }) {
  return (
    <>
      <div className="grid grid-4" style={{ marginBottom: 12 }}>
        <Metric label="Frames Sampled" value={String(result.stats.frames_sampled)} />
        <Metric label="Frames Selected" value={String(result.stats.frames_selected)} />
        <Metric label="OCR Calls Spared" value={`${result.stats.ocr_spared_pct}%`} />
        <Metric label="Processing Speed" value={`${result.stats.processing_fps} fps`} />
      </div>
      {result.meta?.events_created !== undefined && <p style={{ fontSize: 11, color: "var(--text-mid)" }}>{result.meta.events_created} event(s) raised for analyst review (see Overview intelligence feed). No market data was changed by this analysis.</p>}
      <Panel title="Timeline">
        <table className="data-table">
          <thead><tr><th>Time (s)</th><th>Kind</th><th>Severity</th><th>Event</th></tr></thead>
          <tbody>
            {result.events.map((e, i) => (
              <tr key={i}><td>{e.t.toFixed(1)}</td><td style={{ textAlign: "left" }}>{e.kind.replace(/_/g, " ")}</td><td style={{ textAlign: "left" }}><Badge kind={SEVERITY_BADGE[e.severity] ?? "info"}>{e.severity.toUpperCase()}</Badge></td><td style={{ textAlign: "left" }}>{e.title}</td></tr>
            ))}
          </tbody>
        </table>
      </Panel>
      <Panel title="Selected Frames">
        <div className="grid grid-4">
          {result.frames.map((f) => (
            <div key={f.index}>
              <img src={f.thumbnail} alt={`frame ${f.index}`} style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3 }} />
              <div style={{ fontSize: 10, color: "var(--text-mid)", marginTop: 2 }}>t={f.t.toFixed(1)}s · {f.fields.length} value(s)</div>
            </div>
          ))}
        </div>
      </Panel>
      <div className="disclaimer-bar">{result.limitations.map((l, i) => <div key={i}>⚠ {l}</div>)}</div>
    </>
  );
}
