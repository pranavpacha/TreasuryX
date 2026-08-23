import { Panel } from "../components/Common";

export function GraphicsInfoPanel() {
  return (
    <Panel title="Graphics Info — Rendering Pipeline">
      <table className="data-table" style={{ fontSize: 11 }}>
        <tbody>
          <tr><td style={{ textAlign: "left" }}>Rendering API</td><td style={{ textAlign: "left" }}>WebGL via Three.js, declaratively wired through @react-three/fiber</td></tr>
          <tr><td style={{ textAlign: "left" }}>Geometry</td><td style={{ textAlign: "left" }}>Custom THREE.BufferGeometry built per-frame-data from a position/color/index buffer (not a canned chart primitive) — a triangulated grid mesh</td></tr>
          <tr><td style={{ textAlign: "left" }}>Object → World transform</td><td style={{ textAlign: "left" }}>Data values are mapped to object-space (x = category index, y = normalized magnitude "height", z = second category index), then to world space via the mesh's implicit identity transform (single group, no nesting)</td></tr>
          <tr><td style={{ textAlign: "left" }}>World → Camera (view) transform</td><td style={{ textAlign: "left" }}>OrbitControls maintains the camera's position/target and derives the view matrix every frame (look-at transform)</td></tr>
          <tr><td style={{ textAlign: "left" }}>Camera model / Projection</td><td style={{ textAlign: "left" }}>Perspective projection, 45° vertical FOV, near=0.1 far=100 — produces true depth perspective (closer grid points appear larger)</td></tr>
          <tr><td style={{ textAlign: "left" }}>Depth handling</td><td style={{ textAlign: "left" }}>WebGL depth buffer (z-buffer) test, enabled by default in Three.js's WebGLRenderer, resolves surface vs. wireframe vs. marker occlusion</td></tr>
          <tr><td style={{ textAlign: "left" }}>Lighting / shading</td><td style={{ textAlign: "left" }}>Two directional lights (key + fill) + ambient light, Lambert/Standard (PBR-lite) shading via MeshStandardMaterial with flatShading for a faceted terminal look; per-vertex color is computed from the data value (a simple diverging/sequential colormap), then modulated by the lighting model</td></tr>
          <tr><td style={{ textAlign: "left" }}>Materials</td><td style={{ textAlign: "left" }}>MeshStandardMaterial (surface, vertex colors), LineBasicMaterial (wireframe overlay), MeshBasicMaterial (unlit hover markers)</td></tr>
          <tr><td style={{ textAlign: "left" }}>Interaction</td><td style={{ textAlign: "left" }}>Raycasting (via r3f pointer events) against per-vertex marker meshes for hover tooltips; OrbitControls for rotate / zoom / pan</td></tr>
          <tr><td style={{ textAlign: "left" }}>Coordinate systems</td><td style={{ textAlign: "left" }}>Right-handed, Y-up (Three.js default) for object/world/camera space</td></tr>
        </tbody>
      </table>
    </Panel>
  );
}
