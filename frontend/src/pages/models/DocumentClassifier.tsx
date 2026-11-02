import { useEffect, useState } from "react";
import { Badge, ErrorState, Metric, Panel } from "../../components/Common";
import { SingleUploadLab } from "../../components/CvLabShared";
import type { ClassifyResult } from "../../services/visionApi";
import { classifyImage, fetchClassifierBenchmark } from "../../services/visionApi";

interface BenchmarkMetrics {
  test: { accuracy: number; f1_macro: number; confusion_matrix: number[][]; classes: string[]; per_class: { class: string; precision: number; recall: number; f1: number }[] };
  val_accuracy: number; torch_cpu_inference_ms_mean: number;
}
interface Benchmark {
  cnn: { architecture: string; params: number; metrics: BenchmarkMetrics; config: Record<string, unknown>; honesty_note: string };
  vit: { architecture: string; params: number; metrics: BenchmarkMetrics; config: Record<string, unknown>; honesty_note: string };
  dataset: { images_total: number; cache_split_counts: Record<string, number> };
}

function ProbBars({ probs }: { probs: Record<string, number> }) {
  const entries = Object.entries(probs);
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
          <div style={{ width: 110, fontSize: 10.5, color: "var(--text-mid)" }}>{k}</div>
          <div style={{ flex: 1, background: "var(--bg-2)", borderRadius: 3, height: 10, overflow: "hidden" }}>
            <div style={{ width: `${v * 100}%`, height: "100%", background: "var(--accent)" }} />
          </div>
          <div style={{ width: 44, fontSize: 10.5, textAlign: "right" }} className="mono">{(v * 100).toFixed(1)}%</div>
        </div>
      ))}
    </div>
  );
}

function ConfusionMatrix({ cm, classes }: { cm: number[][]; classes: string[] }) {
  const max = Math.max(...cm.flat());
  return (
    <table className="data-table" style={{ fontSize: 10 }}>
      <thead><tr><th></th>{classes.map((c) => <th key={c}>{c.slice(0, 4)}</th>)}</tr></thead>
      <tbody>
        {cm.map((row, i) => (
          <tr key={i}>
            <td style={{ textAlign: "left" }}>{classes[i].slice(0, 10)}</td>
            {row.map((v, j) => (
              <td key={j} style={{ background: i === j ? `rgba(59,130,246,${0.15 + 0.5 * (v / max)})` : v > 0 ? "rgba(229,72,77,0.12)" : undefined }}>{v}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DocumentClassifier() {
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [benchError, setBenchError] = useState<string | null>(null);

  useEffect(() => {
    fetchClassifierBenchmark().then((d) => setBenchmark(d as Benchmark)).catch((e) => setBenchError(e.response?.data?.detail ?? "Model not available"));
  }, []);

  return (
    <div>
      <Panel title="CNN vs. Vision Transformer — Document Type Classifier">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Classifies a financial screenshot into one of 8 types (yield curve, FX line chart,
          candlestick chart, bond table, market report, risk dashboard, portfolio chart, financial
          statement) with two models trained from scratch — a plain CNN and a Vision Transformer
          (patch embedding + multi-head self-attention, written from scratch, not a pretrained
          download) — side by side. Both are served in production via ONNX + OpenCV's DNN runner (no
          torch at runtime). Trained and evaluated on synthetic screenshots only.
        </p>
      </Panel>

      <SingleUploadLab<ClassifyResult> title="Classify a Screenshot" description="Upload any financial chart, table or report screenshot." run={classifyImage}>
        {(result) => result && (
          <>
            <div className="grid grid-2" style={{ marginBottom: 12 }}>
              {(["cnn", "vit"] as const).map((k) => {
                const p = result.predictions[k];
                return (
                  <Panel key={k} title={k.toUpperCase()}>
                    {p.available ? (
                      <>
                        <Metric label="Predicted" value={p.label ?? "—"} sub={`${((p.confidence ?? 0) * 100).toFixed(1)}% confidence · ${p.inference_ms}ms`} />
                        <div style={{ marginTop: 8 }}><ProbBars probs={p.probabilities ?? {}} /></div>
                      </>
                    ) : <div className="empty-state">{p.reason ?? "Unavailable"}</div>}
                  </Panel>
                );
              })}
            </div>
            {result.agree !== null && <Badge kind={result.agree ? "info" : "warn"}>{result.agree ? "Models agree" : "Models disagree"}</Badge>}
            <div className="disclaimer-bar" style={{ marginTop: 8 }}>⚠ {result.domain_gap_note}</div>
          </>
        )}
      </SingleUploadLab>

      {benchError && <ErrorState message={benchError} />}
      {benchmark && (
        <>
          <Panel title="Model Evaluation (held-out synthetic test templates)">
            <div className="grid grid-4" style={{ marginBottom: 12 }}>
              <Metric label="CNN Test Accuracy" value={`${(benchmark.cnn.metrics.test.accuracy * 100).toFixed(1)}%`} />
              <Metric label="ViT Test Accuracy" value={`${(benchmark.vit.metrics.test.accuracy * 100).toFixed(1)}%`} />
              <Metric label="CNN Params" value={benchmark.cnn.params.toLocaleString()} />
              <Metric label="ViT Params" value={benchmark.vit.params.toLocaleString()} />
            </div>
            <p style={{ fontSize: 11, color: "var(--text-mid)" }}>{benchmark.cnn.honesty_note}</p>
          </Panel>
          <div className="grid grid-2">
            <Panel title="CNN Confusion Matrix"><ConfusionMatrix cm={benchmark.cnn.metrics.test.confusion_matrix} classes={benchmark.cnn.metrics.test.classes} /></Panel>
            <Panel title="ViT Confusion Matrix"><ConfusionMatrix cm={benchmark.vit.metrics.test.confusion_matrix} classes={benchmark.vit.metrics.test.classes} /></Panel>
          </div>
        </>
      )}
    </div>
  );
}
