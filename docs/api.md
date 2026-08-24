# API Reference (summary)

Full interactive OpenAPI docs: `http://127.0.0.1:8000/docs` (or `/redoc`) while the backend is
running. Base path for every route below is `/api`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness/config check |
| GET | `/overview` | Aggregated dashboard payload (FX/curve snapshot, risk summary, market events) |
| GET | `/fx/quotes` | Latest demo FX quotes for all supported pairs, with spread/return/vol |
| GET | `/fx/history/{pair}` | Historical daily rates for one pair |
| GET | `/fx/positions` | Open FX positions with live MTM P&L |
| POST | `/fx/trade` | Book a **simulated** FX spot trade (creates a `Position` + `Trade`) |
| GET | `/bonds` | All G-Secs with current yield, clean price, duration, convexity, DV01 |
| GET | `/bonds/{isin}/history` | Historical yield/price series for one bond |
| GET | `/bonds/{isin}/ytm?price=` | Solve YTM for a given price |
| GET | `/positions/bonds` | Open bond positions with MTM |
| POST | `/positions/bonds/trade` | Book a **simulated** bond trade |
| GET | `/positions/blotter` | Full simulated trade blotter |
| GET | `/yield-curve?as_of=` | Yield curve for a date (defaults to latest) |
| GET | `/yield-curve/dates` | All available curve dates |
| GET | `/yield-curve/compare?date1=&date2=` | Curve shift table + steepening/flattening classification |
| GET | `/risk/summary?confidence=&lookback_days=` | VaR/ES, DV01, exposures, drawdown, regime, limit utilization |
| POST | `/scenario/run` | Run a deterministic FX/yield shock scenario, persisted for audit |
| GET | `/scenario/history` | Past scenario runs |
| POST | `/cv/extract` | Upload an image, run the CV pipeline, return stage images + extracted fields |
| POST | `/cv/correct` | Save human-corrected field values for an extraction |
| POST | `/cv/commit` | Apply a (corrected) extracted value into the Treasury engine — writes a `MarketOverride` (so it's visible everywhere else) and returns before/after price, duration, DV01, and affected open positions |
| GET | `/cv/overrides` | List every active CV-sourced market correction |
| DELETE | `/cv/overrides` | Clear all CV-sourced corrections, restoring baseline demo data everywhere |
| GET | `/market3d/yield-surface?n_dates=` | Yield-curve surface data (tenor × date × yield) |
| GET | `/market3d/fx-vol-surface` | FX volatility surface data (pair × lookback-window × vol) |
| GET | `/market3d/stress-surface?fx_steps=&yield_steps=` | Portfolio P&L stress-surface grid (FX shock × yield shock) |
| POST | `/academic/cv/filters` | Gaussian/median/bilateral/CLAHE filter comparison on an uploaded image |
| POST | `/academic/cv/edges` | Sobel/Laplacian/DoG/LoG/adjustable-Canny edge detection |
| POST | `/academic/cv/features` | Harris corner detection + blob detection |
| POST | `/academic/cv/sift` | SIFT keypoint detection + ratio-test matching between two images |
| POST | `/academic/cv/segmentation` | GrabCut segmentation on an uploaded image |
| GET | `/academic/cv/segmentation/benchmark` | Real IoU/Dice on a synthetic ground-truth dataset |
| POST | `/academic/cv/optical-flow` | Dense Farneback optical flow between two frames (or one + a synthetic shift) |
| GET | `/academic/cv/model-benchmarks` | Precomputed CNN vs. ViT training results (accuracy, confusion matrix, training curves, sample predictions) |
| GET | `/academic/cv/object-detection/status` | Honest `NOT_TRAINED` status + reproducible pipeline spec for deep object detection |

## Error handling conventions

- `400` — invalid input (bad pair/ISIN, non-convergent YTM, bad file type/size, empty file).
- `404` — resource not found (unknown pair/ISIN/date/extraction id).
- `422` — pydantic validation failure (e.g. negative trade quantity).
- Every error response includes a `detail` string explaining what went wrong — never a silent
  fallback to a default/fake value.
