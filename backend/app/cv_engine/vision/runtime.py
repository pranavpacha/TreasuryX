"""
Production inference for the trained vision models (classifier CNN/ViT, Siamese encoder) --
cv2.dnn running exported ONNX files. No torch needed at runtime. Each model degrades
independently and honestly: if its .onnx file is missing or OpenCV cannot parse it, the
corresponding status call says so and callers report "unavailable" instead of pretending
a model ran.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from app.cv_engine.vision import synth

MODEL_DIR = Path(__file__).resolve().parents[2] / "data" / "model_results" / "vision"
CLS_SIZE = (96, 64)
_lock = threading.Lock()
_nets: dict[str, cv2.dnn.Net | None] = {}
_errors: dict[str, str] = {}


def card(name: str) -> dict | None:
    p = MODEL_DIR / f"{name}_card.json"
    return json.loads(p.read_text()) if p.exists() else None


def _net(name: str):
    with _lock:
        if name not in _nets:
            path = MODEL_DIR / f"{name}.onnx"
            if not path.exists():
                _nets[name], _errors[name] = None, f"{path.name} not present (run `python -m app.cv_engine.vision.train`)"
            else:
                try:
                    _nets[name] = cv2.dnn.readNetFromONNX(str(path))
                except cv2.error as exc:
                    _nets[name], _errors[name] = None, f"OpenCV could not load {path.name}: {str(exc)[:160]}"
        return _nets[name]


def model_status(name: str) -> dict:
    net = _net(name)
    path = MODEL_DIR / f"{name}.onnx"
    return {"name": name, "available": net is not None, "reason": _errors.get(name), "backend": "onnx/cv2.dnn",
            "size_kb": round(path.stat().st_size / 1024, 1) if path.exists() else None, "card": card(name) is not None}


def _forward(name: str, blob: np.ndarray) -> np.ndarray:
    net = _net(name)
    if net is None:
        raise RuntimeError(_errors.get(name, f"model {name} unavailable"))
    with _lock:
        net.setInput(blob)
        return net.forward()


def _blob(img_bgr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return cv2.dnn.blobFromImage(img_bgr, 1 / 255.0, size, (0, 0, 0), swapRB=True, crop=False)


def _as_bgr(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img


def _softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max())
    return e / e.sum()


# ------------------------------------------------------------------ feature 9: classification
def classify(img_bgr: np.ndarray, which: tuple[str, ...] = ("cnn", "vit")) -> dict:
    img_bgr = _as_bgr(img_bgr)
    blob = _blob(img_bgr, CLS_SIZE)
    result = {}
    for name in which:
        key = f"classifier_{name}"
        if _net(key) is None:
            result[name] = {"available": False, "reason": _errors.get(key)}
            continue
        t0 = time.perf_counter()
        logits = _forward(key, blob)[0]
        ms = (time.perf_counter() - t0) * 1000
        p = _softmax(logits.astype(np.float64))
        order = np.argsort(-p)
        result[name] = {"available": True, "label": synth.KINDS[int(order[0])], "confidence": round(float(p[order[0]]), 4),
                        "inference_ms": round(ms, 2), "probabilities": {synth.KINDS[i]: round(float(p[i]), 4) for i in order}}
    return result


# ------------------------------------------------------------------ feature 10: embeddings
def embed(img_bgr: np.ndarray) -> np.ndarray | None:
    if _net("encoder") is None:
        return None
    v = _forward("encoder", _blob(_as_bgr(img_bgr), CLS_SIZE))[0].astype(np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v
