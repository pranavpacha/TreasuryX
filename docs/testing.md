# Testing

## Backend — `cd backend && .venv\Scripts\python -m pytest tests/ -v`

74 tests, all passing as of this build:

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
- **`test_cv.py`** (12 tests) — preprocessing produces every expected stage; edge detection finds
  edges on a synthetic square; chart-region and Hough-line detection on a synthetic chart; chart-type
  classification (yield curve / FX / unknown); end-to-end pipeline on clean, Gaussian-noisy,
  low-resolution, and near-blank ("difficult") synthetic images without crashing; corrupt input
  raises `ValueError`.
- **`test_api.py`** (24 tests) — health check; overview demo-flag/disclaimer; FX quotes/history
  (valid + invalid pair → 404); FX trade booking + invalid pair (400) + negative quantity (422);
  bonds list + YTM endpoint + unknown ISIN (404); yield-curve default + compare/classification; risk
  summary structure; scenario run + history; CV extract (bad extension/empty file → 400, valid image
  → 200, corrupt image → 400); market3d yield/vol/stress surfaces; trade blotter.

Uses an isolated SQLite file per test (`tests/conftest.py`, FastAPI `dependency_overrides`) — tests
never touch the developer's working `treasuryx.db`.

## Frontend — `cd frontend && npm run test`

15 tests, all passing as of this build:

- **`Common.test.tsx`** (9 tests) — `fmtNumber`/`fmtInr` formatting (crore/lakh/plain/negative) and
  `toneFor` sign classification.
- **`Overview.test.tsx`** (2 tests) — loading state, then renders disclaimer/FX/risk data from a
  mocked API response; renders an error state on a rejected request.
- **`Scenario.test.tsx`** (2 tests) — clicking a preset shock posts the correct payload and renders
  the audited `SCN-xxxxx` result with its method notes; a custom-shock form submission posts the
  user-entered values.
- **`MarketIntelligence.test.tsx`** (2 tests) — uploading a file renders the pipeline-stage images and
  extracted field inputs; a low-confidence warning from the API is surfaced in the UI.

## What is *not* covered

- No end-to-end (Playwright/Cypress) browser test suite — verification of full page rendering
  (all 9 routes) and the 3D canvas was done manually via an automated browser tool during
  development (console-error-free, correct data loaded per network inspection) rather than committed
  as an automated E2E suite, due to time constraints on this build.
- CV OCR accuracy is not benchmarked against a labeled dataset — the test suite verifies the pipeline
  *runs correctly and degrades gracefully* under varied image conditions, not OCR text accuracy,
  which depends on the (optional, separately-installed) Tesseract binary.
- No load/performance testing.
