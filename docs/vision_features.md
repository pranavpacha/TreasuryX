# Computer Vision Intelligence Features (beyond Financial Image Intelligence)

This documents the nine CV capabilities under `/api/vision/*` and the **Intelligence** /
**Vision Models** nav groups, added on top of the original Financial Image Intelligence /
Compare Market Screens / CNN-vs-ViT-4-class pipeline (still present and unchanged — see
[docs/cv_pipeline.md](cv_pipeline.md) and [docs/cv_models.md](cv_models.md)). Every feature below
is real code that runs against an uploaded image; none is a mockup. What is genuinely trained vs.
classical vs. a documented fallback is stated per feature, matching the project's no-fabrication
rule.

## Shared infrastructure

- **Synthetic dataset generator** (`backend/app/cv_engine/vision/synth.py`): procedurally renders
  8 financial-screenshot kinds (yield curve, FX line chart, candlestick chart, bond table, market
  report, risk dashboard, portfolio chart, financial statement) at 30 templates each, with EXACT
  ground truth (chart values, tick positions) because the renderer places every pixel. Splits are
  made **by template** (train 0-19 / val 20-24 / test 25-29) and only degraded (noise/blur/JPEG)
  per *variant*, so a test-split evaluation never sees a variant of a training template. This is
  what every trained-model metric below is measured on — **synthetic, not real screenshots**.
- **Background jobs** (`backend/app/cv_engine/vision/jobs.py`): a small in-process thread-pool job
  store with progress reporting and cooperative cancellation, used by Video Intelligence. Not a
  distributed queue (no Celery/Redis) — sized for one instance.
- **Analyst review** (`backend/app/models/vision.py`, `backend/app/api/vision_review.py`):
  `VisionProposal` rows stage a CV-read market value; nothing changes in Treasury until an analyst
  clicks Approve, which calls `backend/app/services/commit.py::apply_market_value` — the exact
  same function the original Financial Image Intelligence "Apply to Treasury" commit uses. A value
  outside a plausibility band requires a second explicit confirmation. `VisionEvent` rows do the
  same for observations (video/anomaly findings) that don't carry a value to approve.

## 1. Chart Digitization (`/intelligence/chart-digitization`, `POST /api/vision/digitize`)

Classical CV, no trained model. Pipeline: background-color-relative axis/plot-rectangle detection
(morphological line opening) → HSV-saturation curve segmentation (one mask per plotted colour,
legend swatches rejected by connected-component size) → marker detection (morphological opening)
for point-series (yield curves) vs. dense-column sampling for continuous series (FX charts) →
Tesseract OCR of the y-axis tick labels, snapped to detected tick marks, least-squares linear fit
for pixel→value calibration (a decimal-point OCR drop is detected and corrected only when it makes
all tick labels exactly linear) → per-point uncertainty from localisation error + calibration
residual in quadrature. A chart is also screened for "filled shapes" (bars/candles/pie) and
**rejected** rather than mis-digitized. **No numeric value is ever returned without a y-axis
calibration** — without one, only normalised plot coordinates come back, and the response says so.
Manual two-point calibration is available for charts with no numeric axis. Measured on held-out
synthetic templates (`tests/test_vision_core.py`): every plotted tenor on a yield curve is
recovered and within 2 pixels' worth of calibrated value; FX-series values fall within their
stated uncertainty for >90% of points.

## 4. Screenshot Comparison (upgrades `/intelligence/compare-screens`, `POST /api/vision/compare`)

Replaces the previous bare-SIFT-similarity-score demo with a real comparison: SIFT keypoints +
Lowe ratio test + RANSAC homography registers screen B onto screen A; a from-scratch Gaussian-
window SSIM implementation plus absolute pixel difference locate changed regions; each region is
OCR'd in both frames and typed (`value_change` / `label_change` / `chart_line_change` /
`visual_change`) by whether its numbers differ. Separately, the existing OCR field-extraction
pipeline runs on both full screenshots and values are diffed **by instrument label**, not by pixel
position — so a layout shift (a re-scaled window, a scrolled page) is reported as `layout_change`
and never confused with an actual `value_change`, and vice versa (`tests/test_vision_core.py::
test_compare_separates_value_change_from_layout_shift`). Matched value changes can be staged to
Treasury through the same approval flow as Chart Digitization.

## 5. Image Quality Analyzer (`/intelligence/image-quality`, `POST /api/vision/quality`)

Classical, measured (not fabricated) metrics: resolution, Laplacian-variance blur, Immerkaer
fast-noise-sigma estimation, contrast (std-dev), skew (projection-profile search over ±12°), 90°
rotation (row/column ink-profile variance ratio), JPEG 8×8 blockiness (boundary vs. interior
gradient ratio), uneven illumination (morphological background spread), and — when OCR is
available — median character height and Tesseract word confidence. Each check has an `ok` /
`warn` / `poor` status and a documented heuristic threshold. Recommended preprocessing operations
(deskew, upscale, denoise, deblock, flatten illumination, CLAHE, sharpen) are then actually
**applied**, and the "after" image is **re-measured**, never assumed to have worked.

## 6. Visual Anomaly Detection (`/intelligence/anomaly-detection`, `POST /api/vision/anomaly`)

Runs Chart Digitization internally and looks for: gaps (stretches of the plotted line with no
curve pixels), spikes (an excursion, detected at two window scales with MAD-robust thresholds,
that reverts), discontinuities (a level shift that doesn't revert), and OCR value flags
(implausible or low-confidence extracted numbers). **Every result carries the disclaimer that a
visual anomaly is not a confirmed financial anomaly** — a real market move, a chart-rendering
artefact, and a plotting bug look identical to a pixel-level detector, so findings go to analyst
review (as `VisionEvent` rows), never auto-applied. Verified against the synthetic generator's
*injected* gap/spike/jump ground truth.

## 7. Optical Flow (`/intelligence/optical-flow`, `POST /api/vision/flow`)

Dense Farneback optical flow (whole-frame motion field) + pyramidal Lucas-Kanade tracking on
Shi-Tomasi corners with a forward/backward consistency check, run across every consecutive pair in
a 2–10 frame upload. A known synthetic translation is recovered to within ~1px
(`tests/test_vision_core.py::test_lucas_kanade_recovers_known_translation`). The response states
explicitly that flow measures **visual movement only** and does not by itself establish market
direction (an axis rescale or a scroll produces motion too). Also powers the chart-line
vertical-shift measurement used by Video Intelligence's `chart_motion` events.

## 8. Video Intelligence (`/intelligence/video`, `POST /api/vision/video`, `/video/demo`)

Reads a video with `cv2.VideoCapture`, samples at a target rate, and — this is the "intelligent
frame selection" feature — a **threshold-based policy** (`FrameSelector` in
`backend/app/cv_engine/vision/video.py`; explicitly **not** reinforcement learning, labelled as
such in the API response) keeps a sampled frame only if it differs enough from the last *kept*
frame (so OCR isn't re-run on near-static video) **and** has settled relative to the previous
sample (so a half-rendered transition frame is skipped), then prunes to a frame budget keeping the
highest-scoring frames plus the first/last. Each kept frame gets axis/table-rule content detection
and the existing OCR extraction pipeline; values are tracked per instrument across frames and
turned into a chronological event timeline (`value_change`, `scene_change`, `chart_motion`,
`instrument_appeared/disappeared`). Runs as a cancellable background job
(`GET /api/vision/jobs/{id}`, `DELETE` to cancel) with progress reporting. A built-in demo mode
(`/video/demo`) generates a short **simulated** market-terminal clip server-side — scripted,
labelled-synthetic values, not a real recording — so the feature can be tried with no upload; its
detected timeline is checked against the script in `tests/test_vision_video.py`.

## 9. CNN vs. Vision Transformer — 8-Class Document Classifier (`/vision-models/cnn-vs-vit`, `POST /api/vision/classify`)

A **second**, separate CNN/ViT pair from the original 4-class chart-type classifier at Methodology
→ Technical Evidence (kept as-is — see [docs/cv_models.md](cv_models.md)): this one classifies a
screenshot into the 8 document kinds above, trained from scratch
(`backend/app/cv_engine/vision/nets.py` — `ClassifierCNN`, and `ClassifierViT`, a from-scratch
Vision Transformer with patch embedding, learned position embeddings and multi-head self-attention
— not a pretrained download) on the synthetic dataset, and served in production via **ONNX +
OpenCV's `cv2.dnn` runner** rather than live torch inference, so the deployed backend needs no
torch at runtime (see "Model serving" below). Training writes a model card with real measured
confusion matrices, precision/recall/F1 per class, and held-out test accuracy — see
`backend/app/data/model_results/vision/classifier_{cnn,vit}_card.json` and the Model Evaluation
panel on the page.

## 10. Siamese Network Similarity (`/intelligence/similarity-search`, `POST /api/vision/similarity/compare`, `/api/vision/index*`)

A from-scratch `Encoder` (`backend/app/cv_engine/vision/nets.py`) trained with a **contrastive
loss** (`backend/app/cv_engine/vision/train.py::train_siamese`) on pairs sampled 50% positive
(same template, different variant), 30% hard-negative (same document kind, different template),
20% easy-negative (different kind) — producing a 64-d L2-normalised embedding where cosine
similarity is the similarity score. Thresholds (`same_template` / `same_kind` /
`near_duplicate`) are picked on the validation split and recorded in the model card, not
hand-tuned constants. Pairwise comparison additionally requires SSIM confirmation before calling
two images a near-duplicate — a learned score alone never makes that claim. A persisted
**similarity index** (`VisionIndexItem`) stores one embedding + small thumbnail per screenshot;
every upload to Financial Image Intelligence is auto-indexed, so Similarity Search can find
previously uploaded reports with a similar layout. This is document/chart-layout similarity, not
face recognition.

## 11. Zero-Shot Text Search (`/intelligence/zero-shot-search`, `POST /api/vision/search/zero-shot`)

Two backends, and the response **always states which one ran**:
- **CLIP** (`openai/clip-vit-base-patch32` via `transformers`), used only if `transformers`+`torch`
  are importable and the weights are already cached locally (or
  `TREASURYX_ALLOW_MODEL_DOWNLOAD=1` is set to fetch them once, ~600 MB) — not installed in the
  deployed backend. Scores are CLIP image/text cosine similarities, explicitly labelled as
  semantic-similarity scores, not calibrated probabilities.
- **Fallback keyword heuristic** (always available): matches query words against a per-document-
  type synonym list, weighted by the feature-9 classifier's own probability for that type, plus
  OCR word overlap with the candidate image. This is **not CLIP and not semantic** — the response
  says so and states its specific limitation (it cannot judge a visual property like
  "steepening"). A synthetic reference gallery (held-out test templates, one per document kind) is
  always offered so the page has something to search without an upload.

## Model serving (why no torch at runtime)

Every trained model (features 9 and 10) is exported to ONNX at training time
(`backend/app/cv_engine/vision/train.py::export_onnx`) with a parity check against the live
PyTorch output (`onnx_cv2_ok` / `onnx_parity_max_abs_diff` in the model card), then served by
`backend/app/cv_engine/vision/runtime.py` through OpenCV's `cv2.dnn.readNetFromONNX` — the same
`opencv-python-headless` dependency the rest of the app already requires, with no new production
dependency. `torch` and `onnx` stay dev-only (`requirements-dev.txt`), used only to train and
export. If a `.onnx` file is missing or fails to load, `runtime.model_status()` reports why and
every endpoint returns a `503` with that reason rather than silently falling back to something
fabricated.

## Regenerating the trained models

```bash
cd backend
pip install -r requirements-dev.txt --extra-index-url https://download.pytorch.org/whl/cpu
python -m app.cv_engine.vision.train              # both classifiers + Siamese encoder
python -m app.cv_engine.vision.train classifiers  # just the CNN/ViT classifier
python -m app.cv_engine.vision.train siamese      # just the Siamese encoder
```

Writes `.pt` (checkpoint), `.onnx` (served) and `_card.json` (model card) to
`backend/app/data/model_results/vision/`, all committed to the repo so the deployed backend serves
them without needing to train on first boot. Everything is seeded (`torch.manual_seed(42)`); the
dataset cache (`backend/.cache/vision_dataset.npz`) is git-ignored and rebuilt on demand.

## What was deliberately not built

- **Object detection, segmentation, document-region understanding, few-shot recognition,
  self-supervised learning, an edge-performance dashboard** — all were in an earlier, larger scope
  for this feature set and were cut to keep the shipped set of 9 genuinely complete and tested
  rather than partially built. Nothing in the UI or API claims these exist.
- Real-time video (webcam) processing — Video Intelligence works on an uploaded/generated file,
  not a live stream.
- A production CLIP deployment — the free-tier backend does not install `transformers`/`torch`, so
  Zero-Shot Search always runs the fallback there (and says so).
