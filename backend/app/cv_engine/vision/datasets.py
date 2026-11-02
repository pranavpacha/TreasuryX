"""
Cached numpy view of the synthetic dataset (synth.py) at the resolution the classifier and
Siamese encoder use: 96x64 RGB. The cache is a deterministic function of synth.py, so it is
git-ignored and rebuilt on demand rather than committed.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.cv_engine.vision import synth

CLS_W, CLS_H = 96, 64
CACHE_PATH = Path(__file__).resolve().parents[3] / ".cache" / "vision_dataset.npz"
SPLIT_IDS = {"train": 0, "val": 1, "test": 2}


def build_cache(path: Path = CACHE_PATH, variants: int = synth.VARIANTS_PER_TEMPLATE, force: bool = False) -> Path:
    if path.exists() and not force:
        return path
    imgs, meta = [], []
    for split, sid in SPLIT_IDS.items():
        for doc in synth.iter_split(split, variants=variants):
            imgs.append(cv2.resize(doc.image, (CLS_W, CLS_H), interpolation=cv2.INTER_AREA))
            meta.append((synth.KINDS.index(doc.kind), doc.template, doc.variant, sid))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, cls_images=np.stack(imgs), meta=np.array(meta, np.int32))
    return path


class VisionData:
    def __init__(self, path: Path | None = None):
        z = np.load(build_cache(path or CACHE_PATH))
        self.cls_images, self.meta = z["cls_images"], z["meta"]
        self.kind, self.template, self.variant, self.split = self.meta.T

    def idx(self, split: str) -> np.ndarray:
        return np.where(self.split == SPLIT_IDS[split])[0]


def to_chw_float(imgs_bgr: np.ndarray) -> np.ndarray:
    """BGR uint8 NHWC -> RGB float32 NCHW in [0,1] (one consistent convention for every model)."""
    return np.ascontiguousarray(imgs_bgr[..., ::-1].astype(np.float32).transpose(0, 3, 1, 2) / 255.0)
