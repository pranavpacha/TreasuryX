# Database Schema

SQLite via SQLAlchemy 2.0 declarative models (`backend/app/models/`). Timestamps are stored as UTC
(`TimestampMixin.created_at`, default `datetime.now(timezone.utc)`) and displayed in Asia/Kolkata in
the UI. No SQLite-specific column types are used, so switching `TREASURYX_DATABASE_URL` to a
PostgreSQL DSN requires no schema changes.

| Table | Model | Purpose |
|---|---|---|
| `bonds` | `Bond` | Static G-Sec reference data, seeded from the demo provider at startup |
| `fx_quotes` | `FxQuoteCache` | Optional cache table for a future live provider (unused in demo mode — quotes are served directly from CSV) |
| `yield_curve_points` | `YieldCurvePointCache` | Same purpose as above, for curve points |
| `positions` | `Position` | Open/closed simulated FX or bond positions (signed quantity) |
| `trades` | `Trade` | Immutable trade-blotter rows, always `status="SIMULATED"` |
| `pnl_snapshots` | `PnlSnapshot` | Point-in-time P&L snapshots (reserved for future scheduled snapshotting) |
| `risk_metrics` | `RiskMetricSnapshot` | Point-in-time risk metric snapshots (reserved for future use) |
| `scenarios` | `ScenarioRun` | Every scenario/stress run: inputs, outputs, total P&L — the audit trail |
| `cv_extractions` | `CvExtraction` | Every CV upload: filenames, extracted/corrected JSON, confidence, commit flag |
| `market_overrides` | `MarketOverride` | **The CV-to-Treasury state-change mechanism**: latest-wins correction per (instrument_type, instrument_id, field), applied on top of baseline demo data by `services/market_view.py` — this is what makes "Apply to Treasury" a real, persistent change instead of a one-off calculation |
| `market_events` | `MarketEvent` | Demo market-intelligence headlines shown on the Overview page |
| `audit_logs` | `AuditLog` | Generic append-only audit entries (CV corrections/commits, etc.) |

`backend/app/seed.py::seed_all` idempotently seeds `bonds`, a handful of illustrative demo
`positions`, and `market_events` on first startup (checked via row counts, so re-running is a no-op).
