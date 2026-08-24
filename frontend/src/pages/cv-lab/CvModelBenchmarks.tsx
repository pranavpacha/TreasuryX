import { MultiCurveChart } from "../../charts/MultiCurveChart";
import { Badge, LoadingState, Metric, Panel } from "../../components/Common";
import { useApi } from "../../hooks/useApi";
import type { ModelMetrics } from "../../services/academicCvApi";
import { fetchModelBenchmarks } from "../../services/academicCvApi";

function ConfusionMatrix({ cm, classes }: { cm: number[][]; classes: string[] }) {
  const max = Math.max(...cm.flat());
  return (
    <table className="data-table">
      <thead>
        <tr><th></th>{classes.map((c) => <th key={c}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {cm.map((row, i) => (
          <tr key={i}>
            <td style={{ textAlign: "left" }}>{classes[i]}</td>
            {row.map((v, j) => {
              const intensity = max > 0 ? v / max : 0;
              return (
                <td key={j} style={{ background: i === j ? `rgba(47,191,113,${0.15 + intensity * 0.5})` : `rgba(229,72,77,${intensity * 0.4})` }}>
                  {v}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ModelPanel({ name, m }: { name: string; m: ModelMetrics }) {
  return (
    <Panel title={`${name} Results`}>
      <div className="grid grid-4" style={{ marginBottom: 12 }}>
        <Metric label="Test Accuracy" value={(m.accuracy * 100).toFixed(1)} unit="%" />
        <Metric label="Macro F1" value={(m.f1_macro * 100).toFixed(1)} unit="%" />
        <Metric label="Parameters" value={m.params.toLocaleString()} />
        <Metric label="Avg Inference" value={m.avg_inference_ms.toFixed(2)} unit="ms/image" />
      </div>
      <div className="grid grid-2">
        <div>
          <div className="panel-title">Confusion Matrix (test set)</div>
          <ConfusionMatrix cm={m.confusion_matrix} classes={m.classes} />
        </div>
        <div>
          <div className="panel-title">Training Curves</div>
          <MultiCurveChart
            data={m.history.map((h) => ({ epoch: h.epoch, train_acc: h.train_acc, val_acc: h.val_acc }))}
            xKey="epoch"
            series={[
              { key: "train_acc", color: "var(--text-mid)", label: "Train Acc" },
              { key: "val_acc", color: "var(--accent)", label: "Val Acc" },
            ]}
            height={200}
          />
        </div>
      </div>
      <div className="panel-title" style={{ marginTop: 12 }}>Sample Predictions</div>
      <div className="grid grid-4">
        {m.sample_predictions.map((s, i) => (
          <div key={i} style={{ textAlign: "center" }}>
            <img src={s.image} alt="sample" style={{ width: "100%", border: `2px solid ${s.correct ? "var(--up)" : "var(--down)"}`, borderRadius: 3 }} />
            <div style={{ fontSize: 10, marginTop: 3 }}>
              <div>true: {s.true_label}</div>
              <div className={s.correct ? "up" : "down"}>pred: {s.pred_label}</div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export default function CvModelBenchmarks() {
  const { data, loading, error } = useApi(fetchModelBenchmarks);

  if (loading) return <LoadingState label="Loading model benchmark results…" />;
  if (error) return (
    <div className="empty-state">
      Precomputed CNN/ViT benchmark results are not available in this deployment.<br />
      Run <code>python -m app.cv_engine.models.train</code> locally (requires torch) to generate them.
    </div>
  );
  if (!data) return null;

  return (
    <div>
      <Panel title="CNN vs. Vision Transformer -- Model Comparison">
        <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
          Both models are trained from scratch on the SAME small, procedurally-generated synthetic dataset
          ({data.dataset.n_train} train / {data.dataset.n_val} val / {data.dataset.n_test} test images across{" "}
          {data.dataset.classes.join(", ")}). {data.dataset.note} Near-ceiling accuracy on this task is expected --
          the four classes are structurally very distinct (lines vs. bars vs. table grids) -- this is a controlled
          architecture comparison, not a claim of real-world chart-recognition accuracy.
        </p>
        <div className="grid grid-2" style={{ marginTop: 10 }}>
          <Badge>CNN: {data.cnn.params.toLocaleString()} params, {data.cnn.train_time_sec.toFixed(1)}s train</Badge>
          <Badge>ViT: {data.vit.params.toLocaleString()} params, {data.vit.train_time_sec.toFixed(1)}s train</Badge>
        </div>
      </Panel>
      <ModelPanel name="TinyCNN" m={data.cnn} />
      <ModelPanel name="TinyViT" m={data.vit} />
      <Panel title="Why might CNN be better for lightweight deployment? Why might ViT capture global relationships more effectively?">
        <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
          CNNs use local convolutional receptive fields with weight sharing -- fewer parameters for a given input
          size, strong built-in translation-equivariance, and cheaper inference, which favors edge/laptop deployment.
          ViTs treat the image as a sequence of patches attended to globally from layer 1 -- this can capture
          long-range spatial relationships (e.g. an axis label far from its corresponding data point) more directly,
          at the cost of needing more data or explicit positional encoding to learn spatial structure that CNNs get
          "for free" from their architecture. Neither is universally superior -- the right choice depends on data
          scale, latency budget, and the spatial structure of the task.
        </p>
      </Panel>
    </div>
  );
}
