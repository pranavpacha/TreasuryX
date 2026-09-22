import { useState } from "react";
import { Badge } from "../components/Common";
import type { GraphicsMatrices } from "./SurfacePlot";
import { RISK_FRAGMENT_SHADER, RISK_VERTEX_SHADER } from "./SurfacePlot";
import { MatrixReadout } from "./MatrixReadout";

export interface Treasury3DState {
  renderMode: "material" | "shader";
  projectionMode: "perspective" | "orthographic";
  threshold: number;
  matrices: GraphicsMatrices | null;
  rotationXDeg: number;
  rotationYDeg: number;
  rotationZDeg: number;
  verticalScale: number;
  displayMode: "surface" | "wireframe" | "both";
  showNormals: boolean;
}

export function useTreasury3DState(initialThreshold = 0.6) {
  const [renderMode, setRenderMode] = useState<"material" | "shader">("material");
  const [projectionMode, setProjectionMode] = useState<"perspective" | "orthographic">("perspective");
  const [threshold, setThreshold] = useState(initialThreshold);
  const [matrices, setMatrices] = useState<GraphicsMatrices | null>(null);
  const [rotationXDeg, setRotationXDeg] = useState(0);
  const [rotationYDeg, setRotationYDeg] = useState(0);
  const [rotationZDeg, setRotationZDeg] = useState(0);
  const [verticalScale, setVerticalScale] = useState(1);
  const [displayMode, setDisplayMode] = useState<"surface" | "wireframe" | "both">("both");
  const [showNormals, setShowNormals] = useState(false);
  const resetTransform = () => { setRotationXDeg(0); setRotationYDeg(0); setRotationZDeg(0); setVerticalScale(1); };
  return {
    renderMode, setRenderMode, projectionMode, setProjectionMode, threshold, setThreshold, matrices, setMatrices,
    rotationXDeg, setRotationXDeg, rotationYDeg, setRotationYDeg, rotationZDeg, setRotationZDeg,
    verticalScale, setVerticalScale, displayMode, setDisplayMode, showNormals, setShowNormals, resetTransform,
  };
}

/** Real production controls for a 3D Treasury view: Market/Risk render mode (swaps between the
 * standard material and the actual custom GLSL shader), perspective/orthographic projection,
 * plus two inline technical-evidence disclosures (live matrices, and a plain-English trace of
 * the rendering pipeline) -- this is how the CGVR coursework stays visible inside the real
 * product instead of a separate lab. */
export function Treasury3DControls({
  state, dataMapping, onThresholdLabel = "Risk threshold",
}: {
  state: ReturnType<typeof useTreasury3DState>;
  dataMapping: { source: string; xMapping: string; yMapping: string; zMapping: string };
  onThresholdLabel?: string;
}) {
  const {
    renderMode, setRenderMode, projectionMode, setProjectionMode, threshold, setThreshold, matrices,
    rotationXDeg, setRotationXDeg, rotationYDeg, setRotationYDeg, rotationZDeg, setRotationZDeg,
    verticalScale, setVerticalScale, displayMode, setDisplayMode, showNormals, setShowNormals, resetTransform,
  } = state;
  const transformIsIdentity = rotationXDeg === 0 && rotationYDeg === 0 && rotationZDeg === 0 && verticalScale === 1;

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 4, overflow: "hidden" }}>
          <button onClick={() => setRenderMode("material")} style={{ border: "none", borderRadius: 0, background: renderMode === "material" ? "var(--accent)" : "var(--bg-2)", color: renderMode === "material" ? "white" : "var(--text-mid)" }}>Market View</button>
          <button onClick={() => setRenderMode("shader")} style={{ border: "none", borderRadius: 0, background: renderMode === "shader" ? "var(--accent)" : "var(--bg-2)", color: renderMode === "shader" ? "white" : "var(--text-mid)" }}>Risk View (GLSL shader)</button>
        </div>
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 4, overflow: "hidden" }}>
          <button onClick={() => setProjectionMode("perspective")} style={{ border: "none", borderRadius: 0, background: projectionMode === "perspective" ? "var(--accent)" : "var(--bg-2)", color: projectionMode === "perspective" ? "white" : "var(--text-mid)" }}>Perspective</button>
          <button onClick={() => setProjectionMode("orthographic")} style={{ border: "none", borderRadius: 0, background: projectionMode === "orthographic" ? "var(--accent)" : "var(--bg-2)", color: projectionMode === "orthographic" ? "white" : "var(--text-mid)" }}>Orthographic</button>
        </div>
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 4, overflow: "hidden" }}>
          <button onClick={() => setDisplayMode("surface")} style={{ border: "none", borderRadius: 0, background: displayMode === "surface" ? "var(--accent)" : "var(--bg-2)", color: displayMode === "surface" ? "white" : "var(--text-mid)" }}>Surface</button>
          <button onClick={() => setDisplayMode("wireframe")} style={{ border: "none", borderRadius: 0, background: displayMode === "wireframe" ? "var(--accent)" : "var(--bg-2)", color: displayMode === "wireframe" ? "white" : "var(--text-mid)" }}>Wireframe</button>
          <button onClick={() => setDisplayMode("both")} style={{ border: "none", borderRadius: 0, background: displayMode === "both" ? "var(--accent)" : "var(--bg-2)", color: displayMode === "both" ? "white" : "var(--text-mid)" }}>Both</button>
        </div>
        {renderMode === "shader" && (
          <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
            {onThresholdLabel}: {threshold.toFixed(2)}
            <input type="range" min={0} max={1} step={0.01} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          </label>
        )}
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
          <input type="checkbox" checked={showNormals} onChange={(e) => setShowNormals(e.target.checked)} /> Show normals
        </label>
        <Badge kind="info">FOCV/CGVR-powered</Badge>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "center", marginBottom: 8, fontSize: 11, color: "var(--text-mid)" }}>
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          Rotation X: {rotationXDeg}°
          <input type="range" min={-180} max={180} step={5} value={rotationXDeg} onChange={(e) => setRotationXDeg(Number(e.target.value))} />
        </label>
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          Rotation Y: {rotationYDeg}°
          <input type="range" min={-180} max={180} step={5} value={rotationYDeg} onChange={(e) => setRotationYDeg(Number(e.target.value))} />
        </label>
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          Rotation Z: {rotationZDeg}°
          <input type="range" min={-180} max={180} step={5} value={rotationZDeg} onChange={(e) => setRotationZDeg(Number(e.target.value))} />
        </label>
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          Vertical scale: {verticalScale.toFixed(2)}×
          <input type="range" min={0.5} max={3} step={0.05} value={verticalScale} onChange={(e) => setVerticalScale(Number(e.target.value))} />
        </label>
        {!transformIsIdentity && <button onClick={resetTransform}>Reset transform</button>}
      </div>

      <details style={{ marginBottom: 6 }}>
        <summary style={{ cursor: "pointer", fontSize: 11, color: "var(--text-mid)" }}>Graphics Details</summary>
        <div className="panel" style={{ marginTop: 6 }}>
          <div className="grid grid-2">
            <div>
              <table className="data-table">
                <tbody>
                  <tr><td style={{ textAlign: "left" }}>Projection</td><td style={{ textAlign: "left" }}>{projectionMode === "perspective" ? "Perspective (FOV 45°, near 0.1, far 100)" : "Orthographic (zoom 45, near 0.1, far 100)"}</td></tr>
                  <tr><td style={{ textAlign: "left" }}>Render mode</td><td style={{ textAlign: "left" }}>{renderMode === "material" ? "MeshStandardMaterial (PBR-lite)" : "Custom GLSL ShaderMaterial"}</td></tr>
                  <tr><td style={{ textAlign: "left" }}>Depth test (live)</td><td style={{ textAlign: "left" }}>{matrices ? `${matrices.depthTest ? "ON" : "OFF"}, function ${matrices.depthFuncName} (read from the active material)` : "pending first frame..."}</td></tr>
                  <tr><td style={{ textAlign: "left" }}>Lighting</td><td style={{ textAlign: "left" }}>Ambient + 2 directional lights{renderMode === "shader" ? " (1 animated, feeding the shader's diffuse term)" : ""}</td></tr>
                  <tr><td style={{ textAlign: "left" }}>Coordinate system</td><td style={{ textAlign: "left" }}>Right-handed, Y-up</td></tr>
                </tbody>
              </table>
            </div>
            <div>
              {matrices ? (
                <>
                  <MatrixReadout label="Model matrix (live)" matrix={matrices.model} />
                  <MatrixReadout label="View matrix (live)" matrix={matrices.view} />
                  <MatrixReadout label="Projection matrix (live)" matrix={matrices.projection} />
                </>
              ) : (
                <div style={{ fontSize: 11, color: "var(--text-lo)" }}>Matrices update once the scene renders its first frame.</div>
              )}
            </div>
          </div>
        </div>
      </details>

      <details>
        <summary style={{ cursor: "pointer", fontSize: 11, color: "var(--text-mid)" }}>Explain This Visualization</summary>
        <div className="panel" style={{ marginTop: 6, fontSize: 11.5, color: "var(--text-mid)", lineHeight: 1.7 }}>
          <div><strong>Data source:</strong> {dataMapping.source}</div>
          <div><strong>Data mapping:</strong> X = {dataMapping.xMapping} · Height (Y) = {dataMapping.yMapping} · Z (depth) = {dataMapping.zMapping}</div>
          <div><strong>Geometry:</strong> a triangulated grid mesh is built directly from the data above (one vertex per data point).</div>
          <div><strong>Model transform:</strong> {transformIsIdentity
            ? "identity by default -- use the Rotation X/Y/Z and Vertical scale controls above to apply a real transform and watch the Model matrix change below."
            : `rotation (${rotationXDeg}°, ${rotationYDeg}°, ${rotationZDeg}°) and ${verticalScale.toFixed(2)}× vertical scale, composed live into the Model matrix below (see the group wrapping the mesh in SurfacePlot.tsx).`}</div>
          <div><strong>View transform:</strong> OrbitControls maintains the camera position/target; Three.js derives the view matrix every frame.</div>
          <div><strong>Projection:</strong> {projectionMode === "perspective" ? "perspective (distant points appear smaller)" : "orthographic (parallel lines stay parallel, size is distance-independent)"}.</div>
          <div><strong>Depth:</strong> the WebGL depth buffer resolves which surface/wireframe/marker pixels are visible.</div>
          <div><strong>Lighting/shading:</strong> {renderMode === "material" ? "per-vertex color (mapped from the data value) is modulated by ambient + directional lighting via a standard PBR-lite material." : "the fragment shader recomputes color per-pixel from height vs. the risk threshold, blended with a diffuse lighting term computed from the surface normal and an animated light direction."}</div>
        </div>
      </details>

      {renderMode === "shader" && (
        <details>
          <summary style={{ cursor: "pointer", fontSize: 11, color: "var(--text-mid)" }}>View Shader (GLSL source, actually running)</summary>
          <div className="panel" style={{ marginTop: 6 }}>
            <div style={{ fontSize: 10.5, color: "var(--text-lo)", marginBottom: 4 }}>Vertex shader</div>
            <pre className="mono" style={{ fontSize: 10.5, whiteSpace: "pre-wrap", color: "var(--text-mid)", margin: 0 }}>{RISK_VERTEX_SHADER.trim()}</pre>
            <div style={{ fontSize: 10.5, color: "var(--text-lo)", margin: "8px 0 4px" }}>Fragment shader</div>
            <pre className="mono" style={{ fontSize: 10.5, whiteSpace: "pre-wrap", color: "var(--text-mid)", margin: 0 }}>{RISK_FRAGMENT_SHADER.trim()}</pre>
          </div>
        </details>
      )}
    </div>
  );
}
