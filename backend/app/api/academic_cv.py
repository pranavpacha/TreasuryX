"""
Academic Mode / Computer Vision Lab endpoints -- classical CV techniques from CS4231
(Fundamentals of Computer Vision) demonstrated on uploaded images, plus precomputed
CNN-vs-ViT benchmark results (see backend/app/cv_engine/models/train.py).
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile

from app.cv_engine.edges_lab import (
    canny_adjustable, difference_of_gaussians, laplacian_edges, laplacian_of_gaussian, sobel_edges,
)
from app.cv_engine.features_lab import blob_detection, harris_corners
from app.cv_engine.filters_lab import FILTER_NOTES, compare_filters
from app.cv_engine.optical_flow_lab import dense_optical_flow, synthetic_shift
from app.cv_engine.preprocessing import resize_keep_aspect, to_base64_png
from app.cv_engine.segmentation_lab import run_benchmark, segment_region
from app.cv_engine.sift_lab import run_sift_matching

router = APIRouter(prefix="/api/academic/cv", tags=["academic-cv"])

MODEL_RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "model_results" / "cnn_vs_vit.json"


def _decode_gray(content: bytes) -> np.ndarray:
    arr = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode image")
    img = resize_keep_aspect(img, 400)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


@router.post("/filters")
async def filters_lab(file: UploadFile, kernel_size: int = 5, sigma: float = 1.5):
    content = await file.read()
    gray = _decode_gray(content)
    results = compare_filters(gray, kernel_size, sigma)
    return {
        "images": {k: to_base64_png(v) for k, v in results.items()},
        "notes": FILTER_NOTES,
    }


@router.post("/edges")
async def edges_lab(file: UploadFile, canny_low: int = 50, canny_high: int = 150, dog_sigma1: float = 1.0, dog_sigma2: float = 2.0):
    content = await file.read()
    gray = _decode_gray(content)
    sobel = sobel_edges(gray)
    laplacian = laplacian_edges(gray)
    dog = difference_of_gaussians(gray, dog_sigma1, dog_sigma2)
    log = laplacian_of_gaussian(gray)
    canny = canny_adjustable(gray, canny_low, canny_high)
    return {
        "images": {
            "original": to_base64_png(gray),
            "sobel_x": to_base64_png(sobel["sobel_x"]),
            "sobel_y": to_base64_png(sobel["sobel_y"]),
            "gradient_magnitude": to_base64_png(sobel["gradient_magnitude"]),
            "laplacian": to_base64_png(laplacian),
            "dog": to_base64_png(dog),
            "log": to_base64_png(log),
            "canny": to_base64_png(canny),
        },
        "params": {"canny_low": canny_low, "canny_high": canny_high, "dog_sigma1": dog_sigma1, "dog_sigma2": dog_sigma2},
    }


@router.post("/features")
async def features_lab(file: UploadFile):
    content = await file.read()
    gray = _decode_gray(content)
    corners = harris_corners(gray)
    blobs = blob_detection(gray)
    return {
        "images": {"corners": to_base64_png(corners["overlay"]), "blobs": to_base64_png(blobs["overlay"])},
        "n_corners": corners["n_corners"],
        "n_blobs": blobs["n_blobs"],
    }


@router.post("/sift")
async def sift_lab(file_a: UploadFile, file_b: UploadFile, ratio_thresh: float = 0.75):
    gray_a = _decode_gray(await file_a.read())
    gray_b = _decode_gray(await file_b.read())
    out = run_sift_matching(gray_a, gray_b, ratio_thresh)
    images = {"keypoints_a": to_base64_png(out["keypoints_a"]), "keypoints_b": to_base64_png(out["keypoints_b"])}
    if out["matches"] is not None:
        images["matches"] = to_base64_png(out["matches"])
    return {"images": images, "result": out["result"]}


@router.post("/segmentation")
async def segmentation_lab(file: UploadFile):
    content = await file.read()
    arr = np.frombuffer(content, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(400, "Could not decode image")
    img_bgr = resize_keep_aspect(img_bgr, 400)
    result = segment_region(img_bgr)
    return {
        "images": {
            "original": to_base64_png(img_bgr),
            "mask": to_base64_png(result["mask"]),
            "overlay": to_base64_png(result["overlay"]),
            "extracted_region": to_base64_png(result["extracted_region"]),
        },
        "init_rect": result["init_rect"],
    }


@router.get("/segmentation/benchmark")
def segmentation_benchmark():
    """Real IoU/Dice on a synthetic ground-truth dataset (see segmentation_lab.py) -- not
    fabricated numbers, but explicitly a synthetic-data benchmark, not real-world accuracy."""
    return run_benchmark()


@router.post("/optical-flow")
async def optical_flow_lab(file_a: UploadFile, file_b: UploadFile | None = None):
    gray_a = _decode_gray(await file_a.read())
    if file_b is not None:
        gray_b = _decode_gray(await file_b.read())
        synthetic = False
    else:
        gray_b = synthetic_shift(gray_a)
        synthetic = True
    out = dense_optical_flow(gray_a, gray_b)
    return {
        "images": {
            "frame_a": to_base64_png(gray_a), "frame_b": to_base64_png(gray_b),
            "flow_field_color": to_base64_png(out["flow_field_color"]),
            "vector_overlay": to_base64_png(out["vector_overlay"]),
        },
        "mean_magnitude": out["mean_magnitude"], "max_magnitude": out["max_magnitude"],
        "second_frame_synthetic": synthetic,
    }


@router.get("/model-benchmarks")
def model_benchmarks():
    if not MODEL_RESULTS_PATH.exists():
        raise HTTPException(
            404,
            "Precomputed CNN/ViT benchmark results are not present in this deployment. "
            "Run `python -m app.cv_engine.models.train` (requires torch, see requirements-dev.txt) "
            "to generate them.",
        )
    return json.loads(MODEL_RESULTS_PATH.read_text())


@router.get("/object-detection/status")
def object_detection_status():
    """Honest status page: the syllabus's Fast R-CNN/PASCAL VOC and YOLO labs are NOT trained
    in this build (out of scope for a laptop/no-GPU, no-internet-dataset-download build) -- this
    endpoint documents why and what a reproducible pipeline would look like, per the project's
    own 'no fabrication' rule, rather than faking results."""
    return {
        "status": "NOT_TRAINED",
        "reason": (
            "Training a real object detector (Fast R-CNN / FPN / RetinaNet / YOLO) requires a "
            "labeled bounding-box dataset (e.g. PASCAL VOC, ~2GB) and GPU-scale compute for a "
            "meaningful number of epochs -- both out of scope for a laptop-only, offline-capable "
            "build. Rather than download pretrained COCO weights and show generic 'person/car/dog' "
            "detections unrelated to Treasury, or fabricate financial-domain metrics, this status "
            "is reported honestly."
        ),
        "what_is_implemented_instead": (
            "Classical region/line detection (Canny edges + Hough line transform + largest-contour "
            "bounding box, see backend/app/cv_engine/edges.py) locates the chart plot area and axis "
            "lines in an uploaded financial screenshot -- see the Market Intelligence page and the "
            "'Integrated Pipeline' lab."
        ),
        "reproducible_pipeline_if_undertaken": {
            "dataset_schema": {
                "images/": "raw screenshots",
                "annotations.json": "COCO-style bounding boxes with classes: "
                                     "chart_region, axis_label, legend, price_label, table",
                "splits": "train/val/test, e.g. 70/15/15",
            },
            "training_config": {
                "architecture": "e.g. a Fast R-CNN or lightweight single-stage detector",
                "backbone": "small pretrained CNN backbone (e.g. MobileNet) for laptop feasibility",
                "epochs": "dataset-dependent; would need a labeled set of >=500 images to be meaningful",
                "evaluation": "mAP@0.5, precision/recall per class",
            },
            "inference_script": "would load a saved checkpoint and run non-max-suppressed boxes over "
                                 "an uploaded image, returned in the same structured-field format as "
                                 "the current classical pipeline",
        },
    }
