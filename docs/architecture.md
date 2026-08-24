# Architecture

## Layers

```
frontend/  React + TypeScript + Vite, dark institutional terminal UI
  src/pages/            one component per major Terminal-Mode nav section (Overview, FxDesk, ...)
  src/pages/cv-lab/      Academic Mode: Computer Vision Lab pages (filters, edges, SIFT, ...)
  src/pages/graphics-lab/ Academic Mode: Computer Graphics Lab pages (raster, transforms, 3D, ...)
  src/charts/           Recharts wrappers (2D line charts)
  src/three/            @react-three/fiber 3D surface plot, Graphics Info panel, custom-shader
                        surface, live-matrix readout
  src/graphics/         pure-function graphics algorithms (raster line/circle, 2D transform
                        matrices, line clipping, color models) — no React/Three.js dependency,
                        independently unit-testable
  src/context/          ModeContext (Terminal/Academic mode toggle, localStorage-persisted)
  src/services/         typed axios clients (api.ts, academicCvApi.ts) — the only place that
                        knows API response shapes
  src/components/       shared Panel/Metric/Badge/Tooltip/Layout primitives, CvLabShared upload
                        components, PixelCanvas raster-grid renderer
  src/hooks/            useApi — small loading/error/reload data-fetching hook

backend/app/
  main.py          FastAPI app, CORS, router registration, lifespan (DB init + seed)
  config.py        pydantic-settings Settings (env-overridable)
  database.py      SQLAlchemy engine/session/Base
  api/             one router per resource (fx, bonds, positions, yield_curve, risk,
                   scenario, cv, market3d, overview, academic_cv) — thin, delegates to
                   finance/, cv_engine/, and data/
  finance/         pure functions: fx.py, bonds.py, risk_metrics.py, scenario_engine.py, regime.py
                   (no DB or HTTP dependency — independently unit-testable)
  cv_engine/       preprocessing.py, edges.py, ocr.py, pipeline.py (the applied Treasury pipeline),
                   plus filters_lab.py, edges_lab.py, sift_lab.py, segmentation_lab.py,
                   features_lab.py, optical_flow_lab.py (Academic Mode CV labs) — all pure
                   OpenCV/Tesseract functions
  cv_engine/models/  dataset.py (synthetic chart-image generator), cnn.py (TinyCNN), vit.py
                     (TinyViT, written from scratch), train.py (trains both, writes real metrics
                     to data/model_results/cnn_vs_vit.json) — torch is a DEV-ONLY dependency,
                     not required at API runtime (results are precomputed and committed)
  risk/aggregator.py  bridges DB positions + MarketDataProvider -> finance/ functions
  data/            provider.py (abstract MarketDataProvider), demo_provider.py (CSV/JSON-backed),
                   generate_demo_data.py (deterministic synthetic data generator),
                   model_results/ (precomputed CNN/ViT training results, committed to the repo)
  models/          one SQLAlchemy model per table (see docs/database.md)
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
- **`cv_engine/` is also framework-free** — `pipeline.py` takes raw image bytes in and returns a
  plain dict out, so it's testable with synthetic images and reusable from any future entry point
  (CLI, batch job) without FastAPI.
- **The frontend never talks to the DB or files directly** — `src/services/api.ts` is the single
  typed boundary, matching the backend's pydantic response schemas.

## Data flow: CV → Finance → 3D (the project's integration story)

1. User uploads an image → `POST /api/cv/extract` → `cv_engine/pipeline.run_pipeline` → stored as a
   `CvExtraction` row + returned to the UI with all intermediate stage images.
2. User reviews/corrects fields in the UI, optionally `POST /api/cv/correct`.
3. User commits a field → `POST /api/cv/commit` → the value is fed into `finance/bonds.py` or
   `finance/fx.py` and the resulting analytics are returned and audit-logged.
4. Positions (whether from CV-informed trades or the seeded demo book) flow through
   `risk/aggregator.py` into `finance/scenario_engine.py`, which the `/api/market3d/*` endpoints call
   over a grid of shocks to build the 3D stress surface data consumed by `frontend/src/three/SurfacePlot.tsx`.
