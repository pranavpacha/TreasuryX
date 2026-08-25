import { api } from "./api";

export interface LabImageResult {
  images: Record<string, string>;
  [key: string]: unknown;
}

function uploadOne<T>(endpoint: string, file: File, params?: Record<string, string | number>) {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<T>(endpoint, form, { params, headers: { "Content-Type": "multipart/form-data" } })
    .then((r) => r.data);
}

function uploadTwo<T>(endpoint: string, fileA: File, fileB: File | null, params?: Record<string, string | number>) {
  const form = new FormData();
  form.append("file_a", fileA);
  if (fileB) form.append("file_b", fileB);
  return api
    .post<T>(endpoint, form, { params, headers: { "Content-Type": "multipart/form-data" } })
    .then((r) => r.data);
}

export const runFiltersLab = (file: File, kernel_size: number, sigma: number) =>
  uploadOne<LabImageResult>("/academic/cv/filters", file, { kernel_size, sigma });

export const runEdgesLab = (file: File, canny_low: number, canny_high: number, dog_sigma1: number, dog_sigma2: number) =>
  uploadOne<LabImageResult>("/academic/cv/edges", file, { canny_low, canny_high, dog_sigma1, dog_sigma2 });

export const runFeaturesLab = (file: File) =>
  uploadOne<LabImageResult & { n_corners: number; n_blobs: number }>("/academic/cv/features", file);

export interface SiftResult {
  images: Record<string, string>;
  result: {
    n_keypoints_a: number; n_keypoints_b: number; n_descriptors_a: number; n_descriptors_b: number;
    n_matches_raw: number; n_good_matches: number; match_ratio_threshold: number; similarity_pct: number;
  };
}
export const runSiftLab = (fileA: File, fileB: File, ratio_thresh: number) =>
  uploadTwo<SiftResult>("/academic/cv/sift", fileA, fileB, { ratio_thresh });

export const runSegmentationLab = (file: File) =>
  uploadOne<LabImageResult & { init_rect: number[] }>("/academic/cv/segmentation", file);

export interface SegmentationBenchmark {
  n_samples: number; mean_iou: number; mean_dice: number; min_iou: number; max_iou: number;
}
export const fetchSegmentationBenchmark = () =>
  api.get<SegmentationBenchmark>("/academic/cv/segmentation/benchmark").then((r) => r.data);

export interface OpticalFlowResult {
  images: Record<string, string>;
  mean_magnitude: number;
  max_magnitude: number;
  second_frame_synthetic: boolean;
}
export const runOpticalFlowLab = (fileA: File, fileB: File | null) =>
  uploadTwo<OpticalFlowResult>("/academic/cv/optical-flow", fileA, fileB);

export interface ModelMetrics {
  params: number;
  epochs: number;
  train_time_sec: number;
  accuracy: number;
  precision_macro: number;
  recall_macro: number;
  f1_macro: number;
  avg_inference_ms: number;
  confusion_matrix: number[][];
  classes: string[];
  per_class: { class: string; precision: number; recall: number; f1: number }[];
  history: { epoch: number; train_loss: number; train_acc: number; val_loss: number; val_acc: number }[];
  sample_predictions: { image: string; true_label: string; pred_label: string; correct: boolean }[];
}

export interface ModelBenchmarksResponse {
  dataset: { n_classes: number; classes: string[]; img_size: number; n_train: number; n_val: number; n_test: number; note: string };
  cnn: ModelMetrics;
  vit: ModelMetrics;
}

export const fetchModelBenchmarks = () => api.get<ModelBenchmarksResponse>("/academic/cv/model-benchmarks").then((r) => r.data);

export interface ObjectDetectionStatus {
  status: string;
  reason: string;
  what_is_implemented_instead: string;
  reproducible_pipeline_if_undertaken: {
    dataset_schema: Record<string, unknown>;
    training_config: Record<string, unknown>;
    inference_script: string;
  };
}
export const fetchObjectDetectionStatus = () => api.get<ObjectDetectionStatus>("/academic/cv/object-detection/status").then((r) => r.data);
