# Computer Graphics Pipeline

Two layers of graphics work exist in this project:

1. **The integrated 3D Market visualization** (`frontend/src/three/SurfacePlot.tsx`), used by the
   three 3D views on the "3D Market" page (yield-curve surface, FX volatility surface, portfolio
   stress surface) — always driven by real Treasury-engine data.
2. **The Academic Mode Graphics Lab** (`frontend/src/pages/graphics-lab/`, `frontend/src/graphics/`),
   which implements the CS4104 syllabus's lower-level algorithms explicitly (raster line/circle
   drawing, homogeneous-coordinate 2D transforms, line clipping, a from-scratch software Z-buffer,
   and a hand-written GLSL shader) — see [ACADEMIC_MAPPING.md](../ACADEMIC_MAPPING.md) for the
   full syllabus cross-reference.

This document covers (1); see below for a summary of (2).

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

`SurfacePlot.tsx` itself uses built-in materials (`MeshStandardMaterial`, `LineBasicMaterial`,
`MeshBasicMaterial`) — sufficient for the integrated 3D Market views. A genuine **custom GLSL
shader** (hand-written vertex + fragment shader via `THREE.ShaderMaterial`) was written separately
for the Academic Mode Graphics Lab — see below.

## VR

No VR/head-mounted-display support is implemented, matching the project spec's requirement that this
run on a normal laptop without specialized hardware — all interaction is mouse/trackpad-driven. The
syllabus's VR/AR/XR modules (4-5) are documented conceptually only, at
`frontend/src/pages/graphics-lab/VrArConceptsLab.tsx`.

---

## Academic Mode Graphics Lab (CS4104 low-level algorithms)

Unlike the WebGL-based 3D Market views above, these implement the syllabus's foundational
algorithms explicitly, in code the browser's GPU/canvas API does NOT normally expose:

- **Raster graphics** (`frontend/src/graphics/rasterAlgorithms.ts`) — DDA and Bresenham line
  algorithms, and the Midpoint Circle algorithm, each implemented as an explicit pixel-generation
  function (not delegated to `<canvas>`'s built-in `lineTo`/`arc`) and rendered pixel-by-pixel via
  `PixelCanvas.tsx` on a discrete grid.
- **2D transformations** (`frontend/src/graphics/transform2d.ts`) — translation, rotation, scaling,
  reflection, and shear as explicit 3x3 homogeneous-coordinate matrices, with real matrix
  multiplication (`multiply3`) for composing them; the live composite matrix is displayed and
  actually used to transform the on-screen shape (`Transform2DLab.tsx`).
- **Line clipping** (`frontend/src/graphics/clipping.ts`) — both Cohen-Sutherland (outcode-based,
  iterative boundary clipping) and Liang-Barsky (parametric range clipping), with a step-by-step
  log of each algorithm's decisions shown in the UI so the two approaches can be compared directly.
- **3D transformations & the MVP pipeline** (`frontend/src/three/MatrixReadout.tsx`,
  `Graphics3DLab.tsx`) — the actual Model, View, and Projection matrices Three.js computes for a
  live-manipulated 3D object are read out and displayed (`matrixWorld`, `matrixWorldInverse`,
  `projectionMatrix`), not simulated or hand-typed.
- **Camera & projection comparison** — perspective vs. orthographic cameras rendering the identical
  scene side by side, with an adjustable FOV slider on the perspective camera.
- **Illumination & shading** — ambient + directional light intensity sliders on a lit sphere, with
  a wireframe toggle to inspect the underlying geometry.
- **Depth buffer / Z-buffer** (`DepthBufferLab.tsx`) — two demonstrations: (a) a **from-scratch
  software Z-buffer** implemented as a literal per-pixel depth-comparison loop over a JS
  `Float32Array` depth buffer and a `Uint8ClampedArray` color buffer, rasterizing two overlapping
  rectangles so the nearer one correctly wins regardless of draw order; and (b) a WebGL
  `depthTest` on/off toggle on two overlapping 3D planes, showing what breaks without it.
- **Custom GLSL shader** (`frontend/src/three/ShaderYieldSurface.tsx`) — a hand-written vertex
  shader (passes normalized height + transformed normal to the fragment stage) and fragment shader
  (blends two colors based on an interactive `uThreshold` uniform, then applies a simple
  Blinn-Phong-family diffuse term from a rotating light direction) via `THREE.ShaderMaterial`,
  driving a surface built from **real yield-curve data** fetched from the Treasury API. The GLSL
  source is viewable in the UI.
- **RGB/CMY/HSV color models** (`frontend/src/graphics/colorModels.ts`) — bidirectional conversions
  with a live round-trip check, per the syllabus's Module 1 color-models topic.
