"""
Live per-image CNN/ViT inference -- optional, torch-gated.

The API always serves the precomputed offline CNN-vs-ViT benchmark (see
app/api/academic_cv.py::model_benchmarks). This module additionally offers LIVE inference of
the same trained models on a freshly uploaded Financial Image Intelligence image, if and only
if torch is installed AND the trained weight files are present
(backend/app/data/model_results/{cnn,vit}_weights.pt, written by
app/cv_engine/models/train.py). This mirrors the project's existing OCR/Tesseract
graceful-degradation pattern: the production deployment does not install torch (see
requirements-dev.txt, kept dev-only to stay within free-tier hosting limits), so this always
reports unavailable there; a local dev environment with torch installed gets genuine live
inference -- exactly the behaviour requirements-dev.txt already documents.

Domain-gap caveat (stated, not hidden): both models are trained on a small synthetic 4-class
chart dataset (see dataset.py), not real market screenshots. A live prediction on an uploaded
financial chart screenshot is a genuine model inference -- not fabricated -- but should be read
as a demonstration of CNN/ViT mechanics, not a claim of production-grade real-world chart
recognition. See docs/cv_models.md and Methodology -> CNN vs. ViT for the full benchmark.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from app.cv_engine.models.dataset import CLASSES, IMG_SIZE

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "model_results"

try:
    import torch

    from app.cv_engine.models.cnn import TinyCNN
    from app.cv_engine.models.vit import TinyViT

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

_cached_models: dict | None = None


def _weights_present() -> bool:
    return (MODEL_DIR / "cnn_weights.pt").exists() and (MODEL_DIR / "vit_weights.pt").exists()


def model_details_available() -> bool:
    return TORCH_AVAILABLE and _weights_present()


def _load_models() -> dict:
    global _cached_models
    if _cached_models is None:
        cnn = TinyCNN(len(CLASSES), IMG_SIZE)
        cnn.load_state_dict(torch.load(MODEL_DIR / "cnn_weights.pt", map_location="cpu"))
        cnn.eval()
        vit = TinyViT(len(CLASSES), IMG_SIZE)
        vit.load_state_dict(torch.load(MODEL_DIR / "vit_weights.pt", map_location="cpu"))
        vit.eval()
        _cached_models = {"cnn": cnn, "vit": vit}
    return _cached_models


def _predict_one(model, tensor) -> dict:
    t0 = time.perf_counter()
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs).item())
    inference_ms = (time.perf_counter() - t0) * 1000
    return {
        "label": CLASSES[idx],
        "confidence": round(float(probs[idx]), 4),
        "inference_ms": round(inference_ms, 2),
    }


def classify_image_bytes(image_bytes: bytes) -> dict:
    """Live CNN + ViT classification of an uploaded financial image, if available in this
    deployment (torch installed + trained weights present -- see module docstring)."""
    if not model_details_available():
        return {
            "available": False,
            "reason": (
                "Live model inference requires torch, a dev-only dependency not installed in "
                "this deployment (see backend/requirements-dev.txt). The precomputed CNN vs. "
                "ViT benchmark -- trained from scratch, real accuracy/F1/confusion-matrix "
                "results -- is available at Methodology -> Technical Evidence -> "
                "CNN vs. Vision Transformer."
            ),
        }

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"available": False, "reason": "Could not decode image for model inference."}

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(img_rgb, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
    tensor = torch.from_numpy(resized.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)

    models = _load_models()
    cnn_pred = _predict_one(models["cnn"], tensor)
    vit_pred = _predict_one(models["vit"], tensor)

    return {
        "available": True,
        "classes": CLASSES,
        "cnn": cnn_pred,
        "vit": vit_pred,
        "agree": cnn_pred["label"] == vit_pred["label"],
        "note": (
            "Both models were trained from scratch on a small synthetic 4-class chart dataset "
            "(see Methodology -> CNN vs. ViT). This is a genuine live inference on the "
            "uploaded image, not a fabricated result -- but read it as a demonstration of the "
            "technique, not a claim of production-grade real-world chart recognition."
        ),
    }
