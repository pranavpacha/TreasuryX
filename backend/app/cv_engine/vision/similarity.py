"""
Feature 10 -- Siamese-network screenshot similarity (document/chart similarity, not face recognition).

The encoder (nets.Encoder, trained with a contrastive loss on same-template vs different-template
pairs of synthetic screenshots) maps a screenshot to a 64-d unit vector; cosine similarity of two
vectors is the score. Thresholds come from the model card (picked on the validation split). The
pairwise verdict combines the learned score with classical evidence (SSIM + SIFT matched regions,
reusing compare.py) so a near-duplicate claim is never made on the learned score alone.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.cv_engine.preprocessing import to_base64_png
from app.cv_engine.vision import compare, runtime

NEAR_DUP_SSIM = 0.92
DEFAULT_THR = {"same_template_cosine": 0.9, "same_kind_cosine": 0.7, "near_duplicate_cosine": 0.985}


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def verdict(cos: float, ssim: float | None, thr: dict) -> dict:
    if cos >= thr["near_duplicate_cosine"] and (ssim is None or ssim >= NEAR_DUP_SSIM):
        return {"label": "near_duplicate", "text": "Near-duplicate screenshots (very high embedding similarity and structural similarity)."}
    if cos >= thr["same_template_cosine"]:
        return {"label": "same_template", "text": "Likely the same report/screen template (data may differ)."}
    if cos >= thr["same_kind_cosine"]:
        return {"label": "similar_layout", "text": "Similar chart/report structure but probably a different template."}
    return {"label": "different", "text": "Visually different screens."}


def compare_pair(img_a: np.ndarray, img_b: np.ndarray) -> dict:
    ea, eb = runtime.embed(img_a), runtime.embed(img_b)
    if ea is None or eb is None:
        raise RuntimeError("Siamese encoder is not available (encoder.onnx missing); classical SIFT/SSIM comparison is still available under Screenshot Comparison.")
    card = runtime.card("encoder") or {}
    thr = card.get("thresholds", DEFAULT_THR)
    cos = cosine(ea, eb)
    a, b = compare._fit(img_a, 800), compare._fit(img_b, 800)
    ga, gb = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    reg = compare.register(ga, gb)
    ssim = None
    if reg["ok"]:
        al = cv2.warpPerspective(gb, reg["H"], (ga.shape[1], ga.shape[0]))
        ssim = float(compare.ssim_map(ga, al).mean())
    elif ga.shape == gb.shape:
        ssim = float(compare.ssim_map(ga, gb).mean())
    out = {"cosine_similarity": round(cos, 4), "ssim": None if ssim is None else round(ssim, 4), "verdict": verdict(cos, ssim, thr), "thresholds": thr,
           "sift": {"good_matches": reg["good_matches"], "inliers": reg["inliers"], "registered": reg["ok"]},
           "model": {"architecture": card.get("architecture"), "trained_on": "synthetic screenshots", "test_auc_same_template": (card.get("metrics", {}).get("test", {}) or {}).get("auc_same_template")},
           "caveat": "Similarity is learned from synthetic layouts; on real screenshots it is a heuristic score, not a calibrated probability."}
    if reg["matches"]:
        ka, kb = reg["kp"]
        out["matched_regions_image"] = to_base64_png(cv2.drawMatches(b, kb, a, ka, sorted(reg["matches"], key=lambda m: m.distance)[:40], None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS))
    return out


def rank(query_emb: np.ndarray, items: list[dict], top_k: int = 8) -> list[dict]:
    """items: [{'id', 'embedding': list[float], ...}] -> sorted by cosine similarity, highest first."""
    if not items:
        return []
    mat = np.array([it["embedding"] for it in items], dtype=np.float64)
    sims = mat @ query_emb
    order = np.argsort(-sims)[:top_k]
    return [{**{k: v for k, v in items[i].items() if k != "embedding"}, "similarity": round(float(sims[i]), 4)} for i in order]
