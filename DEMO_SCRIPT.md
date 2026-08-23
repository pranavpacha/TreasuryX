# TreasuryX Demo Script (~8–12 minutes)

**Before you start:** run the backend (`uvicorn app.main:app --reload --port 8000`) and frontend
(`npm run dev`), open `http://localhost:5173`. Everything works offline; the amber
**DEMO / SIMULATED DATA** badge in the header should be visible throughout.

## 1. Overview (1 min)
Open **Overview**. Point out: the disclaimer bar, Total P&L / VaR / DV01 / Market Regime metric
cards (each with a unit and method label, not a bare number), the FX and yield-curve snapshots, risk
limit utilization, and the market-intelligence event feed.

## 2. FX Desk (1.5 min)
Open **FX Desk**. Show the quote table (rate/bid/ask/spread/1D return/annualized vol with a
tooltip explaining the volatility methodology). Click a pair to load its 180-day chart. Book a
**simulated** trade (note the SIMULATED badge and disclaimer) and show the new/updated row in "Open
FX Positions & MTM P&L" with entry rate, current rate, and P&L.

## 3. Rates & Bonds (1.5 min)
Open **Rates & Bonds**. Show the G-Sec table: coupon, maturity, yield, clean price, modified
duration, convexity, DV01 (each with a tooltip explaining the bump-and-reprice method). Click a bond
to load its yield/price history and book a simulated bond trade.

## 4. Yield Curve (1 min)
Open **Yield Curve**. Pick two dates ~20 business days apart, show the two-curve overlay chart, the
per-tenor shift table (bps), and the STEEPENING/FLATTENING/STABLE classification with its rule
explained inline.

## 5. Risk (1.5 min)
Open **Risk**. Explain historical VaR/ES (95%/99%, selectable lookback, "no look-ahead" note),
max drawdown, exposures, and risk-limit utilization. Toggle confidence to 99% and note VaR increases.

## 6. Scenario / Stress Testing (2 min)
Open **Scenario / Stress**. Run the "10Y +25bp (parallel)" preset — note the instant P&L
recompute. Then run "Combined stress: USD/INR +2%, 2Y +10bp, 10Y +50bp" and walk through the
**Methodology / Audit Trail** section (`SCN-00xxx` id, exact-reprice note, deterministic-no-AI note,
raw inputs JSON) — this is the auditability story (spec section 29).

## 7. Trade Blotter (0.5 min)
Open **Trade Blotter** — show every simulated trade booked so far, all marked SIMULATED.

## 8. Market Intelligence / Computer Vision (2.5 min)
Open **Market Intelligence (CV)**. Upload a screenshot of a chart (e.g. a screenshot of the FX Desk
or Yield Curve page from this same app, or any FX/yield chart image). Walk through:
- the 7-stage pipeline strip (original → grayscale → denoised → CLAHE-normalized → thresholded →
  Canny edges → detected region/lines) — **this is the actual CV work**, not a black box;
- the raw OCR text panel (note the graceful-degradation warning if Tesseract isn't installed);
- the extracted fields table with per-field confidence badges;
- **manually correct a value** in the input box;
- click **Commit → Engine** and show the returned analytics (bond duration/DV01 or FX spot
  comparison) — this closes the CV → structured value → Treasury analytics loop (spec section 41).

## 9. 3D Market (2 min)
Open **3D Market**. Show all three tabs:
- **Yield Curve Surface** — rotate/zoom, hover a point to show its tenor/date/yield tooltip;
- **FX Volatility Surface** — note the diverging window-length axis;
- **Portfolio Stress Surface** — a diverging red/green surface driven directly by the scenario
  engine over a grid of FX × yield shocks (built from your booked positions).
Scroll down to the **Graphics Info** panel and briefly name the projection, camera model, lighting
model, and coordinate system — this demonstrates the graphics pipeline is understood, not copy-pasted.

## 10. Wrap-up (0.5 min)
Summarize the integration story: **financial chart image → Computer Vision extraction → structured
financial value → Treasury analytics (P&L/risk) → 3D visualization**, and name both academic
subjects covered (see [ACADEMIC_MAPPING.md](ACADEMIC_MAPPING.md)).
