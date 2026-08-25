# CV Models: CNN vs. Vision Transformer

## What was built

Two small image classifiers, both **written and trained from scratch** (no pretrained weights
downloaded), on the same synthetic 4-class financial-chart dataset:

- `backend/app/cv_engine/models/cnn.py` — `TinyCNN`: 3 conv+pool blocks → FC head (~146K params).
- `backend/app/cv_engine/models/vit.py` — `TinyViT`: patch embedding (8x8 patches on a 64x64
  image) → class token → 3 Transformer encoder layers (multi-head self-attention) → FC head
  (~70K params).
- `backend/app/cv_engine/models/dataset.py` — a **synthetic** dataset generator (`fx_line_chart`,
  `yield_curve_chart`, `bar_chart`, `table_report`, 120 images/class, procedurally drawn with
  randomized color/position/noise via OpenCV).
- `backend/app/cv_engine/models/train.py` — trains both models (18 epochs, Adam, batch size 16,
  CPU), evaluates on a held-out test split, and writes real metrics to
  `backend/app/data/model_results/cnn_vs_vit.json`.

## Why synthetic data

No labeled dataset of real FX/yield/bar/table financial screenshots exists for this project, and
scraping one would be both impractical and legally murky (chart images are typically
copyrighted/ToS-restricted). A procedurally generated dataset with genuine structural variation
(line noise, marker jitter, randomized colors/positions) still produces real, non-fabricated
learned classifiers and honest metrics — it's just explicitly *not* a claim about real-world
chart-recognition accuracy. This is stated in the UI (Model Benchmarks page) every time the
results are shown.

## Why train from scratch instead of downloading pretrained weights

- A pretrained CNN (e.g. ResNet/MobileNet) or ViT checkpoint is 20-300+ MB — heavy for a
  "must run on a normal laptop, works offline" build, and would need to be committed to the repo
  or downloaded on first run.
- Training from scratch keeps every parameter of the comparison (architecture, data, epochs)
  fully under this project's control and fully explainable, which matters more for demonstrating
  the underlying CNN-vs-ViT mechanics than squeezing out maximum accuracy.
- Both models train in well under a minute on a CPU-only laptop (measured: TinyCNN ~12s,
  TinyViT ~24s for 18 epochs over 336 training images), so this was practical to do for real.

## Results (measured, not fabricated — see the committed `cnn_vs_vit.json`)

As of this build: TinyCNN reached 100.0% test accuracy, TinyViT reached 98.6%, both on a 72-image
held-out test split. **Near-ceiling accuracy is expected and not impressive on its own** — the
four synthetic classes are structurally very distinct (continuous lines vs. discrete bars vs.
table gridlines), making this closer to a sanity-check task than a hard benchmark. The value of
this experiment is the controlled architecture comparison (parameter count, training time,
inference latency, and how each model's confusion matrix looks) rather than the absolute accuracy
number.

## Why CNN vs. ViT can differ in practice

CNNs use local convolutional receptive fields with weight sharing — fewer parameters for a given
input size, built-in translation-equivariance, and cheaper inference, favoring edge/laptop
deployment. ViTs treat the image as a sequence of patches attended to globally from the first
layer — this can capture long-range spatial relationships (e.g. an axis label far from its data
point) more directly, at the cost of typically needing more data or an inductive bias substitute
to learn the spatial structure CNNs get "for free" from their architecture. Neither is universally
superior; the right choice depends on data scale, latency budget, and the task's spatial
structure.

## Regenerating the results

```bash
cd backend
pip install -r requirements-dev.txt --extra-index-url https://download.pytorch.org/whl/cpu
python -m app.cv_engine.models.train
```

`torch` is a **dev-only** dependency (see `requirements-dev.txt`) — it is deliberately **not**
in the production `requirements.txt` used by the deployed Docker image, to keep that image small
and within free-tier hosting limits. The API serves the precomputed
`backend/app/data/model_results/cnn_vs_vit.json` regardless of whether torch is installed at
runtime.

## Live per-image inference

`app/cv_engine/models/train.py` also writes the trained weights (`cnn_weights.pt`,
`vit_weights.pt`) to `backend/app/data/model_results/`. `app/cv_engine/models/infer.py` loads
them lazily and, if and only if both torch and the weight files are present, runs live CNN + ViT
classification on every image uploaded to Financial Image Intelligence, surfaced in that page's
**Model Details** panel (`POST /api/cv/extract` response, `model_details` field). This is the
same graceful-degradation pattern used for Tesseract OCR: a local dev environment with torch
installed gets genuine live inference; the deployed production build (no torch) reports
`{"available": false, "reason": "..."}` and points to this precomputed benchmark instead.
Predictions on a real financial screenshot are genuine model output, not fabricated — but given
the synthetic training data, read them as a demonstration of CNN/ViT mechanics rather than a
claim of real-world chart-recognition accuracy.
