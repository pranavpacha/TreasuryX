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
      <Panel title="Demo Guide — One Integrated Walkthrough (~10-12 min)">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Full script with timings: see <code>DEMO_SCRIPT.md</code> in the repository. This is ONE Treasury
          workstation demo, not three separate lab tours — Computer Vision and Computer Graphics show up as real
          capabilities inside the workflow, not as detours.
        </p>
      </Panel>

      <Panel title="1. Workstation baseline (~3 min)">
        <DemoSteps steps={[
          "Overview: point out P&L / VaR / DV01 / Regime cards, Data Status, and the Technology Integration panel.",
          "FX Desk: book a simulated USD/INR trade, show updated MTM P&L.",
          "Rates & Bonds: select a G-Sec, show duration/convexity/DV01.",
          "Portfolio Risk: toggle 95%/99% VaR confidence.",
          "Stress Testing: run a combined FX+yield shock, walk through the audit trail (SCN-xxxxx).",
        ]} />
      </Panel>

      <Panel title="2. Financial Image Intelligence — the Computer Vision integration (~4 min)">
        <DemoSteps steps={[
          "Open Financial Image Intelligence, upload a chart/report screenshot mentioning a bond ISIN or FX pair and a value.",
          "Show the extracted field, click 'How Detected?' to reveal the preprocessing → OCR → pairing trace.",
          "Expand 'Processing Details' to show every pipeline stage image (this is real OpenCV, not a mockup).",
          "Edit the extracted value, click 'Apply to Treasury' — show the 'Portfolio updated' confirmation with before/after price and DV01.",
          "Jump to Rates & Bonds and Portfolio Risk — the correction is visibly reflected there too (same effective-market-view layer, not a one-off calculation).",
          "Open Compare Market Screens, upload two related screenshots, show SIFT keypoint matching finding shared/changed regions.",
        ]} />
      </Panel>

      <Panel title="3. 3D Market — the Computer Graphics integration (~4 min)">
        <DemoSteps steps={[
          "Open 3D Market → 3D Yield Surface. Rotate/zoom; note it reflects the correction just applied.",
          "Toggle Perspective/Orthographic — the camera projection genuinely switches.",
          "Open 'Graphics Details' — show the live Model/View/Projection matrices updating as you orbit.",
          "Switch to 'Risk View' — the same data now renders through the hand-written GLSL shader; adjust the threshold slider live.",
          "Open 'Explain This Visualization' — walk through the data → geometry → transform → projection → depth → lighting → shader trace.",
          "Switch to 3D Portfolio Stress Surface — run a scenario shock first, then show the surface reflects it.",
        ]} />
      </Panel>

      <Panel title="4. Methodology — the documentation, not the demo (~2 min)">
        <DemoSteps steps={[
          "Course Mapping: show the syllabus-grounded table — what's implemented, what's honestly marked not implemented, and why.",
          "Computer Vision Methodology / Computer Graphics Methodology: the written pipeline docs matching what was just shown live.",
          "Technical Evidence: point out the supplementary pages (raster algorithms, 2D transforms, CNN vs ViT benchmarks, VR/AR concepts) — syllabus topics with no natural Treasury use, kept as direct evidence rather than forced into the product.",
        ]} />
      </Panel>

      <Panel title="Integration Story">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Financial chart image → Computer Vision extraction → structured financial value → Treasury analytics
          (P&L/risk) → Computer Graphics visualization. Both academic subjects and the Treasury domain meet in one
          pipeline, inside one product, rather than existing as separate, unrelated demos.
        </p>
      </Panel>
    </div>
  );
}
