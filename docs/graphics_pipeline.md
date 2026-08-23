# Computer Graphics Pipeline

Implemented in `frontend/src/three/SurfacePlot.tsx`, used by all three 3D views on the "3D Market"
page (yield-curve surface, FX volatility surface, portfolio stress surface). This is also
summarized live in-app via the "Graphics Info" panel (`GraphicsInfoPanel.tsx`).

## Why a custom surface, not a chart library

`SurfacePlot` builds a `THREE.BufferGeometry` directly from a `values[row][col]` grid — position,
color, and index buffers are constructed by hand (`buildGeometry`) rather than delegated to a canned
3D-charting package, so the transformation/lighting/camera pipeline is genuine, inspectable, and
directly tied to finance-engine output (never synthetic geometry unrelated to the numbers).

## Pipeline stages

1. **Geometry construction** — for a `rows × cols` data grid, each data point becomes one vertex:
   `x = column-index-normalized-to-width`, `z = row-index-normalized-to-depth`,
   `y = (value - min)/(max - min) * heightScale`. Triangles are built in row-major order (`indices`
   array), and `computeVertexNormals()` derives per-vertex normals for lighting.
2. **Coloring** — a per-vertex colormap (`colorFor`) is either **sequential** (blue → amber, for
   yield/vol surfaces) or **diverging**, centered at zero (red losses → green gains, for the P&L
   stress surface) — computed directly from the underlying financial value, then modulated by
   lighting when rendered.
3. **Object → World transform** — the mesh has an identity local transform (single flat group), so
   object space and world space coincide here; documented explicitly rather than left implicit.
4. **View (camera) transform** — `@react-three/drei`'s `OrbitControls` maintains camera
   position/target and derives the view (look-at) matrix every frame in response to user drag/scroll.
5. **Projection** — perspective camera, 45° vertical FOV, `near=0.1 far=100` (`Canvas camera={{...}}`),
   giving true perspective foreshortening (near points render larger).
6. **Depth handling** — WebGL's default depth buffer (z-buffer test) in Three.js's `WebGLRenderer`
   resolves occlusion between the surface mesh, its wireframe overlay, and the hover-marker spheres.
7. **Lighting / shading** — one ambient light + two directional lights (key + fill),
   `MeshStandardMaterial` with `flatShading` for a faceted terminal look; the material's shading model
   (Lambert/PBR-lite) combines the light directions with per-vertex normals and the data-driven vertex
   color.
8. **Interaction** — a low-poly sphere marker is placed at every grid vertex; `@react-three/fiber`
   pointer events (`onPointerOver`/`onPointerOut`) perform ray-mesh intersection tests against those
   markers to drive an `Html`-based tooltip (via `@react-three/drei`) showing the exact axis labels
   and value at the hovered point. `OrbitControls` additionally provides rotate/zoom/pan.

## Coordinate systems

Right-handed, Y-up throughout (Three.js's default convention) for object, world, and camera space —
stated explicitly rather than left as an unstated default.

## Shaders

No custom GLSL shaders were written for this build — `MeshStandardMaterial`, `LineBasicMaterial`,
and `MeshBasicMaterial` (all built into Three.js) were sufficient to express the required
lighting/shading and were judged the right complexity level for a laptop-scale educational surface
plot. This is stated explicitly rather than left ambiguous; no shader code is claimed anywhere else
in this project.

## VR

No VR/head-mounted-display support is implemented, matching the project spec's requirement that this
run on a normal laptop without specialized hardware — all interaction is mouse/trackpad-driven.
