import { api } from "./api";

function uploadOne<T>(endpoint: string, file: File, params?: Record<string, string | number | boolean>, extra?: Record<string, string>) {
  const form = new FormData();
  form.append("file", file);
  if (extra) for (const [k, v] of Object.entries(extra)) form.append(k, v);
  return api.post<T>(endpoint, form, { params, headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
}

function uploadTwo<T>(endpoint: string, fileA: File, fileB: File, params?: Record<string, string | number | boolean>) {
  const form = new FormData();
  form.append("file_a", fileA);
  form.append("file_b", fileB);
  return api.post<T>(endpoint, form, { params, headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
}

export const sampleImageUrl = (kind: string, opts?: { template?: number; variant?: number; scale?: number; anomaly_kind?: string }) => {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "/api";
  const p = new URLSearchParams({ kind, ...(opts?.template !== undefined ? { template: String(opts.template) } : {}), ...(opts?.variant !== undefined ? { variant: String(opts.variant) } : {}),
    ...(opts?.scale !== undefined ? { scale: String(opts.scale) } : {}), ...(opts?.anomaly_kind ? { anomaly_kind: opts.anomaly_kind } : {}) });
  return `${base}/vision/sample-image?${p.toString()}`;
};

export const urlToFile = async (url: string, name: string): Promise<File> => {
  const blob = await (await fetch(url)).blob();
  return new File([blob], name, { type: blob.type || "image/png" });
};

// ---------------------------------------------------------------- 1. digitization
export interface DigitizedPoint {
  x_px: number; y_px: number; x_fraction: number; y_fraction: number;
  tenor?: string; x_label?: string; x_value?: number; y_value?: number; y_uncertainty?: number; loc_err_px: number; steep_segment?: boolean;
}
export interface DigitizedSeries {
  index: number; color_bgr: number[]; mode: "markers" | "continuous"; n_points: number; coverage: number; line_thickness_px: number;
  gaps: { x_start_px: number; x_end_px: number }[]; points: DigitizedPoint[];
}
export interface DigitizeResult {
  filename: string; image_size: number[]; plot_rect: number[]; axes_found: boolean; theme: string; series: DigitizedSeries[]; limitations: string[];
  ocr_available: boolean; chart_kind: string; confidence: number; confidence_factors: { factor: string; score: number }[]; confidence_note: string;
  calibration?: { y: Record<string, unknown>; x: Record<string, unknown> }; resolution?: { value_per_pixel_y: number | null; quantisation_note: string };
  overlay?: string; csv: string; error?: string;
}
export const digitizeChart = (file: File, manual?: { y_top_value?: number; y_bottom_value?: number }) =>
  uploadOne<DigitizeResult>("/vision/digitize", file, undefined, manual && manual.y_top_value !== undefined ? { y_top_value: String(manual.y_top_value), y_bottom_value: String(manual.y_bottom_value) } : undefined);

// ---------------------------------------------------------------- 4. comparison
export interface CompareValueChange {
  instrument: string; metric: string; unit: string; value_a: number; value_b: number; delta: number; delta_bps: number | null; confidence: number; flagged: boolean; note: string;
}
export interface CompareRegion { bbox: number[]; area_share_pct: number; mean_abs_diff: number; min_ssim: number; kind: string; text_a?: string; text_b?: string }
export interface CompareResult {
  verdict: string; mean_ssim: number; changed_pixels_pct: number;
  layout: { registered: boolean; inliers: number; inlier_ratio: number; transform?: Record<string, unknown>; layout_shift?: boolean; reason?: string };
  regions: CompareRegion[]; value_changes: CompareValueChange[]; instruments_appeared: Record<string, unknown>[]; instruments_disappeared: Record<string, unknown>[];
  ocr_available: boolean; notes: string[]; images: Record<string, string>; interpretation: string;
}
export const compareScreens = (fileA: File, fileB: File) => uploadTwo<CompareResult>("/vision/compare", fileA, fileB);

// ---------------------------------------------------------------- 5. quality
export interface QualityCheck { check: string; metric: string; status: "ok" | "warn" | "poor" | "unknown"; detail: string }
export interface QualityAssess { measurements: Record<string, unknown>; checks: QualityCheck[]; quality_score: number; verdict: "good" | "fair" | "poor"; recommendations: { op: string; why: string }[]; score_note: string }
export interface QualityResult { filename: string; before: QualityAssess; after: QualityAssess; applied_operations: string[]; comparison: { metric: string; before: unknown; after: unknown }[]; images: { before: string; after: string }; caveat: string }
export const analyzeQuality = (file: File) => uploadOne<QualityResult>("/vision/quality", file);

// ---------------------------------------------------------------- 6. anomaly
export interface Anomaly { kind: string; severity: number; bbox: number[]; description: string; evidence: Record<string, unknown> }
export interface AnomalyResult { filename?: string; anomalies: Anomaly[]; n_anomalies: number; chart_kind: string | null; digitization_confidence: number | null; method_notes: string[]; disclaimer: string; review_required: boolean; overlay: string; detectors: Record<string, string>; ground_truth?: { injected: Record<string, unknown> | null; note: string }; source_image?: string }
export const analyzeAnomaly = (file: File) => uploadOne<AnomalyResult>("/vision/anomaly", file);
export const anomalySample = (kind: string, anomalyKind: string) =>
  api.get<AnomalyResult>("/vision/anomaly/sample", { params: { kind, anomaly_kind: anomalyKind } }).then((r) => r.data);

// ---------------------------------------------------------------- 7. optical flow
export interface FlowPairResult { pair: number[]; summary: Record<string, number | null>; moving_regions: Record<string, unknown>[]; curve_shift: Record<string, unknown> | null; images: { flow_color: string; vectors: string } }
export interface FlowResult { n_frames: number; pairs: FlowPairResult[]; overall: Record<string, unknown>; caveat: string; methods: string[]; filenames: string[] }
export const analyzeFlow = (files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return api.post<FlowResult>("/vision/flow", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};

// ---------------------------------------------------------------- 8. video
export interface VideoFrame { index: number; t: number; score_changed_pct: number; score_block_mean: number; reason: string; content: Record<string, unknown>; fields: { instrument: string; metric: string; value: number; unit: string; confidence: number; flagged: boolean }[]; thumbnail: string }
export interface VideoEvent { t: number; frame_index: number; kind: string; severity: string; title: string; detail: Record<string, unknown> }
export interface VideoResult {
  video: Record<string, unknown>; frames: VideoFrame[]; tracks: Record<string, { t: number; value: number; confidence: number; flagged: boolean }[]>;
  events: VideoEvent[]; stats: Record<string, number>; ocr_enabled: boolean; selection_policy: Record<string, unknown>; limitations: string[]; meta?: { scripted_truth?: Record<string, unknown>; events_created?: number };
}
export interface JobStatus { id: string; kind: string; status: "queued" | "running" | "done" | "failed" | "cancelled"; progress: number; message: string; error: string | null; result?: VideoResult; meta: Record<string, unknown> }
export const uploadVideo = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<JobStatus>("/vision/video", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};
export const startDemoVideo = () => api.post<JobStatus>("/vision/video/demo").then((r) => r.data);
export const getJobStatus = (id: string) => api.get<JobStatus>(`/vision/jobs/${id}`).then((r) => r.data);
export const cancelJob = (id: string) => api.delete<JobStatus>(`/vision/jobs/${id}`).then((r) => r.data);

// ---------------------------------------------------------------- 9. classifier
export interface ClassPrediction { available: boolean; label?: string; confidence?: number; inference_ms?: number; probabilities?: Record<string, number>; reason?: string }
export interface ClassifyResult { filename: string; predictions: { cnn: ClassPrediction; vit: ClassPrediction }; agree: boolean | null; classes: string[]; architectures: Record<string, string | null>; domain_gap_note: string }
export const classifyImage = (file: File) => uploadOne<ClassifyResult>("/vision/classify", file);
export const fetchClassifierBenchmark = () => api.get("/vision/classifier/benchmark").then((r) => r.data);

// ---------------------------------------------------------------- 10. similarity
export interface SimilarityResult {
  cosine_similarity: number; ssim: number | null; verdict: { label: string; text: string }; thresholds: Record<string, number>;
  sift: { good_matches: number; inliers: number; registered: boolean }; model: Record<string, unknown>; caveat: string; matched_regions_image?: string;
}
export const compareSimilarity = (fileA: File, fileB: File) => uploadTwo<SimilarityResult>("/vision/similarity/compare", fileA, fileB);

export interface IndexItem { id: number; filename: string; origin: string; kind_guess: string | null; created_at: string; width?: number; height?: number; thumbnail?: string }
export const listIndex = () => api.get<{ count: number; items: IndexItem[]; encoder: Record<string, unknown> }>("/vision/index").then((r) => r.data);
export const addToIndex = (file: File) => uploadOne<{ id: number; filename: string; kind_guess: string | null }>("/vision/index", file);
export const seedSyntheticIndex = () => api.post<{ added: number }>("/vision/index/seed-synthetic").then((r) => r.data);
export const searchIndex = (file: File, topK = 6) => uploadOne<{ query: string; index_size: number; results: (IndexItem & { similarity: number; verdict: string })[]; thresholds: Record<string, number> }>("/vision/index/search", file, { top_k: topK });
export const deleteIndexItem = (id: number) => api.delete(`/vision/index/${id}`).then((r) => r.data);

// ---------------------------------------------------------------- 11. zero-shot search
export interface ClipStatus { available: boolean; model?: string; reason?: string; how_to_enable?: string }
export const fetchClipStatus = () => api.get<ClipStatus>("/vision/clip/status").then((r) => r.data);
export interface ZeroShotResult { query: string; backend: string; clip_ran: boolean; clip_status: ClipStatus; results: { name: string; score: number; rank: number; thumbnail: string; synthetic_reference: boolean; evidence?: Record<string, unknown> }[]; score_meaning: string; limitations: string[] }
export const zeroShotSearch = (query: string, files: File[], includeReference: boolean, backend: "auto" | "clip" | "fallback" = "auto") => {
  const form = new FormData();
  form.append("query", query);
  form.append("backend", backend);
  form.append("include_reference", String(includeReference));
  files.forEach((f) => form.append("files", f));
  return api.post<ZeroShotResult>("/vision/search/zero-shot", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};

// ---------------------------------------------------------------- model registry
export const fetchVisionModels = () => api.get("/vision/models").then((r) => r.data);

// ---------------------------------------------------------------- analyst review: proposals & events
export interface ProposalItem { target: "bond_yield" | "fx"; instrument_id: string; value: number; confidence?: number; uncertainty?: number; note?: string }
export interface VisionProposal {
  id: number; source: string; source_ref: string | null; target: string; instrument_id: string; proposed_value: number; previous_value: number | null; unit: string | null;
  confidence: number | null; uncertainty: number | null; note: string | null; validation: { ok: boolean; errors: string[]; warnings: string[]; requires_confirmation: boolean };
  status: "pending" | "approved" | "rejected"; created_at: string; decided_at: string | null; applied_value: number | null; resolved_isin: string | null;
}
export const createProposals = (source: string, items: ProposalItem[], sourceRef?: string) =>
  api.post<{ created: VisionProposal[]; skipped: { instrument_id: string; value: number; reason: string }[]; message: string }>("/vision/proposals", { source, source_ref: sourceRef, items }).then((r) => r.data);
export const listProposals = (status?: string) => api.get<VisionProposal[]>("/vision/proposals", { params: status ? { status } : {} }).then((r) => r.data);
export const approveProposal = (id: number, opts?: { value?: number; confirm_flagged?: boolean; note?: string }) =>
  api.post<{ proposal: VisionProposal; analytics: Record<string, unknown> }>(`/vision/proposals/${id}/approve`, opts ?? {}).then((r) => r.data);
export const rejectProposal = (id: number, note?: string) => api.post<VisionProposal>(`/vision/proposals/${id}/reject`, { note }).then((r) => r.data);

export interface VisionEvent { id: number; kind: string; source: string; severity: string; title: string; detail: Record<string, unknown>; status: string; created_at: string }
export const listEvents = (status?: string) => api.get<VisionEvent[]>("/vision/events", { params: status ? { status } : {} }).then((r) => r.data);
export const setEventStatus = (id: number, status: string) => api.post<VisionEvent>(`/vision/events/${id}/status`, undefined, { params: { status } }).then((r) => r.data);
