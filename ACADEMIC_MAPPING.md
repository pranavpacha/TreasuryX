# Academic Mapping

Grounded directly in the two uploaded course syllabi (Module/Lab structure preserved as
provided):

- **CS4231 — Fundamentals of Computer Vision**, RV University, B.Tech (H), Semester VII (Prof.
  Ashwini Mathur, Prof. Deepak Murthy, Prof. Ramakrishnan)
- **CS4104 — Computer Graphics and Virtual Reality**, RV University, B.Tech (H), Semester VII

## Architecture note: one product, not three

TreasuryX is organized as **Workstation → Intelligence → Visualization → Methodology**, not as
separate Treasury / Computer-Vision-lab / Computer-Graphics-lab sections. Computer Vision powers
two real product features (**Financial Image Intelligence**, which turns an uploaded chart/report
screenshot into a structured value that actually updates bond/FX analytics, risk, and the 3D
views everywhere else in the app; and **Compare Market Screens**, SIFT-based visual comparison of
two screenshots). Computer Graphics powers **3D Market**, the production 3D
yield/volatility/stress visualization — live transformation matrices, a perspective/orthographic
toggle, and a hand-written GLSL shader ("Risk View") all run on real Treasury data inside that one
page. A handful of syllabus topics with no natural Treasury use (raster line-drawing algorithms,
2D transform/clipping mathematics, VR/AR concepts, the CNN/ViT model comparison, the
not-yet-trained object detector) are kept as **Methodology → Technical Evidence** — directly
inspectable, but not forced into the main workflow. See `frontend/src/App.tsx` for the full route
list and `docs/architecture.md` for the module layout.

Every "Implemented" row below corresponds to real, tested code (file path given). Every "Not
Implemented" row states the reason honestly rather than being silently omitted or faked. The same
table is also rendered live in-app at **Methodology → Course Mapping**
(`frontend/src/pages/methodology/CourseMapping.tsx`).

## CS4231 — Fundamentals of Computer Vision

| Syllabus Topic (Module) | Status | Where |
|---|---|---|
| Image formation, sensing, acquisition, sampling & quantization (M1) | Implemented | Financial Image Intelligence (`/intelligence/financial-image`) |
| Camera geometry (M1) | Not implemented | No camera-calibration/multi-view-geometry task in this project |
| Color fundamentals — RGB, HSI (M1) | Partial | Raster Graphics evidence (`/evidence/graphics/raster`) — HSV implemented, not HSI, matching the Graphics course's own Module 1 |
| Spatial domain processing & filtering, Lab 1 (M1) | Implemented | Financial Image Intelligence (CLAHE/denoise in production) + Filter Comparison evidence (`/evidence/cv/filters`) |
| Edge detection — DoG, LoG, Canny, Lab 2 (M2) | Implemented | Financial Image Intelligence (Canny in production) + Edge Detection evidence (`/evidence/cv/edges`) |
| Edge linking via Hough Transform (M2) | Implemented | Financial Image Intelligence — production region-detection stage |
| Segmentation — thresholding, morphological processing (M2) | Implemented | Financial Image Intelligence (production: adaptive thresholding + contour-based region detection) + Segmentation evidence (`/evidence/cv/segmentation`: classical GrabCut, real IoU/Dice benchmarks) |
| Blobs, corner detection (M2) | Implemented | Corner & Blob Detection evidence (`/evidence/cv/features`) |
| Scale space, SIFT, Lab 3 (M2) | Implemented | **Compare Market Screens** (`/intelligence/compare-screens`) — a real product feature |
| Optical flow (M2) | Implemented | Optical Flow evidence (`/evidence/cv/optical-flow`) |
| CNN review, CNNs for recognition (M3) | Implemented | Financial Image Intelligence (`/intelligence/financial-image`, Model Details panel — live per-upload) + CNN vs. ViT evidence (`/evidence/cv/models`) — trained from scratch, real metrics; runs live whenever torch is available (production build omits torch as a dependency, degrades gracefully — see Computer Vision Methodology); does not drive the production chart-type classifier, which is keyword-based |
| Neural style transfer (M3) | Not implemented | Lecture topic, no corresponding lab |
| CNNs for object detection — R-CNN, Fast R-CNN, FPN, RetinaNet, Lab 4 (M3) | Not implemented | Requires PASCAL-VOC-scale labeled data + GPU training — Object Detection Status page (`/evidence/cv/object-detection`) documents why + a reproducible pipeline |
| CNNs for segmentation — FCN, U-Net, Mask-RCNN, Lab 5 (M3) | Partial | Classical GrabCut segmentation implemented and benchmarked (real IoU/Dice) at `/evidence/cv/segmentation` for the in-scope chart-isolation task; U-Net on a medical-imaging dataset is out of scope (wrong domain) |
| Siamese networks, triplet/contrastive/ranking loss, FaceNet, Lab 6 (M3) | Not implemented | Face verification is off-domain for a Treasury tool and avoids handling biometric data |
| 3D CNN / RNN for video understanding, action recognition (M4) | Not implemented | No video data in this project |
| Attention models, Transformers, Vision Transformers, Lab 7 (M4) | Implemented | Financial Image Intelligence (Model Details panel, live) + CNN vs. ViT evidence (`/evidence/cv/models`) — a ViT written from scratch, trained on the same dataset as the CNN for a direct comparison |
| YOLO (M5) | Not implemented | Same reasoning as Fast R-CNN above |
| Zero/one/few-shot, self-supervised learning, CLIP, RL in vision (M5) | Not implemented | Lecture-only topics, no corresponding lab in the syllabus |

**12/19 topics have real, tested, running code (10 fully implemented, mostly inside actual
product features rather than a separate lab; 2 partial). The remaining 7 are lecture-only
topics or explicitly out of scope (camera geometry, neural style transfer, deep object
detection, Siamese/face-verification networks, 3D-CNN/RNN video understanding, YOLO,
zero-shot/self-supervised/CLIP/RL) — each with a stated reason, none silently omitted.**

## CS4104 — Computer Graphics and Virtual Reality

| Syllabus Topic (Module) | Status | Where |
|---|---|---|
| Graphics system architecture, GPU concepts, display technologies (M1) | Partial | Documented conceptually (Computer Graphics Methodology page); rendered via a browser's WebGL context, not raw hardware/driver code |
| Graphics primitives — DDA, Bresenham, Midpoint Circle, Labs 1-2 (M1) | Implemented | Raster Graphics evidence (`/evidence/graphics/raster`) — no natural Treasury use, kept as direct evidence |
| Color models — RGB, CMY, HSV (M1) | Implemented | Raster Graphics evidence |
| 2D transformations, homogeneous coordinates, composite transforms, Labs 3-4 (M2) | Implemented | 2D Transform & Clip evidence (`/evidence/graphics/transform2d`) |
| Windowing & clipping — Cohen-Sutherland, Liang-Barsky, Lab 5 (M2) | Implemented | 2D Transform & Clip evidence |
| 3D transformations, composite 3D transforms (M3) | Implemented | **3D Market** (`/visualization/3d-market`) — live Model matrix, read directly from the production renderer under "Graphics Details" |
| Projection — parallel & perspective, viewing pipeline, Lab 10 (M3) | Implemented | 3D Market — Perspective/Orthographic toggle actually switches the renderer's camera |
| Visible surface detection — back-face, Z-buffer, Lab 6 (M3) | Implemented | 3D Market (WebGL depth test in production) + a from-scratch software Z-buffer at `/evidence/graphics/depth-buffer` |
| Illumination models — ambient, diffuse, specular (M3) | Implemented | 3D Market — ambient + 2 directional lights on every surface |
| Shading — flat, Gouraud, Phong, Lab 7 (M3) | Implemented | 3D Market — **Risk View**: custom GLSL fragment shader computing per-pixel diffuse (Phong-family) shading |
| OpenGL/shader programming — vertex & fragment shaders, Lab 8 (M3/M5) | Implemented | 3D Market — Risk View; hand-written GLSL via `THREE.ShaderMaterial` in `frontend/src/three/SurfacePlot.tsx`, applied to real yield/vol/stress data, source viewable inline |
| Unity interactive 3D scene, Lab 9 | Not implemented | Unity is a separate desktop engine outside this web app's stack; equivalent concepts covered via WebGL/Three.js instead |
| VR/AR/MR — architecture, hardware, DOF, tracking, human factors (M4) | Partial | VR/AR Concepts evidence (`/evidence/graphics/vr-ar`) — documented conceptually, no VR/AR hardware used |
| XR concepts, marker/markerless AR, spatial computing (M5) | Partial | Same page as above |

**10/14 topics fully implemented — the production-relevant ones (transforms, projection, depth,
lighting, shading, shaders) run inside the actual 3D Market page, not a separate demo; 3 more are
documented conceptually (GPU/display architecture, VR/AR, XR — by the project's own laptop-only
design) and 1 is explicitly out of this web app's stack (Unity).**

## The CV → Treasury → Graphics integration

The single most important integration in this project: a value extracted from an uploaded chart
via Financial Image Intelligence, once reviewed and applied, is written as a `MarketOverride` row
(`backend/app/models/market_override.py`) that every other part of the app reads through
(`backend/app/services/market_view.py`) — bond pricing/duration/DV01, portfolio risk, the scenario
engine, and the 3D Portfolio Stress Surface all reflect it immediately. This is exercised by
`backend/tests/test_integration_cv_to_treasury.py` (5 passing tests), proving the pipeline is a
real state change, not a one-off calculation shown once and discarded.

## Verification

Every "Implemented" row above is covered by a passing automated test (backend: 97/97 pytest;
frontend: 52/52 vitest, as of this build) or was manually exercised in-browser during development
with a clean console — see `docs/testing.md`. No row claims coverage of a technique that was not
actually implemented.
