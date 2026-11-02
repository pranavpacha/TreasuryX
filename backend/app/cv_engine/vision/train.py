"""
Trains the two learned vision models from scratch on the synthetic dataset and writes, for each:
  <name>.pt          PyTorch checkpoint
  <name>.onnx        exported network executed in production by cv2.dnn (no torch at runtime)
  <name>_card.json   model card: architecture, dataset sizes, config, seed, REAL measured metrics

Usage (torch + onnx are dev-only, see requirements-dev.txt):
    python -m app.cv_engine.vision.train                   # both
    python -m app.cv_engine.vision.train classifiers        # just the CNN/ViT classifier (feature 9)
    python -m app.cv_engine.vision.train siamese             # just the Siamese encoder (feature 10)

Everything is seeded. All metrics are measured on held-out TEMPLATES of SYNTHETIC screenshots;
they are NOT estimates of accuracy on real market screenshots, and every card says so.
"""
from __future__ import annotations

import json
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.cv_engine.vision import metrics, nets, runtime, synth
from app.cv_engine.vision.datasets import CLS_H, CLS_W, VisionData, to_chw_float

OUT = runtime.MODEL_DIR
SEED = 42
SYN_NOTE = ("Trained and evaluated on procedurally generated synthetic screenshots (synth.py). Splits are by template, so test "
            "templates are unseen layouts -- but they are still synthetic. This is NOT real-world accuracy.")


def _seed(s: int = SEED):
    torch.manual_seed(s)
    np.random.seed(s)


def _batches(n: int, bs: int, rng: np.random.Generator, shuffle=True):
    order = rng.permutation(n) if shuffle else np.arange(n)
    for i in range(0, n, bs):
        yield order[i: i + bs]


def _augment(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Photometric augmentation on an NCHW float batch."""
    b = x.shape[0]
    gain = rng.uniform(0.85, 1.15, (b, 1, 1, 1)).astype(np.float32)
    bias = rng.uniform(-0.06, 0.06, (b, 1, 1, 1)).astype(np.float32)
    out = x * gain + bias + rng.normal(0, 0.015, x.shape).astype(np.float32)
    return np.clip(out, 0, 1)


def export_onnx(model: nn.Module, example: torch.Tensor, name: str, opset: int = 13) -> dict:
    model.eval()
    path = OUT / f"{name}.onnx"
    info = {"onnx_file": path.name, "onnx_opset": opset}
    try:
        torch.onnx.export(model, example, str(path), dynamo=False, opset_version=opset, input_names=["x"], output_names=["y"])
        net = cv2.dnn.readNetFromONNX(str(path))
        net.setInput(example.numpy())
        y_cv = net.forward()
        with torch.no_grad():
            y_t = model(example).numpy()
        info.update(onnx_cv2_ok=True, onnx_parity_max_abs_diff=float(np.abs(y_cv - y_t).max()), onnx_size_kb=round(path.stat().st_size / 1024, 1))
    except Exception as exc:  # noqa: BLE001 -- recorded honestly in the card
        info.update(onnx_cv2_ok=False, onnx_error=str(exc)[:200])
        if path.exists():
            path.unlink()
    return info


def _write_card(name: str, payload: dict):
    payload.setdefault("honesty_note", SYN_NOTE)
    payload["trained_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    payload["seed"] = SEED
    payload["torch_version"] = torch.__version__
    (OUT / f"{name}_card.json").write_text(json.dumps(payload, indent=1))


def _split_counts(d: VisionData) -> dict:
    return {s: int(len(d.idx(s))) for s in ("train", "val", "test")}


# ====================================================================== feature 9: classifiers
def train_classifiers(d: VisionData, bs: int = 32) -> dict:
    X = to_chw_float(d.cls_images)
    tr, va, te = d.idx("train"), d.idx("val"), d.idx("test")
    y = d.kind.astype(np.int64)
    cards = {}
    for name, ctor, epochs, lr in (("cnn", lambda: nets.ClassifierCNN(8), 20, 2e-3), ("vit", lambda: nets.ClassifierViT(8), 60, 1e-3)):
        _seed()
        rng = np.random.default_rng(SEED)
        model = ctor()
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        hist, best, best_state = [], -1.0, None
        t0 = time.time()
        for ep in range(epochs):
            model.train()
            ls = 0.0
            for b in _batches(len(tr), bs, rng):
                ii = tr[b]
                out = model(torch.from_numpy(_augment(X[ii], rng)))
                loss = F.cross_entropy(out, torch.from_numpy(y[ii]))
                opt.zero_grad()
                loss.backward()
                opt.step()
                ls += loss.item() * len(ii)
            va_acc = _cls_acc(model, X[va], y[va])
            hist.append({"epoch": ep + 1, "train_loss": ls / len(tr), "val_acc": va_acc})
            if va_acc >= best:
                best, best_state = va_acc, {k: v.clone() for k, v in model.state_dict().items()}
        train_time = time.time() - t0
        model.load_state_dict(best_state)
        model.eval()
        with torch.no_grad():
            pred = np.concatenate([model(torch.from_numpy(X[te[i: i + 64]])).argmax(1).numpy() for i in range(0, len(te), 64)])
        cm = metrics.confusion_matrix(y[te], pred, 8)
        rep = metrics.classification_report(cm, synth.KINDS)
        ms = []
        with torch.no_grad():
            for i in te[:40]:
                t1 = time.perf_counter()
                model(torch.from_numpy(X[i: i + 1]))
                ms.append((time.perf_counter() - t1) * 1000)
        torch.save(model.state_dict(), OUT / f"classifier_{name}.pt")
        onnx = export_onnx(model, torch.zeros(1, 3, CLS_H, CLS_W), f"classifier_{name}", opset=17 if name == "vit" else 13)
        counts = {k: int((y[tr] == i).sum()) for i, k in enumerate(synth.KINDS)}
        card = {"task": "document-type classification (8 classes)", "architecture": "ClassifierCNN (4 conv blocks + MLP)" if name == "cnn" else "ClassifierViT (patch 8, dim 64, depth 3, 4 heads, learned pos-embed)",
                "params": nets.count_params(model), "classes": synth.KINDS, "input": f"{CLS_W}x{CLS_H} RGB", "dataset": _split_counts(d),
                "train_class_distribution": counts,
                "config": {"epochs": epochs, "batch": bs, "optimizer": f"AdamW lr={lr}", "augmentation": "gain/bias/noise", "train_time_s": round(train_time, 1),
                           "checkpoint_selection": "best validation accuracy"},
                "metrics": {"val_accuracy": best, "test": rep, "torch_cpu_inference_ms_mean": float(np.mean(ms))}, "history": hist, **onnx}
        _write_card(f"classifier_{name}", card)
        cards[name] = card
        print(f"[classifier_{name}] val={best:.3f} test_acc={rep['accuracy']:.3f} f1={rep['f1_macro']:.3f} onnx_ok={onnx.get('onnx_cv2_ok')}", flush=True)
    return cards


@torch.no_grad()
def _cls_acc(model, X, y) -> float:
    model.eval()
    p = np.concatenate([model(torch.from_numpy(X[i: i + 64])).argmax(1).numpy() for i in range(0, len(X), 64)])
    return float((p == y).mean())


# ====================================================================== feature 10: Siamese
def _shift(x: np.ndarray, rng: np.random.Generator, px: int = 2) -> np.ndarray:
    out = np.empty_like(x)
    for k in range(x.shape[0]):
        dx, dy = rng.integers(-px, px + 1, 2)
        out[k] = np.roll(x[k], (int(dy), int(dx)), axis=(1, 2))
    return out


def _contrastive(za: torch.Tensor, zb: torch.Tensor, same: torch.Tensor, margin: float = 1.0) -> torch.Tensor:
    dist = (za - zb).pow(2).sum(1).add(1e-9).sqrt()
    return (same * dist.pow(2) + (1 - same) * F.relu(margin - dist).pow(2)).mean()


def _pairs(d: VisionData, idx: np.ndarray, rng: np.random.Generator, n: int, pos_frac: float = 0.5):
    """Returns (a, b, same, tier) with tier: 0=pos, 1=hard neg (same kind, other template), 2=easy neg (other kind)."""
    key: dict = {}
    for i in idx:
        key.setdefault((int(d.kind[i]), int(d.template[i])), []).append(int(i))
    keys = list(key)
    a_l, b_l, s_l, t_l = [], [], [], []
    for _ in range(n):
        k = keys[rng.integers(len(keys))]
        a = int(rng.choice(key[k]))
        r = rng.random()
        if r < pos_frac:
            b = int(rng.choice([j for j in key[k] if j != a] or key[k]))
            tier = 0
        elif r < pos_frac + (1 - pos_frac) * 0.6:
            same_kind = [kk for kk in keys if kk[0] == k[0] and kk != k]
            kk = same_kind[rng.integers(len(same_kind))]
            b, tier = int(rng.choice(key[kk])), 1
        else:
            other = [kk for kk in keys if kk[0] != k[0]]
            kk = other[rng.integers(len(other))]
            b, tier = int(rng.choice(key[kk])), 2
        a_l.append(a), b_l.append(b), s_l.append(1.0 if tier == 0 else 0.0), t_l.append(tier)
    return np.array(a_l), np.array(b_l), np.array(s_l, np.float32), np.array(t_l)


@torch.no_grad()
def _embed_all(model: nn.Module, X: np.ndarray) -> np.ndarray:
    model.eval()
    return np.concatenate([nets.l2norm(model(torch.from_numpy(X[i: i + 128]))).numpy() for i in range(0, len(X), 128)])


def train_siamese(d: VisionData, epochs: int = 45, bs: int = 64) -> dict:
    _seed()
    rng = np.random.default_rng(SEED)
    X = to_chw_float(d.cls_images)
    tr, va, te = d.idx("train"), d.idx("val"), d.idx("test")
    model = nets.Encoder(64)
    opt = torch.optim.Adam(model.parameters(), lr=1.5e-3)
    hist = []
    for ep in range(epochs):
        model.train()
        a, b, s, _ = _pairs(d, tr, rng, n=len(tr) * 2)
        ls = 0.0
        for st in range(0, len(a), bs):
            sl = slice(st, st + bs)
            xa = torch.from_numpy(_augment(_shift(X[a[sl]], rng), rng))
            xb = torch.from_numpy(_augment(_shift(X[b[sl]], rng), rng))
            loss = _contrastive(nets.l2norm(model(xa)), nets.l2norm(model(xb)), torch.from_numpy(s[sl]))
            opt.zero_grad()
            loss.backward()
            opt.step()
            ls += loss.item() * len(a[sl])
        hist.append({"epoch": ep + 1, "train_contrastive_loss": ls / len(a)})
        if (ep + 1) % 5 == 0:
            print(f"[siamese] ep{ep + 1} loss={hist[-1]['train_contrastive_loss']:.4f}", flush=True)
    emb = _embed_all(model, X)
    ev = {sp: _siamese_eval(d, emb, idx, np.random.default_rng(7)) for sp, idx in (("val", va), ("test", te))}
    t_same = metrics.best_threshold(*ev["val"]["_same"])[0]
    t_family = metrics.best_threshold(*ev["val"]["_family"])[0]
    out_ev = {sp: {k: v for k, v in e.items() if not k.startswith("_")} for sp, e in ev.items()}
    for sp in ("val", "test"):
        sc, lb = ev[sp]["_same"]
        out_ev[sp]["same_template_accuracy_at_val_threshold"] = float(((sc >= t_same) == (lb == 1)).mean())
        sc, lb = ev[sp]["_family"]
        out_ev[sp]["same_kind_accuracy_at_val_threshold"] = float(((sc >= t_family) == (lb == 1)).mean())
    torch.save(model.state_dict(), OUT / "encoder.pt")
    onnx = export_onnx(model, torch.zeros(1, 3, CLS_H, CLS_W), "encoder")
    card = {"task": "metric learning (Siamese network, contrastive loss) for screenshot similarity", "architecture": "Encoder (4 conv blocks + MLP -> 64-d, L2-normalised) shared by both branches",
            "params": nets.count_params(model), "input": f"{CLS_W}x{CLS_H} RGB", "dataset": _split_counts(d),
            "config": {"epochs": epochs, "batch_pairs": bs, "loss": "contrastive (margin 1.0) on L2-normalised embeddings", "pairs": "50% positive (same template, different variant), "
                       "30% hard negative (same kind, different template), 20% easy negative (different kind)", "augmentation": "+-2px shift, gain/bias/noise"},
            "thresholds": {"same_template_cosine": t_same, "same_kind_cosine": t_family, "near_duplicate_cosine": 0.985,
                           "near_duplicate_note": "heuristic constant, additionally gated by SSIM at inference (see similarity.py)"},
            "metrics": out_ev, "history": hist, **onnx}
    _write_card("encoder", card)
    print(f"[siamese] test AUC same-template={out_ev['test']['auc_same_template']:.3f} p@1={out_ev['test']['template_retrieval_top1']:.3f}", flush=True)
    return card


def _siamese_eval(d: VisionData, emb: np.ndarray, idx: np.ndarray, rng: np.random.Generator) -> dict:
    a, b, s, tier = _pairs(d, idx, rng, n=1500)
    cos = (emb[a] * emb[b]).sum(1)
    same_kind = (d.kind[a] == d.kind[b]).astype(int)
    gal = [int(i) for i in idx if d.variant[i] == 0]
    q = [int(i) for i in idx if d.variant[i] != 0]
    sims = emb[q] @ emb[gal].T
    top = np.argmax(sims, 1)
    correct = np.mean([(d.kind[gal[t]], d.template[gal[t]]) == (d.kind[i], d.template[i]) for t, i in zip(top, q)])
    return {
        "n_pairs": int(len(a)), "auc_same_template": metrics.roc_auc(cos, s.astype(int)),
        "auc_same_template_hard_negatives_only": metrics.roc_auc(cos[tier != 2], s[tier != 2].astype(int)),
        "mean_cos_positive": float(cos[tier == 0].mean()), "mean_cos_hard_negative": float(cos[tier == 1].mean()), "mean_cos_easy_negative": float(cos[tier == 2].mean()),
        "template_retrieval_top1": float(correct), "n_retrieval_queries": len(q), "n_gallery_templates": len(gal),
        "_same": (cos, s.astype(int)), "_family": (cos[tier != 0], same_kind[tier != 0]),
    }


# ====================================================================== orchestration
def write_manifest(d: VisionData):
    m = synth.dataset_manifest()
    m["cache_split_counts"] = _split_counts(d)
    (OUT / "dataset_manifest.json").write_text(json.dumps(m, indent=1))


def main(argv: list[str]):
    OUT.mkdir(parents=True, exist_ok=True)
    which = set(argv) or {"classifiers", "siamese"}
    d = VisionData()
    write_manifest(d)
    steps = {"classifiers": train_classifiers, "siamese": train_siamese}
    for name, fn in steps.items():
        if name in which:
            t0 = time.time()
            fn(d)
            print(f"== {name} done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
