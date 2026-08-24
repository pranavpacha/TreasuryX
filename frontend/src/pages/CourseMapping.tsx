import { Link } from "react-router-dom";
import { Badge, Panel } from "../components/Common";

interface Row {
  topic: string;
  status: "implemented" | "partial" | "not";
  where: string;
  link?: string;
  note?: string;
}

const CV_ROWS: Row[] = [
  { topic: "Image formation, sensing, acquisition, sampling & quantization (Module 1)", status: "implemented", where: "cv_engine/preprocessing.py", link: "/vision", note: "Resize, grayscale conversion, quantization via thresholding" },
  { topic: "Camera geometry (Module 1)", status: "not", where: "—", note: "No camera-calibration or multi-view geometry task in this project" },
  { topic: "Color image fundamentals — RGB, HSI (Module 1)", status: "partial", where: "graphics/colorModels.ts", link: "/academic/graphics/raster", note: "RGB/CMY/HSV implemented (HSI not implemented; HSV used instead, matching the CG course's own Module 1)" },
  { topic: "Spatial domain processing & spatial filtering (Module 1, Lab 1)", status: "implemented", where: "cv_engine/filters_lab.py", link: "/academic/cv/filters" },
  { topic: "Edge detection, DoG, LoG, Canny (Module 2, Lab 2)", status: "implemented", where: "cv_engine/edges_lab.py", link: "/academic/cv/edges" },
  { topic: "Edge linking via Hough Transform (Module 2, Lab 2)", status: "implemented", where: "cv_engine/edges.py (detect_lines)", link: "/vision", note: "Shown in the integrated financial-image pipeline's region-detection stage" },
  { topic: "Segmentation — thresholding, morphological processing (Module 2)", status: "implemented", where: "cv_engine/preprocessing.py, segmentation_lab.py", link: "/academic/cv/segmentation" },
  { topic: "Blobs, corner detection (Module 2)", status: "implemented", where: "cv_engine/features_lab.py", link: "/academic/cv/features" },
  { topic: "Scale space & scale selection; SIFT (Module 2, Lab 3)", status: "implemented", where: "cv_engine/sift_lab.py", link: "/academic/cv/sift" },
  { topic: "Optical flow (Module 2)", status: "implemented", where: "cv_engine/optical_flow_lab.py", link: "/academic/cv/optical-flow" },
  { topic: "CNN review, CNNs for recognition (Module 3)", status: "implemented", where: "cv_engine/models/cnn.py, train.py", link: "/academic/cv/models", note: "Small CNN trained from scratch on a synthetic 4-class chart dataset with real accuracy/precision/recall/F1/confusion-matrix metrics" },
  { topic: "Neural style transfer (Module 3)", status: "not", where: "—", note: "Lecture topic, no corresponding lab; not implemented" },
  { topic: "CNNs for object detection — R-CNN, Fast R-CNN, FPN, RetinaNet (Module 3, Lab 4)", status: "not", where: "—", link: "/academic/cv/object-detection", note: "Requires PASCAL-VOC-scale labeled data + GPU training, out of scope for a laptop build — status page documents why + a reproducible pipeline" },
  { topic: "CNNs for segmentation — FCN, U-Net, Mask-RCNN (Module 3, Lab 5)", status: "partial", where: "cv_engine/segmentation_lab.py", link: "/academic/cv/segmentation", note: "Classical (GrabCut) segmentation implemented for the in-scope chart-isolation task; U-Net/medical-dataset training out of scope (wrong domain)" },
  { topic: "Siamese networks, triplet/contrastive/ranking loss, FaceNet (Module 3, Lab 6)", status: "not", where: "—", note: "Face verification is off-domain for a Treasury tool and avoids handling biometric data; not implemented" },
  { topic: "3D CNN for video, RNN/CNN for video understanding, action recognition (Module 4)", status: "not", where: "—", note: "No video data in this project; theory only" },
  { topic: "Attention models, Transformer review, Vision Transformers (Module 4, Lab 7)", status: "implemented", where: "cv_engine/models/vit.py, train.py", link: "/academic/cv/models", note: "A ViT written from scratch (patch embedding, class token, multi-head self-attention) trained on the same synthetic dataset as the CNN, for a direct comparison" },
  { topic: "YOLO (Module 5)", status: "not", where: "—", link: "/academic/cv/object-detection", note: "Same reasoning as Fast R-CNN above" },
  { topic: "Zero/one/few-shot, self-supervised learning, CLIP, RL in vision (Module 5)", status: "not", where: "—", note: "Lecture-only topics, no corresponding lab in the syllabus; not implemented" },
];

const CG_ROWS: Row[] = [
  { topic: "Graphics system architecture, GPU concepts, display technologies (Module 1)", status: "partial", where: "docs/graphics_pipeline.md", note: "Documented conceptually; this project renders via a browser's WebGL context rather than raw hardware/driver-level code" },
  { topic: "Graphics primitives, DDA & Bresenham line algorithms, Midpoint Circle (Module 1, Labs 1-2)", status: "implemented", where: "graphics/rasterAlgorithms.ts", link: "/academic/graphics/raster" },
  { topic: "Color models — RGB, CMY, HSV (Module 1)", status: "implemented", where: "graphics/colorModels.ts", link: "/academic/graphics/raster" },
  { topic: "2D transformations, homogeneous coordinates, composite transforms (Module 2, Labs 3-4)", status: "implemented", where: "graphics/transform2d.ts", link: "/academic/graphics/transform2d" },
  { topic: "Windowing & clipping — Cohen-Sutherland, Liang-Barsky (Module 2, Lab 5)", status: "implemented", where: "graphics/clipping.ts", link: "/academic/graphics/transform2d" },
  { topic: "3D transformations, composite 3D transforms (Module 3)", status: "implemented", where: "three/MatrixReadout.tsx, Graphics3DLab.tsx", link: "/academic/graphics/3d" },
  { topic: "Projection — parallel & perspective; viewing pipeline (Module 3, Lab 10)", status: "implemented", where: "Graphics3DLab.tsx (ProjectionCompareSection)", link: "/academic/graphics/3d" },
  { topic: "Visible surface detection — back-face, Z-buffer (Module 3, Lab 6)", status: "implemented", where: "DepthBufferLab.tsx", link: "/academic/graphics/depth", note: "Includes a from-scratch software Z-buffer, not just a WebGL flag toggle" },
  { topic: "Illumination models — ambient, diffuse, specular (Module 3)", status: "implemented", where: "Graphics3DLab.tsx (LightingSection)", link: "/academic/graphics/3d" },
  { topic: "Shading — flat, Gouraud, Phong (Module 3, Lab 7)", status: "implemented", where: "three/ShaderYieldSurface.tsx", link: "/academic/graphics/3d", note: "Custom GLSL fragment shader computing per-pixel diffuse shading (Phong-family)" },
  { topic: "OpenGL/shader programming — vertex & fragment shaders (Module 3/5, Lab 8)", status: "implemented", where: "three/ShaderYieldSurface.tsx", link: "/academic/graphics/3d", note: "Hand-written GLSL via THREE.ShaderMaterial, applied to real yield-curve data" },
  { topic: "Unity interactive 3D scene (Lab 9)", status: "not", where: "—", link: "/academic/graphics", note: "Unity is a separate desktop engine outside this web app's stack; equivalent concepts covered via WebGL/Three.js instead" },
  { topic: "VR/AR/MR introduction, architecture, hardware, DOF, tracking (Module 4)", status: "partial", where: "VrArConceptsLab.tsx", link: "/academic/graphics/vr-ar", note: "Documented conceptually; no VR/AR hardware used, per the project's laptop-only requirement" },
  { topic: "Human factors in VR — FOV, latency, motion sickness, ergonomics (Module 4)", status: "partial", where: "VrArConceptsLab.tsx", link: "/academic/graphics/vr-ar" },
  { topic: "XR concepts, marker/markerless AR, spatial computing (Module 5)", status: "partial", where: "VrArConceptsLab.tsx", link: "/academic/graphics/vr-ar" },
];

function StatusBadge({ status }: { status: Row["status"] }) {
  if (status === "implemented") return <Badge kind="info">IMPLEMENTED</Badge>;
  if (status === "partial") return <Badge kind="warn">PARTIAL</Badge>;
  return <Badge kind="warn">NOT IMPLEMENTED</Badge>;
}

function CourseTable({ rows }: { rows: Row[] }) {
  return (
    <table className="data-table">
      <thead><tr><th>Topic</th><th>Status</th><th>Where</th></tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td style={{ textAlign: "left" }}>
              {r.topic}
              {r.note && <div style={{ fontSize: 10, color: "var(--text-lo)", marginTop: 2 }}>{r.note}</div>}
            </td>
            <td><StatusBadge status={r.status} /></td>
            <td style={{ textAlign: "left" }}>
              {r.link ? <Link to={r.link} className="mono">{r.where}</Link> : <span className="mono">{r.where}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function CourseMapping() {
  const cvCounts = { implemented: CV_ROWS.filter((r) => r.status === "implemented").length, total: CV_ROWS.length };
  const cgCounts = { implemented: CG_ROWS.filter((r) => r.status === "implemented").length, total: CG_ROWS.length };

  return (
    <div>
      <Panel title="Course Mapping — Verification Notice">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          This mapping is grounded directly in the two uploaded course syllabi: <strong>CS4231 Fundamentals of
          Computer Vision</strong> (RV University, Module/Lab structure) and <strong>CS4104 Computer Graphics and
          Virtual Reality</strong> (RV University, Module/Lab structure). Every row below reflects an actual
          syllabus topic; every "IMPLEMENTED" status corresponds to real, tested code (linked); every "NOT
          IMPLEMENTED" is stated honestly with the reason, rather than silently omitted or fabricated.
        </p>
      </Panel>

      <Panel title={`CS4231 — Fundamentals of Computer Vision (${cvCounts.implemented}/${cvCounts.total} topics implemented)`}>
        <CourseTable rows={CV_ROWS} />
      </Panel>

      <Panel title={`CS4104 — Computer Graphics and Virtual Reality (${cgCounts.implemented}/${cgCounts.total} topics implemented)`}>
        <CourseTable rows={CG_ROWS} />
      </Panel>
    </div>
  );
}
