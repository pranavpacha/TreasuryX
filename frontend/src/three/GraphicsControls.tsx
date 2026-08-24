import { useState } from "react";
import { Badge } from "../components/Common";
import type { GraphicsMatrices } from "./SurfacePlot";
import { MatrixReadout } from "./MatrixReadout";

export interface Treasury3DState {
  renderMode: "material" | "shader";
  projectionMode: "perspective" | "orthographic";
  threshold: number;
  matrices: GraphicsMatrices | null;
}

export function useTreasury3DState(initialThreshold = 0.6) {
  const [renderMode, setRenderMode] = useState<"material" | "shader">("material");
  const [projectionMode, setProjectionMode] = useState<"perspective" | "orthographic">("perspective");
  const [threshold, setThreshold] = useState(initialThreshold);
  const [matrices, setMatrices] = useState<GraphicsMatrices | null>(null);
  return { renderMode, setRenderMode, projectionMode, setProjectionMode, threshold, setThreshold, matrices, setMatrices };
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
  const { renderMode, setRenderMode, projectionMode, setProjectionMode, threshold, setThreshold, matrices } = state;

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
        {renderMode === "shader" && (
          <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
            {onThresholdLabel}: {threshold.toFixed(2)}
            <input type="range" min={0} max={1} step={0.01} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          </label>
        )}
        <Badge kind="info">FOCV/CGVR-powered</Badge>
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
                  <tr><td style={{ textAlign: "left" }}>Depth test</td><td style={{ textAlign: "left" }}>ON, function LESS (WebGL default z-buffer)</td></tr>
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
          <div><strong>Model transform:</strong> vertices are placed in world space (identity local transform for this mesh).</div>
          <div><strong>View transform:</strong> OrbitControls maintains the camera position/target; Three.js derives the view matrix every frame.</div>
          <div><strong>Projection:</strong> {projectionMode === "perspective" ? "perspective (distant points appear smaller)" : "orthographic (parallel lines stay parallel, size is distance-independent)"}.</div>
          <div><strong>Depth:</strong> the WebGL depth buffer resolves which surface/wireframe/marker pixels are visible.</div>
          <div><strong>Lighting/shading:</strong> {renderMode === "material" ? "per-vertex color (mapped from the data value) is modulated by ambient + directional lighting via a standard PBR-lite material." : "the fragment shader recomputes color per-pixel from height vs. the risk threshold, blended with a diffuse lighting term computed from the surface normal and an animated light direction."}</div>
        </div>
      </details>
    </div>
  );
}
