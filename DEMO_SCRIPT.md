# TreasuryX Demo Script

Three focused walkthroughs (~5-7 minutes each), designed to stand alone for a Treasury-focused,
Computer-Vision-focused, or Computer-Graphics-focused audience. All three can also be run
back-to-back (~18-20 min) to tell the full integration story. Toggle **Academic Mode** (top-right
of the header) to reveal the CV Lab / Graphics Lab / Academic & Documentation nav sections used
in Demos 2 and 3.

## Demo 1 — Treasury Workflow (~5-7 min)

1. **Overview** — point out the Total P&L / VaR / DV01 / Market Regime cards (each with unit +
   method label, never a bare number), FX/curve snapshot, and market-intelligence event feed.
2. **FX Desk** — book a simulated USD/INR trade (note the SIMULATED badge); show the updated
   row in Open FX Positions with entry rate, current rate, and P&L.
3. **Rates & Bonds** — select a G-Sec; show clean price, modified duration, convexity, DV01 with
   their tooltips (bump-and-reprice methodology).
4. **Yield Curve** — compare two dates ~20 business days apart; show the curve-shift table and the
   steepening/flattening classification rule.
5. **Portfolio Risk** — toggle 95%→99% VaR confidence, note it increases; point out the
   "no look-ahead bias" note.
6. **Stress Testing** — run "Combined stress: USD/INR +2%, 2Y +10bp, 10Y +50bp"; walk through the
   **Methodology / Audit Trail** section (`SCN-00xxx` id, exact-vs-duration-approx note,
   deterministic-no-AI note, raw inputs JSON).
7. **Trade Blotter** — show every simulated trade booked so far.

## Demo 2 — Computer Vision (~5-7 min)

Grounds every step in **CS4231 Fundamentals of Computer Vision**'s actual module/lab structure.

1. **Market Intelligence** — upload a chart screenshot; walk through all 7 pipeline stages
   (original → grayscale → denoised → CLAHE-normalized → thresholded → Canny edges → detected
   region), then the OCR text and structured field table; manually correct a value and
   **Commit → Engine**.
2. **Academic Mode → CV Lab home** — show the full lab list, each tagged to a specific
   module/lab requirement.
3. **Filters lab** — compare Gaussian/median/bilateral/CLAHE side by side.
4. **Edges lab** — adjust the Canny low/high sliders live; compare DoG vs LoG vs Sobel/Laplacian.
5. **SIFT lab** — upload two related images; show keypoint counts and Lowe's-ratio-test matches.
6. **Segmentation lab** — show the real IoU/Dice benchmark computed on synthetic ground truth
   (mean IoU ≈0.96 as of this build), then try GrabCut on your own image.
7. **CNN vs ViT (Model Benchmarks)** — walk through both models' accuracy/precision/recall/F1,
   confusion matrices, training curves, and sample predictions — both trained from scratch on the
   *same* synthetic dataset for a fair comparison.
8. **Object Detection lab** — show the honest `NOT_TRAINED` status and the documented reason
   (Fast R-CNN/YOLO need GPU-scale training + a large labeled dataset, out of scope for a laptop
   build) plus the reproducible pipeline spec.

## Demo 3 — Computer Graphics (~5-7 min)

Grounds every step in **CS4104 Computer Graphics and Virtual Reality**'s actual module/lab
structure.

1. **Raster Graphics lab** — step through DDA and Bresenham pixel-by-pixel on the 32x32 grid,
   then the Midpoint Circle algorithm; show the RGB/CMY/HSV round-trip widget.
2. **2D Transform & Clip lab** — compose translate/rotate/scale/shear, read the live homogeneous
   3x3 matrix; run Cohen-Sutherland and Liang-Barsky clipping on the same line and compare their
   step-by-step logs.
3. **3D Transform & Shader lab** — rotate/scale a 3D box, read the live Model/View/Projection
   matrices (computed by Three.js, not simulated); compare perspective vs orthographic side by
   side; adjust ambient/directional lighting intensity.
4. **Custom shader section** (same page) — adjust the risk-threshold uniform on the real
   yield-curve-driven GLSL shader surface; expand "View shader source" to show the actual GLSL.
5. **Depth Buffer lab** — show the from-scratch software Z-buffer result (correct occlusion by
   depth, not draw order), then toggle WebGL depth-test on/off on two overlapping planes.
6. **3D Market** (outside Academic Mode) — rotate the yield/volatility/stress surfaces built from
   live Treasury data — closes the loop from graphics theory to the actual application.

## Integration Story (close every demo with this)

```
financial chart image → Computer Vision extraction → structured financial value
   → Treasury analytics (P&L / risk) → 3D visualization
```

Both academic subjects and the Treasury domain meet in this one pipeline rather than existing as
three unrelated mini-projects. See **Academic Mode → Course Mapping** for the full syllabus
cross-reference, and [ACADEMIC_MAPPING.md](ACADEMIC_MAPPING.md) for the written version.
