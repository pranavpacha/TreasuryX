# Assumptions & Simplifications

Every simplification made for this educational build, in one place, with the reasoning.

## Finance

- **Bond day-count**: equal-length coupon periods with a fractional `settle_frac` for
  clean/dirty/accrued pricing, rather than a full Act/Act, Act/360, or 30/360 calendar
  implementation. Chosen because a full day-count/holiday-calendar implementation was judged out of
  scope for the finance concepts being demonstrated (pricing, YTM, duration, convexity, DV01), while
  the simplified version still produces a genuine clean/dirty/accrued split.
- **Duration/Convexity/DV01 valuation date**: assumed on a coupon date (`settle_frac=0`) for the
  Macaulay/Modified Duration/Convexity/DV01 formulas specifically (separate from the more general
  clean/dirty pricing function, which does support `settle_frac>0`). This keeps the formulas in
  their standard textbook form and testable against hand calculations.
- **DV01/Modified Duration/Convexity computed via bump-and-reprice**, not independently-derived
  closed forms — a deliberate choice to guarantee internal consistency with the pricing model (see
  `docs/finance_methodology.md`).
- **VaR/ES**: single reconstructed portfolio-value historical series (FX + bond MTM at each
  historical date, current quantities held fixed), not a full covariance-matrix parametric VaR. This
  is standard "historical simulation" VaR, but note it does not explicitly separate cross-asset
  correlation effects beyond what's implicit in the reconstructed series.
- **Market regime classifier**: fixed-threshold rules (documented in `finance/regime.py`), not a
  trained/validated ML model. Always labeled a "decision-support signal."
- **Curve tilt shocks** pivot at a fixed 5-year point — a simplification for the steepening/flattening
  scenario mechanic, not a full key-rate-duration decomposition.
- **Risk limits** (FX exposure ₹100Cr, bond DV01 ₹2L) are illustrative round numbers for the demo
  book, not derived from any real institution's limit framework.

## Data

- **All market data is synthetic** (`backend/app/data/generate_demo_data.py`): a fixed-seed,
  mean-reverting random walk anchored at plausible round starting levels (documented in that file),
  regenerated deterministically — never claimed to be real historical market data.
- **No live data provider is implemented** in this build; the `MarketDataProvider` abstraction exists
  so one could be added later without touching finance/CV/graphics code.

## Computer Vision

- **Classical CV (OpenCV + Tesseract), not a pretrained deep detector** — see
  `docs/cv_pipeline.md` for the reasoning.
- **Field-to-instrument matching** uses a nearest-pixel-distance heuristic between an OCR'd
  instrument mention and an OCR'd number — approximate by design, always shown with a confidence
  score, and always correctable by the user before being committed to the finance engine.
- **OCR requires the Tesseract binary** to be installed separately from the Python dependencies; the
  rest of the pipeline (preprocessing/edges/regions/classification) runs regardless.

## Graphics

- **No custom GLSL shaders** — built-in Three.js materials (Standard/Basic/Line) were sufficient for
  the required lighting/shading and interaction; this is stated explicitly rather than silently
  omitted.
- **No VR/stereo rendering** — by design, per the project's own "must run on a normal laptop, no VR
  hardware" requirement.

## General

- **No authentication** — single-user local demo. The `users` table mentioned as optional in the
  original spec was not implemented, since there is no multi-user concept in this build.
- **No look-ahead bias**: anywhere historical data feeds a metric (volatility, VaR/ES, regime
  classification, curve-shift comparison), only data at or before the relevant "as of" date is used —
  see `risk/aggregator.py::reconstruct_portfolio_value_history` for the explicit mechanism.
