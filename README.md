# TreasuryX — AI-Assisted Treasury Market Intelligence, Risk Analytics and Interactive Financial Visualization Terminal

> **Educational/simulated Treasury analytics platform. No real-money trading. Outputs are for
> academic and demonstration purposes only.** TreasuryX is a student-built project and is **not**
> Bloomberg, Reuters, or any production bank system.

TreasuryX has two modes: **Terminal Mode** (a clean, professional Treasury workstation) and
**Academic Mode** (adds Computer Vision Lab, Computer Graphics Lab, and course-mapping/methodology
pages, for coursework demonstration). Toggle it top-right in the app header.

## 1. Project Overview

TreasuryX is a simplified institutional-style Treasury workstation that integrates FX analytics,
fixed-income/bond analytics, yield-curve analysis, portfolio P&L and market-risk analytics
(VaR/ES/DV01), deterministic scenario/stress testing, a Computer Vision pipeline for extracting
structured data from financial chart/report screenshots, and an interactive 3D market
visualization layer built on Three.js/WebGL.

It is designed to demonstrate genuine, verifiable coverage of two academic subjects
(**Computer Vision** and **Computer Graphics/VR**) inside a coherent, resume-relevant Treasury
Markets Technology project. See [ACADEMIC_MAPPING.md](ACADEMIC_MAPPING.md) for the detailed
subject-by-subject mapping.

## 2. Problem Statement

Treasury dealers and analysts work across fragmented tools: rate feeds, spreadsheets for bond
math, ad-hoc risk calculations, and screenshots of charts/reports shared over chat that have to be
manually re-keyed into models. TreasuryX explores what a lightweight, auditable workstation could
look like that (a) does the standard Treasury math correctly and transparently, and (b) can lift
structured values directly out of a chart screenshot instead of manual re-entry.

## 3. Treasury Use Case

A hypothetical Treasury dealer/analyst can: inspect FX and bond market data, hold simulated
positions, see mark-to-market P&L, run historical VaR/Expected Shortfall, apply yield/FX shocks in
a deterministic scenario engine (with a full audit trail), upload a chart screenshot and have the
CV pipeline extract instrument/value pairs (with human correction before committing), and explore
yield-curve, FX-volatility, and stress surfaces in 3D.

## 4. Features

- **Overview**: portfolio P&L, VaR, DV01, exposures, risk-limit utilization, market regime, market events.
- **FX Desk**: live-from-demo quotes, spread/return/volatility, simulated spot trades, MTM P&L.
- **Rates & Bonds**: G-Sec analytics — clean/dirty price, YTM, Macaulay/Modified duration, convexity, DV01.
- **Yield Curve**: 1M–30Y tenors, date comparison, curve-shift table, steepening/flattening classification.
- **Risk**: historical VaR/ES (95%/99%, configurable lookback), drawdown, exposures, limit utilization.
- **Scenario / Stress Testing**: preset and custom FX/yield shocks, exact repricing, full audit trail (`SCN-xxxxx`).
- **Trade Blotter**: every simulated trade, clearly labeled SIMULATED.
- **Market Intelligence (CV)**: image upload → preprocessing → edge/region detection → OCR →
  chart classification → structured extraction → human correction → commit into the finance engine.
- **3D Market**: yield-curve surface, FX volatility surface, portfolio stress (P&L) surface — real
  Three.js geometry driven entirely by finance-engine output.
- **Computer Vision Lab** (Academic Mode): filter comparison, adjustable edge detection
  (Sobel/Laplacian/DoG/LoG/Canny), Harris corner + blob detection, SIFT keypoint matching, GrabCut
  segmentation with real IoU/Dice metrics, dense optical flow, and a from-scratch CNN vs. Vision
  Transformer comparison with real accuracy/precision/recall/F1/confusion-matrix results.
- **Computer Graphics Lab** (Academic Mode): DDA/Bresenham/Midpoint-Circle raster algorithms,
  homogeneous-coordinate 2D transforms with live matrices, Cohen-Sutherland & Liang-Barsky line
  clipping, live Model/View/Projection matrices, perspective-vs-orthographic comparison, a
  from-scratch software Z-buffer, and a hand-written GLSL shader driving real yield-curve data.
- **Course Mapping**: an in-app page cross-referencing every implemented (and explicitly
  not-implemented) topic against the actual CS4231/CS4104 course syllabi.

## 5. Architecture

```
frontend (React + TS + Vite)
        |
        v
REST API (FastAPI)
        |
   +----+----------------+------------------+
   |                     |                  |
Finance Engine        CV Engine          Data Layer (SQLite + DemoDataProvider)
(fx / bonds / risk /   (OpenCV + Tesseract
 scenario / regime)     OCR pipeline)
   |
   v
Risk Aggregator -> Scenario Engine -> 3D Visualization Data -> Three.js (frontend)
```

See [docs/architecture.md](docs/architecture.md) for the full module layout.

## 6. Finance Methodology (summary)

All formulas are implemented from first principles (no third-party pricing library), documented in
code, and cross-checked with independent manual calculations in the test suite. See
[docs/finance_methodology.md](docs/finance_methodology.md) and [docs/assumptions.md](docs/assumptions.md)
for full detail, including every simplification made and why. Highlights:

- **FX P&L**: `(current_rate - entry_rate) * signed_notional_base`, quote convention BASE/QUOTE.
- **Volatility**: annualized std-dev of daily log returns (`sqrt(252)` scaling), clearly separated
  from daily volatility everywhere it's shown.
- **Bond pricing**: standard discrete-coupon PV formula; clean/dirty price via a fractional-period
  settlement convention (an explicitly documented educational day-count simplification).
- **YTM**: Brent's method (`scipy.optimize.brentq`) with a wide bracket and explicit non-convergence errors.
- **Duration / Convexity / DV01**: Macaulay duration analytically; Modified Duration, Convexity and
  DV01 via **numerical bump-and-reprice** against the same pricing function, guaranteeing internal
  consistency (verified against the closed-form Modified Duration relationship in tests).
- **VaR / Expected Shortfall**: 1-day **historical** VaR/ES, no look-ahead (only already-observed
  daily returns are used), selectable 95%/99% confidence and lookback window.
- **Scenario engine**: fully deterministic — no randomness, no AI-generated numbers. Every run is
  persisted with its inputs, method, and outputs for audit (`GET /api/scenario/history`).
- **Market regime**: a documented **rule-based** classifier (not a trained model) — explicitly
  labeled a decision-support signal, not a prediction.

## 7. Computer Vision (summary)

The applied Treasury pipeline is classical OpenCV (resize → grayscale → denoise → CLAHE normalize
→ adaptive threshold → Canny edges → Hough lines / contour region detection) feeding Tesseract
OCR, then regex-based financial field extraction and a chart-type classifier — a pretrained deep
detector was deliberately not used here (see [docs/cv_pipeline.md](docs/cv_pipeline.md)). OCR
degrades gracefully if Tesseract isn't installed; every other stage still runs and is shown in the
UI. Extracted values are manually correctable before being committed into the finance engine.

Academic Mode adds a full **Computer Vision Lab** covering the rest of the CS4231 syllabus: filter
comparison, adjustable edge detection, corner/blob detection, SIFT matching, GrabCut segmentation
(with real IoU/Dice benchmarks), optical flow, and a CNN vs. Vision Transformer comparison — both
models written and trained **from scratch** on a small synthetic dataset, with real (not
fabricated) metrics. See [docs/cv_models.md](docs/cv_models.md). Deep object detection (Fast
R-CNN/YOLO) is honestly marked `NOT_TRAINED` with the reason and a reproducible pipeline spec,
rather than faked — see the Object Detection lab.

## 8. Computer Graphics (summary)

The integrated 3D Market views are real Three.js/WebGL scenes (via `@react-three/fiber`), not a
canned 3D-chart library: custom `BufferGeometry` grid meshes built directly from finance-engine
data, vertex-colored, lit by ambient + two directional lights, perspective camera with
`OrbitControls`, and raycast-driven hover tooltips.

Academic Mode adds a full **Computer Graphics Lab** covering the CS4104 syllabus's lower-level
algorithms explicitly: DDA/Bresenham/Midpoint-Circle rasterization (pixel-by-pixel, not
canvas-native), homogeneous-coordinate 2D transforms with live matrices, Cohen-Sutherland &
Liang-Barsky line clipping, live Model/View/Projection matrices read directly from Three.js,
perspective-vs-orthographic comparison, ambient/diffuse/specular lighting, a from-scratch software
Z-buffer, and a hand-written GLSL vertex+fragment shader (`ShaderYieldSurface.tsx`) driving real
yield-curve data. VR/AR/XR syllabus topics are documented conceptually only — no VR hardware is
used, per the project's laptop-only design. See
[docs/graphics_pipeline.md](docs/graphics_pipeline.md).

## 9. Data Sources

TreasuryX ships with a `DemoDataProvider` (`backend/app/data/demo_provider.py`) that serves
**clearly labeled DEMO/SIMULATED** FX, yield-curve, and bond data generated by a fixed-seed,
mean-reverting synthetic random walk (`backend/app/data/generate_demo_data.py`) — the app runs
fully offline. The `MarketDataProvider` abstraction (`backend/app/data/provider.py`) allows a real
provider to be substituted later without touching the rest of the app; **no live-data provider is
implemented in this build**, and every UI surface carries a "DEMO / SIMULATED DATA" badge.

## 10. Database Schema

SQLite (via SQLAlchemy ORM) with tables: `bonds`, `fx_quotes` (cache, live-provider-ready),
`yield_curve_points` (cache), `positions`, `trades`, `pnl_snapshots`, `risk_metrics`, `scenarios`,
`cv_extractions`, `market_events`, `audit_logs`. See [docs/database.md](docs/database.md). Schema is
plain SQLAlchemy models with no SQLite-specific types, so swapping `TREASURYX_DATABASE_URL` to a
Postgres DSN is the only change needed to migrate.

## 11. API Documentation

Interactive OpenAPI docs are served at `http://127.0.0.1:8000/docs` when the backend is running.
See [docs/api.md](docs/api.md) for a written summary of every endpoint.

## 12. Setup

### Prerequisites
- Python 3.11+ (developed on 3.12)
- Node.js 18+ (developed on 22)
- (Optional, for OCR) [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) — on Windows,
  `winget install --id UB-Mannheim.TesseractOCR`. Without it, the CV pipeline still runs every other
  stage and shows a clear warning instead of OCR text.
- (Optional, only to *regenerate* the CNN/ViT model-benchmark results) `torch` — see
  [docs/cv_models.md](docs/cv_models.md). Not required to run the app; precomputed results are
  already committed at `backend/app/data/model_results/cnn_vs_vit.json`.

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python -m app.data.generate_demo_data   # regenerate demo data (already included in the repo)
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`.

### Docker
```bash
docker compose up --build
```
Frontend on `http://localhost:5173`, backend on `http://localhost:8000`. See
[Section 35 / docker-compose.yml](docker-compose.yml). **Note**: the CV container does not install
the Tesseract binary by default (kept lean); see `backend/Dockerfile` comments to add it.

## 13. Demo Mode

TreasuryX **only ships with demo mode** in this build (`TREASURYX_DATA_MODE=demo`). It requires no
internet access and no API keys. All demo data is regenerated deterministically by
`backend/app/data/generate_demo_data.py` (fixed random seed) and is labeled DEMO/SIMULATED
throughout the UI and API responses (`is_demo: true` fields).

## 14. Screenshots

Not included in this repository snapshot — run the app locally (Section 12) and follow
[DEMO_SCRIPT.md](DEMO_SCRIPT.md) to reproduce every screen.

## 15. Testing

- **Backend**: `cd backend && .venv\Scripts\python -m pytest tests/ -v` — 92 tests covering finance
  formulas (FX, bonds, YTM, duration/convexity/DV01, VaR/ES, scenario engine), the CV pipeline
  (synthetic clean/noisy/low-resolution/low-contrast images), the Academic Mode CV labs
  (filters, edges, SIFT, segmentation, corners/blobs, optical flow), and the API (valid/invalid
  inputs, error responses, end-to-end flows). All 92 pass as of this build.
- **Frontend**: `cd frontend && npm run test` — Vitest + React Testing Library, 49 tests covering
  formatting utilities, page rendering, the scenario-submission flow, the CV upload workflow, and
  the graphics-lab algorithms (raster line/circle drawing, 2D transform matrices, line clipping,
  color-model conversions). All 49 pass as of this build.
- See [docs/testing.md](docs/testing.md) for what is and isn't covered.

## 16. Limitations

- Demo data only — no live market-data provider is wired up (the abstraction exists; see Section 9).
- Bond pricing uses an equal-period, fractional-settlement day-count simplification, not a full
  Act/Act or 30/360 calendar implementation — documented in `docs/assumptions.md`.
- Market regime classification is rule-based, not a validated ML model, and is explicitly a
  decision-support signal, not a forecast.
- CV field-to-instrument matching (nearest-OCR-word heuristic) is approximate by design — the UI
  always shows a confidence score and lets the user correct values before committing them.
- OCR requires the Tesseract binary to be installed separately; without it, the rest of the CV
  pipeline (preprocessing, edges, region detection, chart classification) still runs.
- No authentication/authorization layer — this is a single-user local demo, not a multi-tenant system.
- CNN/ViT are trained on a small synthetic dataset; deep object detectors (Fast R-CNN/YOLO) and
  a trained segmentation network (U-Net) are explicitly not trained — see
  [docs/cv_models.md](docs/cv_models.md) and [ACADEMIC_MAPPING.md](ACADEMIC_MAPPING.md).
- No VR/AR hardware is used anywhere; the syllabus's VR/AR/XR modules are documented conceptually
  only. No Unity integration (separate desktop engine, outside this web app's stack).
- See [docs/assumptions.md](docs/assumptions.md) for the complete list.

## 17. Future Work

- Wire a real (delayed) market-data provider behind the existing `MarketDataProvider` interface.
- Portfolio-level (covariance-aware) VaR instead of a single reconstructed-value historical series.
- A labeled financial-chart dataset large enough to justify training a real object detector or
  segmentation network, to replace the current classical-CV / synthetic-data approach.
- WebSocket-based live quote streaming into the FX Desk.
- See [docs/assumptions.md](docs/assumptions.md) for the complete list.

## 18. Academic Mapping

See [ACADEMIC_MAPPING.md](ACADEMIC_MAPPING.md) — grounded directly in the two uploaded course
syllabi (**CS4231 Fundamentals of Computer Vision** and **CS4104 Computer Graphics and Virtual
Reality**, both RV University), with every topic marked Implemented / Partial / Not Implemented
against real code, and reasons given for anything out of scope. Also rendered live in-app at
**Academic Mode → Course Mapping**.

---

**Disclaimer**: Educational/simulated Treasury analytics platform. No real-money trading. Outputs
are for academic and demonstration purposes only. Nothing in this application constitutes financial
or investment advice.
