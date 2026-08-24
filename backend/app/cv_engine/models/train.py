"""
Trains TinyCNN and TinyViT on the synthetic financial-chart dataset and writes REAL
(not fabricated) metrics to backend/app/data/model_results/. Run once during development:

    .venv/Scripts/python -m app.cv_engine.models.train

Requires torch (see requirements-dev.txt) -- NOT a production runtime dependency.
The API serves these precomputed results; see docs/cv_models.md for methodology and honest
limitations (small synthetic dataset, laptop-scale models, not a claim of real-world accuracy).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from app.cv_engine.models.cnn import TinyCNN
from app.cv_engine.models.dataset import CLASSES, IMG_SIZE, generate_dataset, split_dataset
from app.cv_engine.models.vit import TinyViT
from app.cv_engine.preprocessing import to_base64_png

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "model_results"
OUT_DIR.mkdir(exist_ok=True, parents=True)

DEVICE = "cpu"
EPOCHS = 18
BATCH_SIZE = 16
LR = 1e-3


class ChartDataset(Dataset):
    def __init__(self, samples):
        self.samples = samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        img = s.image.astype(np.float32) / 255.0
        tensor = torch.from_numpy(img).permute(2, 0, 1)  # CHW
        return tensor, s.label


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def precision_recall_f1_macro(cm: np.ndarray) -> dict:
    n = cm.shape[0]
    precisions, recalls, f1s = [], [], []
    for c in range(n):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
    return {
        "precision_macro": float(np.mean(precisions)),
        "recall_macro": float(np.mean(recalls)),
        "f1_macro": float(np.mean(f1s)),
        "per_class": [
            {"class": CLASSES[c], "precision": precisions[c], "recall": recalls[c], "f1": f1s[c]}
            for c in range(n)
        ],
    }


def train_model(model: nn.Module, train_loader, val_loader, epochs: int) -> list[dict]:
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.CrossEntropyLoss()
    history = []
    for epoch in range(epochs):
        model.train()
        train_loss, train_correct, train_n = 0.0, 0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x.size(0)
            train_correct += (out.argmax(1) == y).sum().item()
            train_n += x.size(0)

        model.eval()
        val_loss, val_correct, val_n = 0.0, 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                out = model(x)
                loss = criterion(out, y)
                val_loss += loss.item() * x.size(0)
                val_correct += (out.argmax(1) == y).sum().item()
                val_n += x.size(0)

        history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss / train_n, "train_acc": train_correct / train_n,
            "val_loss": val_loss / val_n, "val_acc": val_correct / val_n,
        })
    return history


@torch.no_grad()
def evaluate(model: nn.Module, test_loader, test_samples) -> dict:
    model.eval()
    all_true, all_pred = [], []
    times = []
    for x, y in test_loader:
        for i in range(x.size(0)):
            xi = x[i:i + 1]
            t0 = time.perf_counter()
            out = model(xi)
            times.append((time.perf_counter() - t0) * 1000)
            pred = out.argmax(1).item()
            all_pred.append(pred)
            all_true.append(y[i].item())

    y_true, y_pred = np.array(all_true), np.array(all_pred)
    cm = confusion_matrix(y_true, y_pred, len(CLASSES))
    metrics = precision_recall_f1_macro(cm)
    accuracy = float((y_true == y_pred).mean())

    # A handful of sample predictions (correct + incorrect) for the UI
    samples_out = []
    rng = np.random.default_rng(0)
    idxs = rng.choice(len(test_samples), size=min(8, len(test_samples)), replace=False)
    for i in idxs:
        samples_out.append({
            "image": to_base64_png(test_samples[i].image),
            "true_label": CLASSES[all_true[i]],
            "pred_label": CLASSES[all_pred[i]],
            "correct": bool(all_true[i] == all_pred[i]),
        })

    return {
        "accuracy": accuracy,
        "confusion_matrix": cm.tolist(),
        "classes": CLASSES,
        "avg_inference_ms": float(np.mean(times)),
        "sample_predictions": samples_out,
        **metrics,
    }


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


def main():
    print("Generating synthetic dataset...")
    samples = generate_dataset(n_per_class=120)
    train_s, val_s, test_s = split_dataset(samples)
    print(f"train={len(train_s)} val={len(val_s)} test={len(test_s)}")

    train_loader = DataLoader(ChartDataset(train_s), batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(ChartDataset(val_s), batch_size=BATCH_SIZE)
    test_loader = DataLoader(ChartDataset(test_s), batch_size=BATCH_SIZE)

    results = {"dataset": {
        "n_classes": len(CLASSES), "classes": CLASSES, "img_size": IMG_SIZE,
        "n_train": len(train_s), "n_val": len(val_s), "n_test": len(test_s),
        "note": "Synthetic, procedurally generated (see dataset.py) -- NOT real market chart screenshots.",
    }}

    for name, model_fn in [("cnn", lambda: TinyCNN(len(CLASSES), IMG_SIZE)), ("vit", lambda: TinyViT(len(CLASSES), IMG_SIZE))]:
        print(f"\n=== Training {name} ===")
        model = model_fn()
        t0 = time.time()
        history = train_model(model, train_loader, val_loader, EPOCHS)
        train_time = time.time() - t0
        eval_result = evaluate(model, test_loader, test_s)
        results[name] = {
            "params": count_params(model),
            "epochs": EPOCHS,
            "train_time_sec": train_time,
            "history": history,
            **eval_result,
        }
        print(f"{name}: test accuracy={eval_result['accuracy']:.3f} params={count_params(model)} train_time={train_time:.1f}s")

    (OUT_DIR / "cnn_vs_vit.json").write_text(json.dumps(results, indent=2))
    print(f"\nWrote {OUT_DIR / 'cnn_vs_vit.json'}")


if __name__ == "__main__":
    main()
