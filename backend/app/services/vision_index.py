"""Similarity index (feature 10): store a Siamese embedding + thumbnail for every screenshot we
have seen, so a new screenshot can be matched against previously uploaded reports with a similar
layout -- the "Similarity search finds previously uploaded reports with similar layouts" use case."""
from __future__ import annotations

import base64

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.cv_engine.vision import runtime
from app.models.vision import VisionIndexItem


def thumbnail_jpeg_b64(img: np.ndarray, width: int = 200) -> str:
    s = width / img.shape[1]
    t = cv2.resize(img, (width, max(1, int(img.shape[0] * s))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", t, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode("ascii")


def add_to_index(db: Session, img: np.ndarray, filename: str, origin: str = "upload") -> VisionIndexItem | None:
    """Returns None (without raising) when the encoder is unavailable -- indexing is best-effort."""
    try:
        emb = runtime.embed(img)
    except Exception:  # noqa: BLE001
        return None
    if emb is None:
        return None
    kind = None
    try:
        cls = runtime.classify(img, ("cnn",)).get("cnn", {})
        kind = cls.get("label") if cls.get("available") else None
    except Exception:  # noqa: BLE001
        pass
    item = VisionIndexItem(filename=filename[:120], origin=origin, kind_guess=kind, embedding=[float(x) for x in emb], thumbnail=thumbnail_jpeg_b64(img),
                           width=int(img.shape[1]), height=int(img.shape[0]))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
