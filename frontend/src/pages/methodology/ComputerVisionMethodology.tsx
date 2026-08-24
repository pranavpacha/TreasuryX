import { Link } from "react-router-dom";
import { Badge, Panel } from "../../components/Common";

const STAGES = [
  { stage: "1. Preprocessing", algo: "Resize, grayscale, non-local-means denoise, CLAHE contrast normalization, adaptive threshold", purpose: "Cleans up screenshot artifacts (compression noise, uneven lighting) before structural analysis." },
  { stage: "2. Region / structure detection", algo: "Canny edges + probabilistic Hough line transform + largest-contour bounding box", purpose: "Locates the chart plot area and axis lines so extraction focuses on the relevant region." },
  { stage: "3. Chart-type classification", algo: "Deterministic keyword/structural classifier over OCR text", purpose: "Routes the image to the right interpretation (FX chart vs. yield curve vs. table/report) — chosen over a CNN/ViT here because it's reliable on arbitrary real uploads (see note below)." },
  { stage: "4. OCR / text extraction", algo: "Tesseract via pytesseract, per-word text + bounding box + confidence", purpose: "Extracts instrument names, numbers, dates, percentages." },
  { stage: "5. Field extraction", algo: "Regex number/date/instrument matching + nearest-neighbor pairing", purpose: "Associates a detected number with its nearest instrument label." },
  { stage: "6. Structured output", algo: "{instrument, metric, value, unit, confidence, source_region}", purpose: "A reviewable, editable structure — never written directly into Treasury analytics without human confirmation." },
];

export default function ComputerVisionMethodology() {
  return (
    <div>
      <Panel title="Computer Vision Methodology">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          TreasuryX's Computer Vision work is used for one real product capability:{" "}
          <Link to="/intelligence/financial-image">Financial Image Intelligence</Link> — turning an uploaded
          chart/report screenshot into structured Treasury data — plus{" "}
          <Link to="/intelligence/compare-screens">Compare Market Screens</Link> for visual comparison between two
          screenshots. This page documents the pipeline; the algorithms themselves run inside those product pages,
          not a separate lab.
        </p>
      </Panel>

      <Panel title="Financial Image Intelligence Pipeline">
        <table className="data-table">
          <thead><tr><th>Stage</th><th>Algorithm</th><th>Purpose</th></tr></thead>
          <tbody>
            {STAGES.map((s) => (
              <tr key={s.stage}>
                <td style={{ textAlign: "left" }}>{s.stage}</td>
                <td style={{ textAlign: "left" }}>{s.algo}</td>
                <td style={{ textAlign: "left" }}>{s.purpose}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="Why classical CV, not a pretrained deep detector, for the extraction pipeline">
        <p style={{ fontSize: 11.5, color: "var(--text-mid)" }}>
          Financial chart/report screenshots are dominated by text and line primitives (axis labels, legends,
          numeric callouts, gridlines) rather than natural-scene objects. A classical OpenCV pipeline is more
          precise for this domain, runs instantly on a laptop CPU with no GPU or large model download, and is
          fully explainable — every intermediate result is inspectable, which matters more for an auditable
          Treasury tool than a black-box detector's raw accuracy.
        </p>
      </Panel>

      <Panel title="Where CNN and Vision Transformer fit in">
        <p style={{ fontSize: 11.5, color: "var(--text-mid)", marginBottom: 8 }}>
          A CNN and a Vision Transformer were written and trained from scratch as a genuine architecture
          comparison for image classification (see <Link to="/evidence/cv/models">CNN vs. Vision Transformer</Link>).
          Both are trained only on a small, synthetic, procedurally-generated chart dataset — not real market
          screenshots — so their predictions on an arbitrary real upload are not reliable enough to drive
          production routing decisions. <strong>The chart-type classifier that actually routes the Financial Image
          Intelligence pipeline is the deterministic keyword/structural classifier above</strong>, which is
          reliable on real uploads. The CNN/ViT comparison is kept as a rigorous, honestly-labeled evaluation
          exercise rather than claiming an unreliable capability as production-ready.
        </p>
        <Badge kind="warn">No fabricated accuracy claims — see the real, measured results</Badge>
      </Panel>

      <Panel title="Honesty on Object Detection">
        <p style={{ fontSize: 11.5, color: "var(--text-mid)" }}>
          Training a real financial-domain object detector (Fast R-CNN/FPN/RetinaNet/YOLO) needs a labeled
          bounding-box dataset and GPU-scale compute — out of scope for a laptop, offline-capable build. Rather
          than show generic COCO-object detections mislabeled as "financial objects," or fabricate metrics, this
          is reported honestly with a documented, reproducible pipeline spec — see{" "}
          <Link to="/evidence/cv/object-detection">Object Detection — Status</Link>. The classical region/line
          detection already used in Financial Image Intelligence covers the actual in-scope need (locating the
          chart plot area and axes).
        </p>
      </Panel>
    </div>
  );
}
