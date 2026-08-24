import { Link } from "react-router-dom";
import { Badge, Panel } from "../../components/Common";

const LABS = [
  { to: "/academic/graphics/raster", label: "1. Raster Graphics", desc: "DDA, Bresenham, Midpoint Circle -- implemented pixel-by-pixel, plus RGB/CMY/HSV color models.", status: "implemented" },
  { to: "/academic/graphics/transform2d", label: "2. 2D Transformations & Clipping", desc: "Homogeneous-coordinate matrices, composite transforms, Cohen-Sutherland & Liang-Barsky line clipping.", status: "implemented" },
  { to: "/academic/graphics/3d", label: "3. 3D Transformations, Camera, Lighting, Shader", desc: "Live Model/View/Projection matrices, perspective vs orthographic, illumination model, a hand-written GLSL shader on real yield data.", status: "implemented" },
  { to: "/academic/graphics/depth", label: "4. Depth Buffer (Z-buffer)", desc: "A from-scratch software Z-buffer implementation, plus a WebGL depth-test on/off comparison.", status: "implemented" },
  { to: "/3d", label: "5. 3D Market (integrated)", desc: "Yield curve, FX volatility, and portfolio stress surfaces -- the same graphics pipeline applied to real Treasury data.", status: "implemented" },
  { to: "/academic/graphics/vr-ar", label: "6. VR / AR / XR Concepts", desc: "Documented conceptually per the syllabus's Modules 4-5 -- no VR/AR hardware used.", status: "conceptual" },
];

const NOT_IMPLEMENTED = [
  "Unity-based interactive 3D scene (Lab-9) -- Unity is a standalone desktop game engine outside this web app's stack; the equivalent WebGL/Three.js labs cover the same underlying graphics concepts instead.",
  "Real VR/AR hardware integration (headset rendering, hand tracking, spatial anchors) -- by design, per the project's laptop-only requirement.",
];

export default function GraphicsLabHome() {
  return (
    <div>
      <Panel title="Computer Graphics Lab — CS4104 Computer Graphics and Virtual Reality">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Each lab below maps to a specific module/lab requirement from the course syllabus (see Course Mapping for
          the full table).
        </p>
      </Panel>
      <div className="grid grid-2">
        {LABS.map((lab) => (
          <Link key={lab.to} to={lab.to} style={{ textDecoration: "none" }}>
            <div className="panel" style={{ cursor: "pointer" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <strong style={{ fontSize: 13, color: "var(--text-hi)" }}>{lab.label}</strong>
                <Badge kind={lab.status === "implemented" ? "info" : "warn"}>{lab.status === "implemented" ? "IMPLEMENTED" : "CONCEPTUAL"}</Badge>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-mid)" }}>{lab.desc}</div>
            </div>
          </Link>
        ))}
      </div>
      <Panel title="Explicitly Not Implemented">
        <ul style={{ fontSize: 11.5, color: "var(--text-mid)", margin: 0, paddingLeft: 18 }}>
          {NOT_IMPLEMENTED.map((n, i) => <li key={i} style={{ marginBottom: 4 }}>{n}</li>)}
        </ul>
      </Panel>
    </div>
  );
}
