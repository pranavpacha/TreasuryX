# Architecture

## Layers

```
frontend/  React + TypeScript + Vite, dark institutional terminal UI
  src/pages/               Workstation pages (Overview, FxDesk, RatesBonds, Risk, Scenario, ...)
  src/pages/intelligence/  Intelligence: CompareMarketScreens (SIFT-based screen comparison)
  src/pages/methodology/   Methodology (documentation): TreasuryMethodology,
                           ComputerVisionMethodology, ComputerGraphicsMethodology, CourseMapping,
                           TechnicalEvidence
  src/pages/cv-lab/        Technical Evidence sub-pages for CV (filters, edges, features,
                           segmentation, optical flow, CNN-vs-ViT benchmarks, object-detection
                           status) -- linked from Technical Evidence, not primary nav
  src/pages/graphics-lab/  Technical Evidence sub-pages for Graphics (raster algorithms, 2D
                           transforms/clipping, transform/camera/lighting concepts, depth buffer,
                           VR/AR concepts) -- same reasoning
  src/pages/MarketIntelligence.tsx  Financial Image Intelligence (the real CV product page)
  src/pages/Market3D.tsx   3D Market (the real Graphics product page)
  src/charts/              Recharts wrappers (2D line charts)
  src/three/               SurfacePlot.tsx (the production 3D renderer: geometry, materials,
                           the shared risk shader, live-matrix callback), GraphicsControls.tsx
                           (Market View/Risk View + Perspective/Orthographic + Graphics Details +
                           Explain Visualization -- used by every 3D Market surface),
                           MatrixReadout.tsx (live 4x4 matrix display)
  src/graphics/            pure-function graphics algorithms (raster line/circle, 2D transform
                           matrices, line clipping, color models) -- no React/Three.js dependency,
                           independently unit-testable; used by the Technical Evidence pages
  src/services/             typed axios clients (api.ts, academicCvApi.ts) -- the only place that
                           knows API response shapes
  src/components/          shared Panel/Metric/Badge/Tooltip/Layout primitives, CvLabShared
                           upload components, PixelCanvas raster-grid renderer
  src/hooks/                useApi -- small loading/error/reload data-fetching hook

backend/app/
  main.py          FastAPI app, CORS, router registration, lifespan (DB init + seed)
  config.py        pydantic-settings Settings (env-overridable)
  database.py      SQLAlchemy engine/session/Base
  api/             one router per resource (fx, bonds, positions, yield_curve, risk,
                   scenario, cv, market3d, overview, academic_cv) -- thin, delegates to
                   finance/, cv_engine/, services/, and data/
  finance/         pure functions: fx.py, bonds.py, risk_metrics.py, scenario_engine.py, regime.py
                   (no DB or HTTP dependency -- independently unit-testable)
  cv_engine/       preprocessing.py, edges.py, ocr.py, pipeline.py (the applied Financial Image
                   Intelligence pipeline), plus filters_lab.py, edges_lab.py, sift_lab.py,
                   segmentation_lab.py, features_lab.py, optical_flow_lab.py (the classical-CV
                   techniques behind Compare Market Screens and the Technical Evidence pages) --
                   all pure OpenCV/Tesseract functions
  cv_engine/models/  dataset.py (synthetic chart-image generator), cnn.py (TinyCNN), vit.py
                     (TinyViT, written from scratch), train.py (trains both, writes real metrics
                     to data/model_results/cnn_vs_vit.json) -- torch is a DEV-ONLY dependency,
                     not required at API runtime (results are precomputed and committed)
  services/        overrides.py (MarketOverride CRUD -- the CV-to-Treasury state-change
                   mechanism) and market_view.py (effective_bonds/effective_fx_quotes: baseline
                   demo data with any active override applied on top) -- see below
  risk/aggregator.py  bridges DB positions + the effective market view -> finance/ functions
  data/            provider.py (abstract MarketDataProvider), demo_provider.py (CSV/JSON-backed),
                   generate_demo_data.py (deterministic synthetic data generator),
                   model_results/ (precomputed CNN/ViT training results, committed to the repo)
  models/          one SQLAlchemy model per table (see docs/database.md), including
                   market_override.py (the CV-correction state)
  schemas/         pydantic request/response models
  seed.py          idempotent startup seeding (bonds, demo positions, market events)
```

## Why this split

- **`finance/` has zero framework dependencies.** Every formula is a plain function taking/returning
  primitives or small dataclasses, so it can be tested in isolation (see `backend/tests/test_*.py`)
  without spinning up a database or HTTP server, and reused identically from the FX router, the bond
  router, the risk aggregator, and the scenario engine.
- **`data/provider.py` is an abstract interface** (`MarketDataProvider`) so a live data source could
  be substituted for `DemoDataProvider` without touching any router, finance function, or frontend
  code — only `app/dependencies.py::get_provider` would change.
- **`services/market_view.py` sits between the provider and everything else.** Routers never read
  `provider.get_bonds()` / `provider.get_all_fx_latest()` directly when they need "the current"
  level — they call `effective_bonds(db, provider)` / `effective_fx_quotes(db, provider)`, which
  apply any active `MarketOverride` on top of the baseline. This is the single mechanism that makes
  a Financial-Image-Intelligence correction visible everywhere (bonds, positions, risk, scenario,
  the 3D stress surface) instead of being a one-off calculation.
- **`cv_engine/` is also framework-free** — `pipeline.py` takes raw image bytes in and returns a
  plain dict out, so it's testable with synthetic images and reusable from any future entry point
  (CLI, batch job) without FastAPI.
- **`three/SurfacePlot.tsx` is the one production 3D renderer**, parameterized by `renderMode`
  ("material" | "shader") and `projectionMode` ("perspective" | "orthographic") rather than having a
  separate demo component for the shader — see `docs/graphics_pipeline.md`.
- **The frontend never talks to the DB or files directly** — `src/services/api.ts` /
  `academicCvApi.ts` are the single typed boundary, matching the backend's pydantic response
  schemas.

## Data flow: CV → Finance → Risk → 3D (the project's central integration)

1. User uploads an image on **Financial Image Intelligence** → `POST /api/cv/extract` →
   `cv_engine/pipeline.run_pipeline` → stored as a `CvExtraction` row + returned to the UI with all
   intermediate stage images.
2. User reviews/edits fields in the UI; clicking **Apply to Treasury** first calls
   `POST /api/cv/correct` (persisting the edited value) then `POST /api/cv/commit`.
3. `commit()` writes a `MarketOverride` row via `services/overrides.py::set_override` and computes
   before/after analytics (price, duration, DV01, affected open positions) using the same
   `finance/bonds.py` / `finance/fx.py` functions used everywhere else — never a duplicated
   calculation.
4. Every subsequent request to `/api/bonds`, `/api/fx/quotes`, `/api/positions/bonds`,
   `/api/risk/summary`, `/api/scenario/run`, and `/api/market3d/stress-surface` goes through
   `services/market_view.py`, so the correction is reflected immediately and consistently.
5. **3D Market**'s `SurfacePlot.tsx` renders whatever the `/api/market3d/*` endpoints return — real
   Treasury data in, real geometry/transform/projection/depth/lighting/shader pipeline out.
   `backend/tests/test_integration_cv_to_treasury.py` exercises this whole chain end to end.
