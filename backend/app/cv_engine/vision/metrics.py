"""Evaluation metrics (pure numpy -- no torch needed) for the classifier and Siamese encoder.
Used by both the training script and the live API, so trained and reported numbers match."""
from __future__ import annotations

import numpy as np


def confusion_matrix(y_true, y_pred, n: int) -> np.ndarray:
    cm = np.zeros((n, n), int)
    for t, p in zip(y_true, y_pred):
        cm[int(t), int(p)] += 1
    return cm


def classification_report(cm: np.ndarray, names: list[str]) -> dict:
    per, p_l, r_l, f_l = [], [], [], []
    for c in range(cm.shape[0]):
        tp = cm[c, c]
        fp, fn = cm[:, c].sum() - tp, cm[c, :].sum() - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        per.append({"class": names[c], "precision": float(p), "recall": float(r), "f1": float(f), "support": int(cm[c].sum())})
        p_l.append(p), r_l.append(r), f_l.append(f)
    return {"accuracy": float(np.trace(cm) / max(1, cm.sum())), "precision_macro": float(np.mean(p_l)), "recall_macro": float(np.mean(r_l)),
            "f1_macro": float(np.mean(f_l)), "per_class": per, "confusion_matrix": cm.tolist(), "classes": names}


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney U formulation of ROC AUC (higher score => positive)."""
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = scores[labels == 1], scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    allv = np.concatenate([pos, neg])[order]
    ranks = np.empty(len(order))
    r = np.empty(len(allv))
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        r[i: j + 1] = (i + j) / 2 + 1
        i = j + 1
    ranks[order] = r
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def best_threshold(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Threshold maximizing accuracy on (scores, labels). Returns (threshold, accuracy)."""
    cand = np.unique(scores)
    best_t, best_a = float(cand[0]), 0.0
    for t in cand:
        a = float(((scores >= t) == (labels == 1)).mean())
        if a > best_a:
            best_t, best_a = float(t), a
    return best_t, best_a
