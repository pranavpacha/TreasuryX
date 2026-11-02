# Testing

## Backend — `cd backend && .venv\Scripts\python -m pytest tests/ -v`

202 tests, all passing as of this build (114 pre-existing across finance/CV/API, plus 88 added
across four new test files for the nine `/api/vision/*` features below):

- **`test_fx.py`** (10 tests) — FX P&L long/short profit/loss, invalid-rate handling, log/simple
  return correctness against manually-computed values, volatility zero-variance and scaling checks.
- **`test_bonds.py`** (16 tests) — par/premium/discount pricing, a hand-computed 2-year annual-coupon
  reference price, invalid-input errors, clean/dirty/accrued relationship, YTM round-trip (price → 
  YTM recovers the original yield), YTM invalid-price error, Macaulay duration ≈ maturity for a
  near-zero coupon, Modified Duration < Macaulay (with the exact `/(1+y/f)` relationship checked),
  positive convexity, DV01 matched against an independent manual bump-and-reprice, and duration
  approximation vs. exact reprice at both small and large yield shocks.
- **`test_risk.py`** (7 tests) — VaR/ES on a known distribution (ES ≥ VaR), linear scaling with
  portfolio value, monotonicity with confidence level, insufficient-data and invalid-confidence
  errors, max-drawdown on a hand-worked example and a monotonic-increase edge case.
- **`test_scenario.py`** (6 tests) — FX long/short shock direction, bond long-position P&L sign for
  yield up/down, combined-scenario total additivity, curve-tilt differential impact on short vs.
  long maturities.
- **`test_cv.py`** (17 tests) — preprocessing produces every expected stage; edge detection finds
  edges on a synthetic square; chart-region and Hough-line detection on a synthetic chart; chart-type
  classification (yield curve / FX / unknown); end-to-end pipeline on clean, Gaussian-noisy,
  low-resolution, and near-blank ("difficult") synthetic images without crashing; corrupt input
  raises `ValueError`; the G-Sec yield-curve OCR regression (no duplicate rows, no OCR-confidence-
  as-value bug, "G-SEC" asset-class text never paired as an instrument); image-quality assessment
  flags a low-res/blurry/low-contrast image and passes a sharp one.
- **`test_api.py`** (25 tests) — health check; overview demo-flag/disclaimer; FX quotes/history
  (valid + invalid pair → 404); FX trade booking + invalid pair (400) + negative quantity (422);
  bonds list + YTM endpoint + unknown ISIN (404); yield-curve default + compare/classification; risk
  summary structure; scenario run + history; CV extract (bad extension/empty file → 400, valid image
  → 200, corrupt image → 400); market3d yield/vol/stress surfaces; trade blotter.
- **`test_market_view.py`** (7 tests) — tenor-string parsing (months/years, rejects non-tenors);
  `find_bond_by_tenor` matches the closest bond within tolerance, matches a short tenor to a
  near-maturity bond, returns `None` (never a best-effort guess) when nothing is close enough,
  excludes already-matured bonds, and never invents an ISIN.

- **`test_academic_cv.py`** (18 tests) — filter comparison produces all variants and actually
  smooths noise; Sobel/Laplacian/DoG/LoG run without error and respond correctly to threshold
  changes; Harris corners and blob detection run on a synthetic rectangle; SIFT self-matching
  recovers a bounded fraction of keypoints and handles blank (no-keypoint) images gracefully;
  segmentation IoU/Dice are exactly 1.0 for identical masks and 0.0 for disjoint masks, and the
  synthetic-ground-truth benchmark produces a valid [0,1] IoU/Dice; optical flow reports near-zero
  magnitude for identical frames and positive magnitude for a known translation.
- **`test_integration_cv_to_treasury.py`** (5 tests) — the core CV → Treasury integration: a
  committed bond-yield correction propagates to `/api/bonds` (price/duration change,
  `is_cv_corrected` flag), to open bond positions and portfolio risk (DV01), and to the 3D
  Portfolio Stress Surface (a non-zero-shock grid point changes because the underlying base yield
  changed — the always-zero zero-shock point is explicitly excluded as a non-discriminating check);
  a committed FX correction propagates to `/api/fx/quotes` and open FX positions; and
  `DELETE /api/cv/overrides` cleanly restores baseline demo data everywhere.

- **`test_vision_core.py`** (32 tests) — synthetic-dataset integrity (disjoint template splits,
  deterministic rendering, valid annotations for all 8 kinds); the image-quality analyzer detects
  injected blur/noise/low-contrast/skew/90°-rotation and that enhancement is re-measured, not
  assumed; chart digitization recovers every plotted yield-curve tenor within 2 pixels of
  calibrated value and FX-series points within their stated uncertainty >90% of the time, and
  returns **no** numeric value when OCR/calibration is unavailable; screenshot comparison tells a
  genuine value change (`10Y 6.85 -> 7.02`) apart from a pure pixel translation (`layout_change`,
  zero value changes); visual anomaly detection finds every injected gap/spike and raises nothing
  on a clean chart; optical flow recovers a known pixel translation via Lucas-Kanade.
- **`test_vision_video.py`** (9 tests) — the frame-selection policy keeps changed+settled frames
  and drops redundant ones, waits for a still-moving screen to settle, and the budget pruner keeps
  the highest-scoring frames plus first/last; the simulated demo video's detected event timeline
  (value changes, scene change, chart motion) matches its scripted ground truth, in chronological
  order; the background job store reports progress, cancels cooperatively, fails gracefully on an
  exception, and stays bounded.
- **`test_vision_api.py`** (21 tests) — upload validation (bad extension/empty/corrupt/oversized)
  across every endpoint; each feature endpoint's shape; and, most importantly, the **approval
  flow**: creating a proposal changes zero Treasury state; approval propagates to `/api/bonds`
  and `/api/fx/quotes` with correct before/after analytics; an analyst can correct the value before
  approving; a flagged (implausible/large-jump) value requires explicit confirmation and is
  rejected without it; invalid/unmappable values are never staged; rejecting leaves state
  untouched; a video job creates events but never touches market data; the existing G-Sec OCR
  regression and FX-screenshot extraction still work end to end into a staged proposal.
- **`test_vision_models.py`** (15 tests) + **`test_vision_models_api.py`** (11 tests) — the 8-class
  CNN/ViT classifier predicts a valid class with real probabilities/timing and beats chance on
  held-out synthetic templates, with real measured metrics in its model card; the Siamese encoder
  scores a same-template pair higher than a different-kind pair and a self-comparison as
  `near_duplicate`; the similarity index add/search/delete lifecycle, and that a
  Financial-Image-Intelligence upload is auto-indexed; zero-shot search ranks a matching document
  type above a mismatched one via the fallback backend and reports `clip_ran: false` honestly when
  CLIP isn't installed; every model-dependent test **skips** (not fails) when the trained ONNX
  files aren't present, matching the project's own graceful-degradation pattern.

Uses an isolated SQLite file per test (`tests/conftest.py`, FastAPI `dependency_overrides`) — tests
never touch the developer's working `treasuryx.db`. The CNN/ViT training scripts
(`app/cv_engine/models/train.py`, `app/cv_engine/vision/train.py`) are exercised manually during
development (not in the pytest suite, since they require the dev-only `torch`/`onnx` dependencies
and take minutes) — see [cv_models.md](cv_models.md) and [vision_features.md](vision_features.md).

## Frontend — `cd frontend && npm run test`

52 tests, all passing as of this build:

- **`Common.test.tsx`** (9 tests) — `fmtNumber`/`fmtInr` formatting (crore/lakh/plain/negative) and
  `toneFor` sign classification.
- **`Overview.test.tsx`** (2 tests) — loading state, then renders disclaimer/FX/risk data from a
  mocked API response; renders an error state on a rejected request.
- **`Scenario.test.tsx`** (2 tests) — clicking a preset shock posts the correct payload and renders
  the audited `SCN-xxxxx` result with its method notes; a custom-shock form submission posts the
  user-entered values.
- **`MarketIntelligence.test.tsx`** (5 tests) — extracted fields render with pipeline stages hidden
  behind "Processing Details" by default; the low-confidence warning banner surfaces; clicking
  "Show" reveals the stage images; **editing a value and clicking "Apply to Treasury" calls
  `/cv/correct` with the edited value BEFORE calling `/cv/commit`** (a regression test for a real
  bug caught during development — the correction was previously never persisted before commit) and
  renders the "Portfolio updated" confirmation; "How Detected?" reveals the technical trace.
- **`rasterAlgorithms.test.ts`** (8 tests) — DDA/Bresenham produce correct horizontal, diagonal, and
  steep-line pixel sequences with no gaps; Bresenham matches DDA on a horizontal line; Midpoint
  Circle points all fall within tolerance of the true radius and are symmetric across all 4 quadrants.
- **`transform2d.test.ts`** (12 tests) — identity/translation/rotation/scaling/reflection/shear
  matrices produce mathematically correct point transforms (e.g. rotating (1,0) by 90° gives (0,1));
  `composeTransforms` demonstrably applies transforms in the stated order (translate-then-rotate
  differs from rotate-then-translate, verified numerically).
- **`clipping.test.ts`** (7 tests) — Cohen-Sutherland and Liang-Barsky both trivially accept
  fully-inside lines, reject fully-outside lines, correctly clip a boundary-crossing line to the
  window edge, and agree with each other on the same input.
- **`colorModels.test.ts`** (7 tests) — RGB→CMY→RGB and RGB→HSV→RGB round-trips recover the original
  color; known reference colors (pure red/green, white, black, gray) map to their expected values.

## What is *not* covered

- No end-to-end (Playwright/Cypress) browser test suite — verification of full page rendering
  (all 25+ routes, including the 3D Market page's Market View/Risk View toggle and every
  Methodology/Technical Evidence page) was done manually via an automated browser tool during
  development (console-error-free, correct data loaded per network inspection, matrix/algorithm
  output spot-checked by hand) rather than committed as an automated E2E suite, due to time
  constraints on this build. Note: the 3D canvases' actual pixel dimensions could not be visually
  screenshotted in that tool's headless testing pane (its own tooling reports frames aren't
  compositing when the pane isn't displayed) — rendering was confirmed error-free and
  data-correct, but a full visual pixel check is worth doing once in a normal browser.
- CV OCR accuracy is not benchmarked against a labeled dataset — the test suite verifies the pipeline
  *runs correctly and degrades gracefully* under varied image conditions, not OCR text accuracy,
  which depends on the (optional, separately-installed) Tesseract binary.
- CNN/ViT accuracy is measured on synthetic data only (see [cv_models.md](cv_models.md)) — not
  covered by an automated regression test since it requires the dev-only `torch` dependency.
- The nine new `/api/vision/*` frontend pages (`frontend/src/pages/intelligence/*`,
  `frontend/src/pages/models/DocumentClassifier.tsx`) have no dedicated Vitest component tests —
  coverage comes from the comprehensive backend API test suite above (every endpoint's valid/
  invalid/unavailable paths) plus manual in-browser verification of each page during development
  (chart digitization, the stage→approve→propagate-to-Rates&Bonds flow, zero-shot search with the
  CLIP-unavailable fallback, and the Siamese similarity index all exercised live against the
  running backend). This mirrors the existing gap noted above for full page-rendering E2E coverage.
- No load/performance testing.
