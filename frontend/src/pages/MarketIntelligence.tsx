import { useRef, useState } from "react";
import { Badge, Panel } from "../components/Common";
import type { CvExtractionResult } from "../services/api";
import { commitCvExtraction, uploadCvImage } from "../services/api";

const STAGE_LABELS: Record<string, string> = {
  original: "1. Original (resized)",
  grayscale: "2. Grayscale",
  denoised: "3. Denoised (Non-local Means)",
  normalized: "4. Contrast Normalized (CLAHE)",
  thresholded: "5. Adaptive Threshold",
  edges: "6. Canny Edge Detection",
  regions: "7. Detected Chart Region + Hough Lines",
};

export default function MarketIntelligence() {
  const [result, setResult] = useState<CvExtractionResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [commitMsg, setCommitMsg] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const [correctedFields, setCorrectedFields] = useState<CvExtractionResult["fields"]>([]);

  const onUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setCommitMsg(null);
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

  const commit = async (field: CvExtractionResult["fields"][number]) => {
    if (!result || !field.instrument || field.value == null) return;
    const target = result.chart_type === "yield_curve" ? "bond_yield" : "fx";
    try {
      const analytics = await commitCvExtraction(result.id, target, field.instrument.replace("/", ""));
      setCommitMsg(`Committed to Treasury engine: ${JSON.stringify(analytics)}`);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setCommitMsg(`Commit failed: ${err.response?.data?.detail ?? err.message}`);
    }
  };

  return (
    <div>
      <Panel title="Upload Financial Chart / Report Image">
        <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
          Upload a screenshot of an FX chart, yield curve, or financial report. The Computer Vision pipeline runs
          preprocessing → edge/region detection → OCR → chart classification → structured field extraction, entirely
          on-device (OpenCV + Tesseract). Max 8MB, PNG/JPG/WEBP only.
        </p>
        <input
          ref={fileInput} type="file" accept=".png,.jpg,.jpeg,.webp"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); }}
        />
        {uploading && <div className="loading-state">Running CV pipeline…</div>}
        {error && <div className="error-state">{error}</div>}
      </Panel>

      {result && (
        <>
          <Panel title={`Pipeline Stages — ${result.original_filename} (${result.chart_type})`}>
            <div className="grid grid-4">
              {Object.entries(result.stages).map(([key, src]) => (
                <div key={key}>
                  <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>{STAGE_LABELS[key] ?? key}</div>
                  <img src={src} alt={key} style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3 }} />
                </div>
              ))}
            </div>
          </Panel>

          <div className="grid grid-2">
            <Panel title="OCR Result (Raw Text)">
              {!result.ocr_available && (
                <div className="empty-state">
                  OCR engine unavailable in this environment. Preprocessing / edge / region detection stages above still ran.
                </div>
              )}
              <div className="mono" style={{ fontSize: 11.5, whiteSpace: "pre-wrap", color: "var(--text-mid)" }}>
                {result.ocr_text_raw || "(no text detected)"}
              </div>
            </Panel>

            <Panel title="Extracted Financial Values" right={<span style={{ fontSize: 10.5, color: "var(--text-mid)" }}>Mean confidence: {(result.mean_confidence * 100).toFixed(0)}%</span>}>
              {result.warnings.length > 0 && (
                <div className="disclaimer-bar">
                  {result.warnings.map((w, i) => <div key={i}>{w}</div>)}
                </div>
              )}
              {correctedFields.length === 0 && <div className="empty-state">No structured fields extracted. Try a clearer image.</div>}
              {correctedFields.map((f, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "1px solid var(--bg-2)" }}>
                  <span style={{ width: 90, fontSize: 12 }}>{f.instrument ?? "(unlabeled)"}</span>
                  <span style={{ width: 60, fontSize: 10.5, color: "var(--text-lo)" }}>{f.metric}</span>
                  <input
                    style={{ width: 90 }} type="number" value={f.value ?? ""}
                    onChange={(e) => updateField(i, Number(e.target.value))}
                  />
                  <span style={{ fontSize: 10.5, color: "var(--text-lo)" }}>{f.unit}</span>
                  <Badge kind={f.confidence >= 0.7 ? "info" : "warn"}>{(f.confidence * 100).toFixed(0)}%</Badge>
                  <button style={{ marginLeft: "auto" }} disabled={!f.instrument} onClick={() => commit(f)}>Commit → Engine</button>
                </div>
              ))}
              {commitMsg && <div className="mono" style={{ fontSize: 10.5, marginTop: 8, color: "var(--text-mid)", wordBreak: "break-all" }}>{commitMsg}</div>}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}
