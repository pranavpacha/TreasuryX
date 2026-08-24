# Computer Vision Pipeline

## Design decision: classical CV, not a pretrained deep detector

Financial chart/report screenshots are dominated by **text and line primitives** (axis labels,
legends, numeric callouts, gridlines) rather than natural-scene objects. A classical OpenCV pipeline
(edge/line/contour detection + OCR) is:

- **More precise for this domain** — a YOLO-style object detector is trained for natural objects,
  not for locating "the number next to the axis label," which is fundamentally a text/geometry task.
- **Instant on a laptop CPU** — no GPU, no multi-hundred-MB model download, satisfying the project's
  "must run on a normal student laptop" constraint (spec section 43).
- **Fully explainable** — every stage output is inspectable in the UI (see below), which matters for
  an auditable Treasury tool more than raw black-box accuracy.

This mirrors the project spec's own guidance: *"If a simpler CV method works better, prefer it."*
A **pretrained** deep detector was therefore deliberately not used for this pipeline specifically.
(A Vision Transformer *was* later written from scratch and trained for the separate CNN-vs-ViT
comparison (see [cv_models.md](cv_models.md)) — but that's a controlled
classification experiment on a small synthetic dataset, not a replacement for this pipeline's
region/OCR extraction, which remains classical CV for the reasons above.)

## Stages (`backend/app/cv_engine/`)

| # | Stage | Function | Technique |
|---|---|---|---|
| 1 | Preprocessing | `preprocessing.py::preprocess` | resize (aspect-preserving, capped 1400px) → grayscale → non-local-means denoise → CLAHE contrast normalization → adaptive Gaussian threshold |
| 2 | Structural / feature processing | `edges.py` | Canny edge detection; probabilistic Hough line transform; largest-bounding-rect contour detection for the chart/table region |
| 3 | OCR | `ocr.py::run_ocr` | Tesseract via `pytesseract` — per-word text, bounding box, and confidence |
| 4 | Chart recognition | `pipeline.py::classify_chart_type` | keyword-scoring classifier over the OCR text → `fx_chart` / `yield_curve` / `report` / `unknown` |
| 5 | Field extraction | `pipeline.py::run_pipeline` | regex-based number/date/instrument-mention extraction (`ocr.py`), then nearest-neighbor pairing of an instrument mention to its closest number by pixel distance |
| 6 | Structured output | `pipeline.py::run_pipeline` return value | `{instrument, metric, value, unit, confidence, source_region}` per field, plus a list of human-readable warnings |

## Honesty / graceful degradation

- If the Tesseract binary isn't installed, `ocr.py::run_ocr` catches the failure and returns
  `available=False` with an explicit warning string — **the rest of the pipeline still runs** and is
  shown in the UI (preprocessing stages, edges, region detection), rather than the whole request
  failing. This is exercised by `test_cv.py` and was observed directly during development on a
  machine without Tesseract initially installed.
- If no fields can be confidently matched, the pipeline falls back to surfacing raw detected numbers
  at reduced confidence, with an explicit "please verify" warning, rather than returning nothing or
  guessing.
- Mean confidence < 0.5 triggers an additional "manual review strongly recommended" warning.
- Every extracted field is editable in the UI **before** it can be committed into the finance engine
  (`POST /api/cv/correct` then `POST /api/cv/commit`) — the pipeline never writes directly into
  Treasury analytics without a human-reviewable step.

## Demonstrating this to a reviewer

The Market Intelligence page renders all 7 intermediate images (original → grayscale → denoised →
normalized → thresholded → edges → detected-region overlay) side by side, plus the raw OCR text and
the structured field table with per-field confidence — see `frontend/src/pages/MarketIntelligence.tsx`.

## Testing

`backend/tests/test_cv.py` generates four synthetic test images (clean, Gaussian-noisy, low
resolution, and a near-blank low-contrast "difficult" case) with no external image files required,
and asserts: preprocessing produces all expected stages, edge/line/region detection runs without
error, chart classification is correct on keyword-bearing text, the end-to-end pipeline never
crashes on any of the four conditions, and corrupt input raises a clear `ValueError` rather than
crashing silently.

## Compare Market Screens and Technical Evidence (deeper syllabus coverage)

This pipeline (Financial Image Intelligence) is the *applied* Treasury use case. SIFT keypoint
matching is also a real product feature — **Compare Market Screens**
(`frontend/src/pages/intelligence/CompareMarketScreens.tsx`) — for visually comparing two
uploaded Treasury screenshots. The rest of the CS4231 syllabus is implemented explicitly and
interactively as **Methodology → Technical Evidence**, since these are evaluation/demonstration
exercises rather than production-critical routing decisions: filter comparison, adjustable edge
detection (Sobel/Laplacian/DoG/LoG/Canny), Harris corner + blob detection, GrabCut segmentation
with real IoU/Dice metrics, dense optical flow, and a from-scratch CNN vs. Vision Transformer
comparison (see [cv_models.md](cv_models.md)) — backed by
`backend/app/cv_engine/{filters_lab,edges_lab,features_lab,sift_lab,segmentation_lab,optical_flow_lab}.py`
and `backend/app/api/academic_cv.py`. See [ACADEMIC_MAPPING.md](../ACADEMIC_MAPPING.md) for the
full syllabus-to-code cross-reference, including what's explicitly out of scope and why.
