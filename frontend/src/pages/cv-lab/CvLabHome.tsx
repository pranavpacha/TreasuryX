import { Link } from "react-router-dom";
import { Badge, Panel } from "../../components/Common";

const LABS = [
  { to: "/vision", label: "1. Preprocessing & Integrated Pipeline", desc: "Resize/grayscale/denoise/CLAHE/threshold -> region detection -> OCR -> structured Treasury values. The main financial CV workflow.", status: "implemented" },
  { to: "/academic/cv/filters", label: "2. Filter Comparison", desc: "Gaussian, median, bilateral, CLAHE side by side.", status: "implemented" },
  { to: "/academic/cv/edges", label: "3. Edge Detection", desc: "Sobel, Laplacian, DoG, LoG, adjustable Canny.", status: "implemented" },
  { to: "/academic/cv/features", label: "4. Corners & Blobs", desc: "Harris corner detection, blob detection.", status: "implemented" },
  { to: "/academic/cv/sift", label: "5. SIFT Feature Matching", desc: "Keypoints, descriptors, ratio-test matching between two images.", status: "implemented" },
  { to: "/academic/cv/segmentation", label: "6. Segmentation", desc: "GrabCut chart-region isolation with real IoU/Dice on synthetic ground truth.", status: "implemented" },
  { to: "/academic/cv/optical-flow", label: "7. Optical Flow", desc: "Dense Farneback flow between two frames.", status: "implemented" },
  { to: "/academic/cv/models", label: "8. CNN vs. Vision Transformer", desc: "Two models trained from scratch on a synthetic chart-classification dataset, with real accuracy/precision/recall/F1/confusion-matrix metrics.", status: "implemented" },
  { to: "/academic/cv/object-detection", label: "9. Deep Object Detection", desc: "Fast R-CNN / FPN / RetinaNet / YOLO status and reproducible pipeline.", status: "not-trained" },
];

const NOT_IMPLEMENTED = [
  "FaceNet / Siamese networks / triplet loss (face verification -- off-domain for a Treasury tool, and avoids handling biometric face data)",
  "U-Net trained on a medical-imaging dataset (wrong domain; classical segmentation implemented instead for the in-scope chart-isolation task)",
  "Fast R-CNN on PASCAL VOC, FPN, RetinaNet, YOLO (require GPU-scale training + a large labeled dataset -- see the Object Detection lab's documented status)",
  "Zero/one/few-shot learning, self-supervised learning, CLIP, RL-in-vision (Q-learning/DQN) -- Module 5 lecture topics with no corresponding lab in the syllabus; theory only, not implemented",
  "3D CNN for video / RNN video understanding / action recognition -- Module 4 lecture topics, no corresponding lab, not implemented (no video data in this project)",
];

export default function CvLabHome() {
  return (
    <div>
      <Panel title="Computer Vision Lab — CS4231 Fundamentals of Computer Vision">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Each lab below maps to a specific module/lab requirement from the course syllabus (see Course Mapping for
          the full table). All results are computed on real images you upload -- nothing here is precomputed or
          faked, except where explicitly labeled.
        </p>
      </Panel>
      <div className="grid grid-2">
        {LABS.map((lab) => (
          <Link key={lab.to} to={lab.to} style={{ textDecoration: "none" }}>
            <div className="panel" style={{ cursor: "pointer" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <strong style={{ fontSize: 13, color: "var(--text-hi)" }}>{lab.label}</strong>
                <Badge kind={lab.status === "implemented" ? "info" : "warn"}>{lab.status === "implemented" ? "IMPLEMENTED" : "NOT TRAINED"}</Badge>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-mid)" }}>{lab.desc}</div>
            </div>
          </Link>
        ))}
      </div>
      <Panel title="Explicitly Not Implemented (syllabus topics out of scope for this build)">
        <ul style={{ fontSize: 11.5, color: "var(--text-mid)", margin: 0, paddingLeft: 18 }}>
          {NOT_IMPLEMENTED.map((n, i) => <li key={i} style={{ marginBottom: 4 }}>{n}</li>)}
        </ul>
      </Panel>
    </div>
  );
}
