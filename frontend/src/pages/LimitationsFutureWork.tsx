import { Panel } from "../components/Common";

export default function LimitationsFutureWork() {
  return (
    <div>
      <Panel title="Limitations & Assumptions">
        <ul style={{ fontSize: 12, color: "var(--text-mid)", paddingLeft: 18 }}>
          <li>All market data is synthetic (fixed-seed, mean-reverting random walk) — no live data provider is wired up in this build.</li>
          <li>Bond pricing uses an equal-period, fractional-settlement day-count simplification, not a full Act/Act or 30/360 calendar implementation.</li>
          <li>Historical VaR/ES uses a single reconstructed portfolio-value series, not a full covariance-matrix parametric model.</li>
          <li>Market regime classification is rule-based (documented thresholds), not a trained/validated ML model — explicitly a decision-support signal, not a prediction.</li>
          <li>CV field-to-instrument matching (nearest-OCR-word heuristic) is approximate by design — always shown with a confidence score and correctable before committing.</li>
          <li>OCR requires the Tesseract binary, installed separately from Python dependencies; the rest of the CV pipeline runs regardless of whether it's present.</li>
          <li>CNN/ViT models are trained on a small, procedurally-generated synthetic 4-class dataset — near-ceiling accuracy reflects the task's simplicity, not general-purpose chart-recognition accuracy on real-world screenshots.</li>
          <li>Deep object detectors (Fast R-CNN/FPN/RetinaNet/YOLO) are not trained in this build — see the Object Detection lab for the documented reason and a reproducible pipeline.</li>
          <li>Segmentation uses classical GrabCut, not a trained U-Net — the syllabus's medical-imaging U-Net lab is out of scope (wrong domain for a Treasury tool).</li>
          <li>No custom GLSL shaders were needed beyond the one built for the yield-curve demonstration — built-in Three.js materials cover the rest of the 3D visualization.</li>
          <li>No VR/AR hardware is used anywhere — Modules 4-5 of the Graphics course are documented conceptually only.</li>
          <li>No authentication/authorization layer — this is a single-user local/demo deployment, not a multi-tenant system.</li>
        </ul>
      </Panel>

      <Panel title="Future Work">
        <ul style={{ fontSize: 12, color: "var(--text-mid)", paddingLeft: 18 }}>
          <li>Wire a real (delayed) market-data provider behind the existing MarketDataProvider interface.</li>
          <li>Portfolio-level (covariance-aware) VaR instead of a single reconstructed-value historical series.</li>
          <li>A labeled financial-chart dataset large enough to justify training a real object detector (Fast R-CNN or a lightweight single-stage detector) for chart-region/legend/axis-label localization.</li>
          <li>A trained U-Net or similar segmentation network once a labeled financial-screenshot dataset exists, to replace the current classical GrabCut approach.</li>
          <li>WebSocket-based live quote streaming into the FX Desk.</li>
          <li>Custom shaders for the FX volatility and portfolio stress surfaces (currently the standard-material path), matching the yield-surface shader.</li>
          <li>Production-grade authentication and PostgreSQL for a genuinely multi-user deployment.</li>
        </ul>
      </Panel>
    </div>
  );
}
