# TreasuryX Demo Script

**One integrated walkthrough (~10-12 min)** — not three separate lab tours. Computer Vision and
Computer Graphics show up as real capabilities inside the Treasury workflow, not as detours into
an academic lab. The same script (slightly condensed) is also rendered in-app at
**Methodology → Demo Guide** if you'd rather present from the browser.

## 1. Workstation baseline (~3 min)

1. **Overview** — point out the Total P&L / VaR / DV01 / Market Regime cards (each with unit +
   method label), the **Data Status** panel, and the small **Technology Integration** panel
   (FOCV / Treasury Engine / CGVR — subtle, professional, not a badge farm).
2. **FX Desk** — book a simulated USD/INR trade; show the updated row in Open FX Positions.
3. **Rates & Bonds** — select a G-Sec; show clean price, modified duration, convexity, DV01.
4. **Portfolio Risk** — toggle 95%→99% VaR confidence, note it increases.
5. **Stress Testing** — run "Combined stress: USD/INR +2%, 2Y +10bp, 10Y +50bp"; walk through the
   audit trail (`SCN-00xxx`, inputs, exact-vs-duration-approx note, deterministic-no-AI note).

## 2. Financial Image Intelligence — the Computer Vision integration (~4 min)

1. Open **Financial Image Intelligence**, upload a chart/report screenshot mentioning a bond ISIN
   or FX pair and a value.
2. Point at the extracted field row; click **How Detected?** to reveal the preprocessing → OCR →
   pairing trace for that specific value.
3. Expand **Processing Details** to show every pipeline-stage image (original → grayscale →
   denoised → CLAHE → threshold → Canny → region) — real OpenCV output, not a mockup.
4. Edit the extracted value in the input box, click **Apply to Treasury** — show the "Portfolio
   updated" confirmation with before/after clean price and DV01.
5. Navigate to **Rates & Bonds** and **Portfolio Risk** — the correction is visibly reflected there
   too, because it went through the same effective-market-view layer the rest of the app reads
   from, not a one-off calculation shown once and discarded.
6. Open **Compare Market Screens**, upload two related screenshots, show SIFT keypoint matching
   with the confident-match count and visualization.

## 3. 3D Market — the Computer Graphics integration (~4 min)

1. Open **3D Market → 3D Yield Surface**. Rotate/zoom; note it reflects the correction just
   applied in step 2.
2. Toggle **Perspective / Orthographic** — the camera projection genuinely switches (compare how
   the surface's apparent depth changes).
3. Open **Graphics Details** — show the live Model/View/Projection matrices updating as you orbit
   the camera (these are read directly from the Three.js renderer, not hand-typed examples).
4. Switch to **Risk View** — the same data now renders through the hand-written GLSL shader;
   adjust the threshold slider live and watch the color band move.
5. Open **Explain This Visualization** — walk through the data → geometry → model transform → view
   transform → projection → depth → lighting/shading trace, tailored to the current settings.
6. Switch to **3D Portfolio Stress Surface** — run a scenario shock first (back on Stress Testing),
   then return and show the surface reflects it.

## 4. Methodology — documentation, not a fourth demo (~2 min)

1. **Course Mapping** — the syllabus-grounded table: implemented / partial / not-implemented, with
   reasons, for both CS4231 and CS4104.
2. **Computer Vision Methodology** / **Computer Graphics Methodology** — the written pipeline docs
   matching exactly what was just shown live, including why CNN/ViT and deep object detection are
   kept as evaluation exercises rather than claimed production capabilities.
3. **Technical Evidence** — point out the supplementary pages (raster algorithms, 2D transforms,
   CNN vs. ViT benchmarks, VR/AR concepts) — syllabus topics with no natural Treasury use, kept as
   direct evidence rather than forced into the product.

## Integration Story (close with this)

```
financial chart image → Computer Vision extraction → structured financial value
   → Treasury analytics (P&L / risk) → Computer Graphics visualization
```

Both academic subjects and the Treasury domain meet in this one pipeline, inside one product —
not as three unrelated demos bolted together. See [ACADEMIC_MAPPING.md](ACADEMIC_MAPPING.md) for
the full syllabus cross-reference.
