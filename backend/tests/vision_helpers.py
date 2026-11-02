from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.cv_engine.ocr import run_ocr

OCR_AVAILABLE = run_ocr(np.full((20, 20), 255, dtype=np.uint8)).available
needs_ocr = pytest.mark.skipif(not OCR_AVAILABLE, reason="Tesseract OCR not installed")
def png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def files(name: str, img: np.ndarray, field: str = "file"):
    return {field: (name, png(img), "image/png")}
