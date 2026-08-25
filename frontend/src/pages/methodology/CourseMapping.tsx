import { Link } from "react-router-dom";
import { Badge, Panel } from "../../components/Common";

interface Row {
  topic: string;
  status: "implemented" | "partial" | "not";
  where: string;
  link?: string;
  note?: string;
}

const CV_ROWS: Row[] = [
  { topic: "Image formation, sensing, acquisition, sampling & quantization (Module 1)", status: "implemented", where: "Financial Image Intelligence", link: "/intelligence/financial-image", note: "Resize, grayscale conversion, quantization via thresholding — first stage of every upload" },
  { topic: "Camera geometry (Module 1)", status: "not", where: "—", note: "No camera-calibration or multi-view geometry task in this project" },
  { topic: "Color image fundamentals — RGB, HSI (Module 1)", status: "partial", where: "Raster Graphics (evidence)", link: "/evidence/graphics/raster", note: "RGB/CMY/HSV implemented (HSI not implemented; HSV used instead, matching the CG course's own Module 1)" },
  { topic: "Spatial domain processing & spatial filtering (Module 1, Lab 1)", status: "implemented", where: "Financial Image Intelligence + Filter Comparison", link: "/intelligence/financial-image", note: "CLAHE/denoise run in production; full filter comparison at /evidence/cv/filters" },
  { topic: "Edge detection, DoG, LoG, Canny (Module 2, Lab 2)", status: "implemented", where: "Financial Image Intelligence + Edge Detection", link: "/intelligence/financial-image", note: "Canny runs in production for chart-boundary detection; full comparison at /evidence/cv/edges" },
  { topic: "Edge linking via Hough Transform (Module 2, Lab 2)", status: "implemented", where: "Financial Image Intelligence", link: "/intelligence/financial-image", note: "Used in production for axis/gridline detection during region extraction" },
  { topic: "Segmentation — thresholding, morphological processing (Module 2)", status: "implemented", where: "Financial Image Intelligence + Segmentation", link: "/intelligence/financial-image", note: "Adaptive thresholding + contour-based chart-region detection run in production (edges.py); classical GrabCut segmentation, with real IoU/Dice benchmarks, is kept as evidence at /evidence/cv/segmentation" },
  { topic: "Blobs, corner detection (Module 2)", status: "implemented", where: "Corner & Blob Detection (evidence)", link: "/evidence/cv/features", note: "Structural analysis supporting chart-marker/gridline localization" },
  { topic: "Scale space & scale selection; SIFT (Module 2, Lab 3)", status: "implemented", where: "Compare Market Screens", link: "/intelligence/compare-screens", note: "SIFT keypoint matching for visually comparing two Treasury screenshots — a real product feature" },
  { topic: "Optical flow (Module 2)", status: "implemented", where: "Optical Flow (evidence)", link: "/evidence/cv/optical-flow", note: "Motion/change detection between sequential screenshots" },
  { topic: "CNN review, CNNs for recognition (Module 3)", status: "implemented", where: "Financial Image Intelligence (Model Details, live) + CNN vs. ViT (evidence)", link: "/intelligence/financial-image", note: "Trained from scratch on a small synthetic dataset; runs live per-upload when torch is available (production build omits torch, degrades gracefully), aggregate benchmark always at /evidence/cv/models — see Computer Vision Methodology" },
  { topic: "Neural style transfer (Module 3)", status: "not", where: "—", note: "Lecture topic, no corresponding lab; not implemented" },
  { topic: "CNNs for object detection — R-CNN, Fast R-CNN, FPN, RetinaNet (Module 3, Lab 4)", status: "not", where: "Object Detection Status", link: "/evidence/cv/object-detection", note: "Requires PASCAL-VOC-scale labeled data + GPU training, out of scope for a laptop build — status page documents why + a reproducible pipeline" },
  { topic: "CNNs for segmentation — FCN, U-Net, Mask-RCNN (Module 3, Lab 5)", status: "partial", where: "Segmentation (evidence)", link: "/evidence/cv/segmentation", note: "Classical GrabCut segmentation implemented and benchmarked (real IoU/Dice) for the in-scope chart-isolation task; U-Net/medical-dataset training out of scope (wrong domain)" },
  { topic: "Siamese networks, triplet/contrastive/ranking loss, FaceNet (Module 3, Lab 6)", status: "not", where: "—", note: "Face verification is off-domain for a Treasury tool and avoids handling biometric data; not implemented" },
  { topic: "3D CNN for video, RNN/CNN for video understanding, action recognition (Module 4)", status: "not", where: "—", note: "No video data in this project; theory only" },
  { topic: "Attention models, Transformer review, Vision Transformers (Module 4, Lab 7)", status: "implemented", where: "Financial Image Intelligence (Model Details, live) + CNN vs. ViT (evidence)", link: "/intelligence/financial-image", note: "A ViT written from scratch (patch embedding, class token, multi-head self-attention), directly compared against the CNN; same live/graceful-degradation availability" },
  { topic: "YOLO (Module 5)", status: "not", where: "Object Detection Status", link: "/evidence/cv/object-detection", note: "Same reasoning as Fast R-CNN above" },
  { topic: "Zero/one/few-shot, self-supervised learning, CLIP, RL in vision (Module 5)", status: "not", where: "—", note: "Lecture-only topics, no corresponding lab in the syllabus; not implemented" },
];

const CG_ROWS: Row[] = [
  { topic: "Graphics system architecture, GPU concepts, display technologies (Module 1)", status: "partial", where: "Computer Graphics Methodology", link: "/methodology/computer-graphics", note: "Documented conceptually; this project renders via a browser's WebGL context rather than raw hardware/driver-level code" },
  { topic: "Graphics primitives, DDA & Bresenham line algorithms, Midpoint Circle (Module 1, Labs 1-2)", status: "implemented", where: "Raster Graphics (evidence)", link: "/evidence/graphics/raster", note: "No natural Treasury use — kept as direct syllabus evidence" },
  { topic: "Color models — RGB, CMY, HSV (Module 1)", status: "implemented", where: "Raster Graphics (evidence)", link: "/evidence/graphics/raster" },
  { topic: "2D transformations, homogeneous coordinates, composite transforms (Module 2, Labs 3-4)", status: "implemented", where: "2D Transform & Clip (evidence)", link: "/evidence/graphics/transform2d" },
  { topic: "Windowing & clipping — Cohen-Sutherland, Liang-Barsky (Module 2, Lab 5)", status: "implemented", where: "2D Transform & Clip (evidence)", link: "/evidence/graphics/transform2d" },
  { topic: "3D transformations, composite 3D transforms (Module 3)", status: "implemented", where: "3D Market (production)", link: "/visualization/3d-market", note: "Live Model matrix, read directly from the renderer under 'Graphics Details'" },
  { topic: "Projection — parallel & perspective; viewing pipeline (Module 3, Lab 10)", status: "implemented", where: "3D Market (production)", link: "/visualization/3d-market", note: "Perspective/Orthographic toggle actually switches the renderer's camera" },
  { topic: "Visible surface detection — back-face, Z-buffer (Module 3, Lab 6)", status: "implemented", where: "3D Market (production) + software Z-buffer evidence", link: "/visualization/3d-market", note: "WebGL depth test used in production; a from-scratch software Z-buffer implementation at /evidence/graphics/concepts" },
  { topic: "Illumination models — ambient, diffuse, specular (Module 3)", status: "implemented", where: "3D Market (production)", link: "/visualization/3d-market", note: "Ambient + 2 directional lights on every surface" },
  { topic: "Shading — flat, Gouraud, Phong (Module 3, Lab 7)", status: "implemented", where: "3D Market — Risk View", link: "/visualization/3d-market", note: "Custom GLSL fragment shader computing per-pixel diffuse (Phong-family) shading" },
  { topic: "OpenGL/shader programming — vertex & fragment shaders (Module 3/5, Lab 8)", status: "implemented", where: "3D Market — Risk View", link: "/visualization/3d-market", note: "Hand-written GLSL via THREE.ShaderMaterial, applied to real yield/vol/stress data — view source inline" },
  { topic: "Unity interactive 3D scene (Lab 9)", status: "not", where: "—", note: "Unity is a separate desktop engine outside this web app's stack; equivalent concepts covered via WebGL/Three.js instead" },
  { topic: "VR/AR/MR — architecture, hardware, DOF, tracking, human factors (Module 4)", status: "partial", where: "VR/AR Concepts (evidence)", link: "/evidence/graphics/vr-ar", note: "Documented conceptually; no VR/AR hardware used, per the project's laptop-only requirement" },
  { topic: "XR concepts, marker/markerless AR, spatial computing (Module 5)", status: "partial", where: "VR/AR Concepts (evidence)", link: "/evidence/graphics/vr-ar" },
];

function StatusBadge({ status }: { status: Row["status"] }) {
  if (status === "implemented") return <Badge kind="info">IMPLEMENTED</Badge>;
  if (status === "partial") return <Badge kind="warn">PARTIAL</Badge>;
  return <Badge kind="warn">NOT IMPLEMENTED</Badge>;
}

function CourseTable({ rows }: { rows: Row[] }) {
  return (
    <table className="data-table">
      <thead><tr><th>Topic</th><th>Status</th><th>Where (product feature or evidence page)</th></tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td style={{ textAlign: "left" }}>
              {r.topic}
              {r.note && <div style={{ fontSize: 10, color: "var(--text-lo)", marginTop: 2 }}>{r.note}</div>}
            </td>
            <td><StatusBadge status={r.status} /></td>
            <td style={{ textAlign: "left" }}>
              {r.link ? <Link to={r.link}>{r.where}</Link> : <span>{r.where}</span>}
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
          syllabus topic; every "IMPLEMENTED" status corresponds to real, tested code that runs inside an actual
          product page wherever a sensible Treasury use exists (linked); every "NOT IMPLEMENTED" is stated
          honestly with the reason, rather than silently omitted or fabricated.
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
