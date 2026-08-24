import { Link } from "react-router-dom";
import { Badge, Panel } from "../../components/Common";

const CV_EVIDENCE = [
  { to: "/evidence/cv/filters", label: "Filter Comparison", desc: "Gaussian, median, bilateral, CLAHE — the same filters used in the Financial Image Intelligence preprocessing stage, shown side by side." },
  { to: "/evidence/cv/edges", label: "Edge Detection", desc: "Sobel, Laplacian, DoG, LoG, adjustable Canny — the family of edge detectors behind chart-boundary and axis detection." },
  { to: "/evidence/cv/features", label: "Corner & Blob Detection", desc: "Harris corners and blob detection for gridline intersections and marker-like regions." },
  { to: "/evidence/cv/segmentation", label: "Segmentation Benchmark", desc: "GrabCut chart-region isolation with real IoU/Dice metrics on a synthetic ground-truth dataset." },
  { to: "/evidence/cv/optical-flow", label: "Optical Flow", desc: "Dense Farneback flow between two frames, for detecting motion/change between sequential screenshots." },
  { to: "/evidence/cv/models", label: "CNN vs. Vision Transformer", desc: "Two models trained from scratch on a synthetic chart-classification dataset, with real accuracy/precision/recall/F1/confusion-matrix results." },
  { to: "/evidence/cv/object-detection", label: "Deep Object Detection — Status", desc: "Honest NOT_TRAINED status and a documented, reproducible training pipeline for Fast R-CNN/YOLO-style detection." },
];

const GRAPHICS_EVIDENCE = [
  { to: "/evidence/graphics/raster", label: "Raster Graphics", desc: "DDA, Bresenham, and Midpoint Circle — implemented pixel-by-pixel, plus RGB/CMY/HSV color-model conversions. No natural Treasury production use, kept here as direct syllabus evidence." },
  { to: "/evidence/graphics/transform2d", label: "2D Transformations & Clipping", desc: "Homogeneous-coordinate matrices, composite transforms, Cohen-Sutherland & Liang-Barsky line clipping." },
  { to: "/evidence/graphics/concepts", label: "Transform / Camera / Lighting Concepts", desc: "A generic 3D object with live Model/View/Projection matrices, perspective-vs-orthographic comparison, and an illumination-model demonstration — the same concepts the production 3D Market page uses on real data." },
  { to: "/evidence/graphics/depth-buffer", label: "Software Z-Buffer", desc: "A from-scratch, pixel-by-pixel Z-buffer algorithm implementation (not just a WebGL flag), plus a WebGL depth-test on/off comparison." },
  { to: "/evidence/graphics/vr-ar", label: "VR / AR / XR Concepts", desc: "Documented conceptually per the syllabus's VR/AR modules — no VR/AR hardware used, by design." },
];

export default function TechnicalEvidence() {
  return (
    <div>
      <Panel title="Technical Evidence">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Every capability used in the actual product — image preprocessing, edge/region detection, OCR,
          segmentation, SIFT matching, CNN/ViT classification, and the 3D rendering pipeline (transforms, camera,
          projection, depth, lighting, custom GLSL shader) — runs inside the real workstation pages: <Link to="/intelligence/financial-image">Financial Image Intelligence</Link>,{" "}
          <Link to="/intelligence/compare-screens">Compare Market Screens</Link>, and{" "}
          <Link to="/visualization/3d-market">3D Market</Link>. The pages below are supplementary: a few syllabus
          topics (raster algorithms, 2D transform mathematics, VR/AR concepts) have no natural Treasury production
          use, so per the project's own design rule they're kept here as direct, inspectable evidence instead of
          being forced into the main workflow. A couple of others (the CNN/ViT model comparison, the deep
          object-detection status) are shown here because they're evaluation/benchmark exercises rather than
          production-critical routing decisions — see each page for why.
        </p>
      </Panel>

      <Panel title="Computer Vision (CS4231) — Supplementary Evidence">
        <div className="grid grid-2">
          {CV_EVIDENCE.map((e) => (
            <Link key={e.to} to={e.to} style={{ textDecoration: "none" }}>
              <div className="panel" style={{ cursor: "pointer", marginBottom: 0 }}>
                <strong style={{ fontSize: 13, color: "var(--text-hi)" }}>{e.label}</strong>
                <div style={{ fontSize: 11.5, color: "var(--text-mid)", marginTop: 4 }}>{e.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </Panel>

      <Panel title="Computer Graphics (CS4104) — Supplementary Evidence">
        <div className="grid grid-2">
          {GRAPHICS_EVIDENCE.map((e) => (
            <Link key={e.to} to={e.to} style={{ textDecoration: "none" }}>
              <div className="panel" style={{ cursor: "pointer", marginBottom: 0 }}>
                <strong style={{ fontSize: 13, color: "var(--text-hi)" }}>{e.label}</strong>
                <div style={{ fontSize: 11.5, color: "var(--text-mid)", marginTop: 4 }}>{e.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </Panel>

      <Panel title="Not Implemented (stated honestly, not silently omitted)">
        <Badge kind="warn">See Course Mapping for full detail</Badge>
        <p style={{ fontSize: 11.5, color: "var(--text-mid)", marginTop: 8 }}>
          FaceNet/Siamese networks, U-Net trained on a medical-imaging dataset, Fast R-CNN/FPN/RetinaNet/YOLO
          training, neural style transfer, 3D CNN/RNN video understanding, zero/few-shot and self-supervised
          learning, CLIP, RL-in-vision, and Unity-based 3D scenes are not implemented — each for a specific,
          documented reason (wrong domain, out of laptop compute/dataset scope, or outside this web app's stack).
          See <Link to="/methodology/course-mapping">Course Mapping</Link>.
        </p>
      </Panel>
    </div>
  );
}
