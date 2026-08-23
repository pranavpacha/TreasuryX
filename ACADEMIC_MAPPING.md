# Academic Mapping

> **Verification notice (required honesty disclosure):** no Computer Vision or Computer Graphics/VR
> course syllabus documents were uploaded or made available in the session that built this project.
> Per the project's own anti-hallucination rule, this mapping therefore uses **standard, widely-taught
> terminology** for a typical 7th-semester "Fundamentals of Computer Vision" course and a typical
> "Computer Graphics and Visualization / VR" course, rather than inventing or guessing your specific
> syllabus's unit names, lab numbers, or exact terminology. **You must cross-check every row below
> against your actual syllabus before submitting** — some topics your course covers may not be listed
> here, and some listed here may use different names in your syllabus. Every row below only claims
> topics that are **actually implemented in this codebase** (file paths given for verification).

## Subject A — Computer Vision

| Standard CV Topic | Implemented? | Where | Notes |
|---|---|---|---|
| Image acquisition / I/O | Yes | [`backend/app/cv_engine/pipeline.py`](backend/app/cv_engine/pipeline.py) (`cv2.imdecode`) | Reads uploaded PNG/JPG/WEBP bytes |
| Preprocessing: resizing | Yes | [`preprocessing.py`](backend/app/cv_engine/preprocessing.py) `resize_keep_aspect` | Aspect-preserving resize, capped at 1400px |
| Preprocessing: grayscale conversion | Yes | `preprocessing.py` `preprocess()` | `cv2.cvtColor(..., COLOR_BGR2GRAY)` |
| Preprocessing: noise reduction / filtering | Yes | `preprocessing.py` | Non-local means denoising (`cv2.fastNlMeansDenoising`) |
| Contrast enhancement / histogram-based methods | Yes | `preprocessing.py` | CLAHE (adaptive histogram equalization) |
| Thresholding / binarization | Yes | `preprocessing.py` | Adaptive Gaussian threshold |
| Edge detection | Yes | [`edges.py`](backend/app/cv_engine/edges.py) `detect_edges` | Canny edge detector |
| Line detection | Yes | `edges.py` `detect_lines` | Probabilistic Hough transform (`HoughLinesP`) |
| Contour / region detection | Yes | `edges.py` `detect_chart_region` | `cv2.findContours` + bounding-rect heuristic |
| Feature extraction (structural) | Yes | `edges.py`, `pipeline.py` | Edge/line/contour features feed chart-region + classification |
| Optical Character Recognition (OCR) | Yes | [`ocr.py`](backend/app/cv_engine/ocr.py) | Tesseract via `pytesseract`, with graceful degradation + a documented warning if the binary is absent |
| Information extraction / text parsing | Yes | `ocr.py`, `pipeline.py` | Regex-based number/date/instrument extraction, nearest-neighbor field association |
| Image classification (rule-based) | Yes | `pipeline.py` `classify_chart_type` | Keyword-scoring classifier: fx_chart / yield_curve / report / unknown |
| Object detection (deep, e.g. YOLO) | **Not implemented** | — | Deliberately not used; see [docs/cv_pipeline.md](docs/cv_pipeline.md) for the documented reasoning (classical CV was judged more appropriate and more explainable for this text/line-dominated image domain) |
| Semantic/instance segmentation | **Not implemented** | — | Not required by the extraction task; not claimed |
| CNN / Vision Transformer feature extraction | **Not implemented** | — | Not used; not claimed |
| SIFT / classical keypoint matching | **Not implemented** | — | Not used; not claimed |
| Evaluation on varied image conditions | Yes | [`backend/tests/test_cv.py`](backend/tests/test_cv.py) | Synthetic clean, noisy (Gaussian), low-resolution, and low-contrast/blank ("difficult") test images |

## Subject B — Computer Graphics & Visualization / VR

| Standard Graphics Topic | Implemented? | Where | Notes |
|---|---|---|---|
| 3D geometry construction (vertices, faces) | Yes | [`frontend/src/three/SurfacePlot.tsx`](frontend/src/three/SurfacePlot.tsx) `buildGeometry` | Hand-built `THREE.BufferGeometry`: position/color/index buffers, not a canned chart primitive |
| Object-space → world-space transformation | Yes | `SurfacePlot.tsx` | Documented explicitly in the in-app Graphics Info panel and `docs/graphics_pipeline.md` |
| View (camera) transformation | Yes | `SurfacePlot.tsx` (`OrbitControls`) | Look-at/view matrix maintained by `@react-three/drei`'s `OrbitControls` |
| Projection (perspective) | Yes | `SurfacePlot.tsx` (`Canvas camera={{ fov: 45, near: 0.1, far: 100 }}`) | True perspective projection |
| Depth handling / hidden-surface removal | Yes | WebGL default depth buffer (Three.js `WebGLRenderer`) | Standard z-buffer test |
| Lighting / shading models | Yes | `SurfacePlot.tsx` (`ambientLight`, `directionalLight` x2, `MeshStandardMaterial`) | Ambient + two directional lights, flat-shaded standard (PBR-lite) material |
| Materials | Yes | `SurfacePlot.tsx` | `MeshStandardMaterial` (surface), `LineBasicMaterial` (wireframe), `MeshBasicMaterial` (markers) |
| Interactive 3D scene / user interaction | Yes | `SurfacePlot.tsx` | Rotate/zoom/pan via `OrbitControls`; hover raycasting on per-vertex markers with tooltips |
| Vertex coloring / data-driven color mapping | Yes | `SurfacePlot.tsx` `colorFor` | Sequential and diverging colormaps driven by the underlying financial values |
| Coordinate systems (object / world / camera) | Yes | Documented in-app | Right-handed, Y-up (Three.js convention) |
| WebGL rendering pipeline | Yes | Three.js via `@react-three/fiber` | — |
| Shaders (custom GLSL) | **Not implemented** | — | Standard/Basic/Line materials were sufficient for this data-surface use case; no custom shader was written, and none is claimed |
| Stereo rendering / head-mounted VR | **Not implemented (by design)** | — | Project spec explicitly excludes VR hardware; this is laptop-based interactive 3D graphics only |

## Verified project-level claims

- Every "Yes" row above corresponds to code that exists in this repository and is covered by a
  passing automated test (backend) or was manually exercised in-browser (frontend/3D) during this
  build — see [docs/testing.md](docs/testing.md).
- No row claims coverage of a technique that was not actually implemented.
