import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Panel } from "../components/Common";
import type { CvCommitResult, CvExtractionResult, CvField } from "../services/api";
import { commitCvExtraction, correctCvExtraction, uploadCvImage } from "../services/api";

const STAGE_LABELS: Record<string, string> = {
  original: "1. Original (resized)",
  grayscale: "2. Grayscale",
  denoised: "3. Denoised (Non-local Means)",
  normalized: "4. Contrast Normalized (CLAHE)",
  thresholded: "5. Adaptive Threshold",
  edges: "6. Canny Edge Detection",
  regions: "7. Detected Chart Region + Hough Lines",
};

const STAGE_PURPOSE: Record<string, string> = {
  original: "The uploaded image, resized so processing stays fast on a laptop.",
  grayscale: "Removes color to simplify structural analysis.",
  denoised: "Non-local-means denoising removes screenshot compression artifacts.",
  normalized: "CLAHE boosts local contrast so faint gridlines/text become readable.",
  thresholded: "Adaptive binarization separates text/lines from background.",
  edges: "Canny edge detection finds chart boundaries and axis lines.",
  regions: "Hough line transform + contour detection locates the plotted chart area.",
};

export default function MarketIntelligence() {
  const [result, setResult] = useState<CvExtractionResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [committing, setCommitting] = useState<number | null>(null);
  const [commitResults, setCommitResults] = useState<Record<number, CvCommitResult | string>>({});
  const [showDetails, setShowDetails] = useState(false);
  const [showModelDetails, setShowModelDetails] = useState(false);
  const [howDetectedIdx, setHowDetectedIdx] = useState<number | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const [correctedFields, setCorrectedFields] = useState<CvField[]>([]);

  const onUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setCommitResults({});
    try {
      const r = await uploadCvImage(file);
      setResult(r);
      setCorrectedFields(r.fields);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const updateField = (idx: number, value: number) => {
    setCorrectedFields((fields) => fields.map((f, i) => (i === idx ? { ...f, value } : f)));
  };

  const applyToTreasury = async (idx: number) => {
    const field = correctedFields[idx];
    if (!result || !field.instrument || field.value == null) return;
    setCommitting(idx);
    try {
      // Persist any manual edit BEFORE committing, so the engine uses the reviewed value.
      await correctCvExtraction(result.id, correctedFields);
      const target = result.chart_type === "yield_curve" ? "bond_yield" : "fx";
      const analytics = await commitCvExtraction(result.id, target, field.instrument.replace("/", ""));
      setCommitResults((r) => ({ ...r, [idx]: analytics }));
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setCommitResults((r) => ({ ...r, [idx]: err.response?.data?.detail ?? err.message ?? "Commit failed" }));
    } finally {
      setCommitting(null);
    }
  };

  return (
    <div>
      <Panel title="Financial Image Intelligence" right={<Badge kind="info">FOCV PIPELINE: OpenCV · OCR · Segmentation · CNN/ViT (live when available)</Badge>}>
        <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
          Upload a screenshot of an FX chart, yield curve, or financial report. TreasuryX preprocesses it, detects
          the chart region, runs OCR, extracts structured financial values, and — once you review and confirm — can
          apply a corrected value directly into the Treasury engine, updating bond/FX analytics, risk, and the 3D
          visualizations everywhere else in the app. Max 8MB, PNG/JPG/WEBP only.
        </p>
        <input
          ref={fileInput} type="file" accept=".png,.jpg,.jpeg,.webp"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); }}
        />
        {uploading && <div className="loading-state">Running image intelligence pipeline…</div>}
        {error && <div className="error-state">{error}</div>}
      </Panel>

      {result && (
        <>
          <Panel title="Extracted Financial Information" right={<span style={{ fontSize: 10.5, color: "var(--text-mid)" }}>Chart type: {result.chart_type} · Mean confidence: {(result.mean_confidence * 100).toFixed(0)}%</span>}>
            {result.warnings.length > 0 && (
              <div className="disclaimer-bar">
                {result.warnings.map((w, i) => <div key={i}>{w}</div>)}
              </div>
            )}
            {correctedFields.length === 0 && <div className="empty-state">No structured fields extracted. Try a clearer image.</div>}
            {correctedFields.map((f, i) => {
              const commitResult = commitResults[i];
              return (
                <div key={i} style={{ borderBottom: "1px solid var(--bg-2)", padding: "8px 0" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 90, fontSize: 12 }}>{f.instrument ?? "(unlabeled)"}</span>
                    <span style={{ width: 60, fontSize: 10.5, color: "var(--text-lo)" }}>{f.metric}</span>
                    <input
                      style={{ width: 90 }} type="number" value={f.value ?? ""}
                      onChange={(e) => updateField(i, Number(e.target.value))}
                    />
                    <span style={{ fontSize: 10.5, color: "var(--text-lo)" }}>{f.unit}</span>
                    <Badge kind={f.confidence >= 0.7 ? "info" : "warn"}>{(f.confidence * 100).toFixed(0)}%</Badge>
                    <button onClick={() => setHowDetectedIdx(howDetectedIdx === i ? null : i)}>How Detected?</button>
                    <button className="primary" style={{ marginLeft: "auto" }} disabled={!f.instrument || committing === i} onClick={() => applyToTreasury(i)}>
                      {committing === i ? "Applying…" : "Apply to Treasury"}
                    </button>
                  </div>

                  {howDetectedIdx === i && (
                    <div className="panel" style={{ marginTop: 8, fontSize: 11, color: "var(--text-mid)" }}>
                      <div><strong>Trace:</strong> uploaded image → preprocessing (resize/grayscale/CLAHE/threshold) → region detection (Canny + Hough) → OCR word "{f.instrument}" and its nearest numeric token → paired as ({f.metric} = {f.value}{f.unit}) → confidence {(f.confidence * 100).toFixed(0)}% (min of the two OCR word confidences).</div>
                      {f.source_region && <div style={{ marginTop: 4 }}>Source pixel region (x, y, w, h): [{f.source_region.join(", ")}]</div>}
                    </div>
                  )}

                  {commitResult && typeof commitResult === "string" && (
                    <div className="error-state" style={{ marginTop: 6 }}>{commitResult}</div>
                  )}
                  {commitResult && typeof commitResult === "object" && (
                    <div className="panel" style={{ marginTop: 8, borderColor: "var(--up)" }}>
                      <Badge kind="info">Portfolio updated</Badge>
                      <table className="data-table" style={{ marginTop: 6 }}>
                        <tbody>
                          <tr><td style={{ textAlign: "left" }}>{commitResult.field}</td><td>{commitResult.previous_value} → <strong>{commitResult.new_value}</strong></td></tr>
                          {commitResult.clean_price_before != null && (
                            <tr><td style={{ textAlign: "left" }}>Clean price</td><td>{commitResult.clean_price_before} → <strong>{commitResult.clean_price_after}</strong></td></tr>
                          )}
                          {commitResult.dv01_per_100_face_after != null && (
                            <tr><td style={{ textAlign: "left" }}>DV01 / 100 face (new)</td><td>{commitResult.dv01_per_100_face_after}</td></tr>
                          )}
                        </tbody>
                      </table>
                      {commitResult.affected_open_positions.length > 0 && (
                        <div style={{ fontSize: 11, color: "var(--text-mid)", marginTop: 6 }}>
                          {commitResult.affected_open_positions.length} open position(s) repriced. See{" "}
                          <Link to="/rates">Rates & Bonds</Link>, <Link to="/risk">Portfolio Risk</Link>, or{" "}
                          <Link to="/visualization/3d-market">3D Market</Link> to see it reflected everywhere.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </Panel>

          <Panel title="Processing Details" right={<button onClick={() => setShowDetails((s) => !s)}>{showDetails ? "Hide" : "Show"}</button>}>
            {!showDetails && <p style={{ fontSize: 11, color: "var(--text-lo)" }}>Click "Show" to inspect every preprocessing/OCR stage this image went through.</p>}
            {showDetails && (
              <>
                <div className="grid grid-4">
                  {Object.entries(result.stages).map(([key, src]) => (
                    <div key={key}>
                      <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>{STAGE_LABELS[key] ?? key}</div>
                      <img src={src} alt={key} style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3 }} />
                      <div style={{ fontSize: 10, color: "var(--text-lo)", marginTop: 3 }}>{STAGE_PURPOSE[key]}</div>
                    </div>
                  ))}
                </div>
                <hr className="sep" />
                <div className="panel-title">OCR Result (Raw Text)</div>
                {!result.ocr_available && (
                  <div className="empty-state">
                    OCR engine unavailable in this environment. Preprocessing / edge / region detection stages above still ran.
                  </div>
                )}
                <div className="mono" style={{ fontSize: 11.5, whiteSpace: "pre-wrap", color: "var(--text-mid)" }}>
                  {result.ocr_text_raw || "(no text detected)"}
                </div>
              </>
            )}
          </Panel>

          <Panel title="Model Details — CNN vs. ViT" right={<button onClick={() => setShowModelDetails((s) => !s)}>{showModelDetails ? "Hide" : "Show"}</button>}>
            {!showModelDetails && <p style={{ fontSize: 11, color: "var(--text-lo)" }}>Click "Show" to see how the trained CNN and Vision Transformer classify this specific image.</p>}
            {showModelDetails && (
              !result.model_details.available ? (
                <div className="empty-state">
                  {result.model_details.reason}
                </div>
              ) : (
                <>
                  <table className="data-table">
                    <thead><tr><th>Model</th><th>Predicted class</th><th>Confidence</th><th>Inference time</th></tr></thead>
                    <tbody>
                      <tr>
                        <td style={{ textAlign: "left" }}>CNN (TinyCNN, from scratch)</td>
                        <td>{result.model_details.cnn?.label}</td>
                        <td>{((result.model_details.cnn?.confidence ?? 0) * 100).toFixed(1)}%</td>
                        <td>{result.model_details.cnn?.inference_ms.toFixed(2)} ms</td>
                      </tr>
                      <tr>
                        <td style={{ textAlign: "left" }}>ViT (TinyViT, from scratch)</td>
                        <td>{result.model_details.vit?.label}</td>
                        <td>{((result.model_details.vit?.confidence ?? 0) * 100).toFixed(1)}%</td>
                        <td>{result.model_details.vit?.inference_ms.toFixed(2)} ms</td>
                      </tr>
                    </tbody>
                  </table>
                  <div style={{ marginTop: 8 }}>
                    <Badge kind={result.model_details.agree ? "info" : "warn"}>
                      {result.model_details.agree ? "Models agree" : "Models disagree"}
                    </Badge>
                  </div>
                  <p style={{ fontSize: 10.5, color: "var(--text-lo)", marginTop: 8 }}>
                    {result.model_details.note} Full accuracy/precision/recall/F1/confusion-matrix benchmark: <Link to="/evidence/cv/models">CNN vs. Vision Transformer</Link>.
                  </p>
                </>
              )
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
