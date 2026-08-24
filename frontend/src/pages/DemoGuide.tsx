import { Panel } from "../components/Common";

function DemoSteps({ steps }: { steps: string[] }) {
  return (
    <ol style={{ fontSize: 12, color: "var(--text-mid)", paddingLeft: 20 }}>
      {steps.map((s, i) => <li key={i} style={{ marginBottom: 4 }}>{s}</li>)}
    </ol>
  );
}

export default function DemoGuide() {
  return (
    <div>
      <Panel title="Demo Guide — Three Focused Walkthroughs">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Full script with timings: see <code>DEMO_SCRIPT.md</code> in the repository. Each demo below runs
          ~5-7 minutes and is designed to stand alone for a Treasury, CV, or Graphics-focused audience.
        </p>
      </Panel>

      <Panel title="Demo 1 — Treasury Workflow (~5-7 min)">
        <DemoSteps steps={[
          "Overview: point out P&L / VaR / DV01 / Regime cards, each with unit + method label.",
          "FX Desk: book a simulated USD/INR trade, show updated MTM P&L.",
          "Rates & Bonds: select a G-Sec, show duration/convexity/DV01.",
          "Yield Curve: compare two dates, show the shift table and steepening/flattening classification.",
          "Risk: toggle 95%/99% VaR confidence, note the change.",
          "Scenario/Stress: run a combined FX+yield shock, walk through the audit trail (SCN-xxxxx).",
        ]} />
      </Panel>

      <Panel title="Demo 2 — Computer Vision (~5-7 min)">
        <DemoSteps steps={[
          "Market Intelligence: upload a chart screenshot, walk through all 7 pipeline stages.",
          "CV Lab home: show the full lab list mapped to CS4231 modules.",
          "Filters/Edges labs: adjust Canny thresholds live, compare DoG vs LoG.",
          "SIFT lab: upload two related images, show keypoint matching with the ratio test.",
          "Segmentation lab: show the real IoU/Dice benchmark on synthetic ground truth.",
          "Model Benchmarks: CNN vs ViT accuracy, confusion matrices, training curves, sample predictions.",
          "Object Detection lab: show the honest NOT_TRAINED status and documented reasoning.",
        ]} />
      </Panel>

      <Panel title="Demo 3 — Computer Graphics (~5-7 min)">
        <DemoSteps steps={[
          "Raster lab: step through DDA and Bresenham pixel-by-pixel, then the Midpoint Circle algorithm.",
          "2D Transform lab: compose translate/rotate/scale/shear, show the live homogeneous matrix; run Cohen-Sutherland and Liang-Barsky clipping on the same line.",
          "3D Graphics lab: rotate/scale a 3D object, read out the live Model/View/Projection matrices; compare perspective vs orthographic; adjust ambient/directional lighting.",
          "Depth Buffer lab: show the from-scratch software Z-buffer result, then toggle WebGL depth-test on/off.",
          "Custom shader section: adjust the risk-threshold uniform on the real yield-curve shader surface, view the GLSL source.",
          "3D Market: rotate the yield/volatility/stress surfaces built from live Treasury data -- close the loop from graphics theory to the actual application.",
        ]} />
      </Panel>

      <Panel title="Integration Story">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Financial chart image → Computer Vision extraction → structured financial value → Treasury analytics
          (P&L/risk) → 3D visualization. Both academic subjects and the Treasury domain meet in this one pipeline
          rather than existing as separate, unrelated mini-projects.
        </p>
      </Panel>
    </div>
  );
}
