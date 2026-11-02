"""Shared helpers for the vision routers: upload validation, safe temp files, numpy-safe JSON."""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.cv_engine.vision.video import ALLOWED_VIDEO_EXT, MAX_VIDEO_BYTES


def clean(obj):
    """Recursively convert numpy scalars/arrays and NaN/Inf into JSON-safe values."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return clean(obj.tolist())
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        return f if math.isfinite(f) else None
    return obj


class NpResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(clean(content), ensure_ascii=False, allow_nan=False).encode("utf-8")


async def read_image(file: UploadFile) -> tuple[np.ndarray, bytes, str]:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {list(settings.allowed_upload_extensions)}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(413, f"File too large ({len(data)} bytes). Max {settings.max_upload_size_bytes} bytes.")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode image -- unsupported or corrupt file")
    if img.shape[0] < 16 or img.shape[1] < 16:
        raise HTTPException(400, "Image is too small to analyse (minimum 16x16 px)")
    return img, data, file.filename or "upload"


async def save_video_temp(file: UploadFile) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(400, f"Unsupported video type '{ext}'. Allowed: {sorted(ALLOWED_VIDEO_EXT)}")
    fd, path = tempfile.mkstemp(suffix=ext, prefix="tx_vid_")
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = await file.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(413, f"Video too large (limit {MAX_VIDEO_BYTES // 1048576} MB)")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "Uploaded video is empty")
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
    return path
