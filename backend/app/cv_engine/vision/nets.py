"""
PyTorch architectures for the two LEARNED vision models (feature 9's CNN/ViT classifier, feature
10's Siamese encoder). Torch is a DEV-ONLY dependency (training and export); the trained networks
are exported to ONNX and executed in production by cv2.dnn (see runtime.py), so the deployed
backend does not need torch. Both are trained FROM SCRATCH on the synthetic dataset (synth.py) --
neither starts from pretrained weights.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def conv_bn(i: int, o: int, k: int = 3, s: int = 1) -> nn.Sequential:
    return nn.Sequential(nn.Conv2d(i, o, k, s, padding=k // 2, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True))


class ClassifierCNN(nn.Module):
    """Plain CNN: conv -> pool x4 -> FC, covering the syllabus's 'CNN for recognition' concept."""

    def __init__(self, n_classes: int = 8):
        super().__init__()
        self.features = nn.Sequential(conv_bn(3, 16), nn.MaxPool2d(2), conv_bn(16, 32), nn.MaxPool2d(2),
                                      conv_bn(32, 48), nn.MaxPool2d(2), conv_bn(48, 64), nn.MaxPool2d(2))
        self.fc = nn.Sequential(nn.Flatten(), nn.Linear(64 * 4 * 6, 96), nn.ReLU(inplace=True), nn.Dropout(0.2), nn.Linear(96, n_classes))

    def forward(self, x):  # x: [B,3,64,96]
        return self.fc(self.features(x))


class _Attn(nn.Module):
    def __init__(self, d: int, heads: int):
        super().__init__()
        self.h, self.dh = heads, d // heads
        self.qkv, self.proj = nn.Linear(d, 3 * d), nn.Linear(d, d)

    def forward(self, x):
        b, n, d = x.shape
        q, k, v = self.qkv(x).reshape(b, n, 3, self.h, self.dh).permute(2, 0, 3, 1, 4)
        a = torch.softmax((q @ k.transpose(-2, -1)) * (self.dh ** -0.5), dim=-1)
        return self.proj((a @ v).transpose(1, 2).reshape(b, n, d))


class _Block(nn.Module):
    def __init__(self, d: int, heads: int, mlp: float):
        super().__init__()
        self.n1, self.attn, self.n2 = nn.LayerNorm(d), _Attn(d, heads), nn.LayerNorm(d)
        self.mlp = nn.Sequential(nn.Linear(d, int(d * mlp)), nn.GELU(), nn.Linear(int(d * mlp), d))

    def forward(self, x):
        x = x + self.attn(self.n1(x))
        return x + self.mlp(self.n2(x))


class ClassifierViT(nn.Module):
    """Vision Transformer, written from scratch (not a pretrained download): patchify -> linear
    embedding + learned position embedding -> transformer encoder blocks (multi-head self-attention)
    -> mean-pooled tokens -> linear head."""

    def __init__(self, n_classes: int = 8, h: int = 64, w: int = 96, patch: int = 8, dim: int = 64, depth: int = 3, heads: int = 4):
        super().__init__()
        self.patch = nn.Conv2d(3, dim, patch, stride=patch)
        self.n_tokens = (h // patch) * (w // patch)
        self.pos = nn.Parameter(torch.zeros(1, self.n_tokens, dim))
        nn.init.trunc_normal_(self.pos, std=0.02)
        self.blocks = nn.Sequential(*[_Block(dim, heads, 2.0) for _ in range(depth)])
        self.norm, self.head = nn.LayerNorm(dim), nn.Linear(dim, n_classes)

    def forward(self, x):
        t = self.patch(x).flatten(2).transpose(1, 2) + self.pos
        return self.head(self.norm(self.blocks(t)).mean(dim=1))


class Encoder(nn.Module):
    """Shared embedding network for Siamese metric learning (feature 10) and the zero-shot search
    fallback's document-type signal (feature 11 reuses the classifier, not this). Keeps spatial
    layout (flatten, not global pooling) because 'same report template' is largely a layout property."""

    def __init__(self, emb: int = 64):
        super().__init__()
        self.features = nn.Sequential(conv_bn(3, 16), nn.MaxPool2d(2), conv_bn(16, 32), nn.MaxPool2d(2),
                                      conv_bn(32, 48), nn.MaxPool2d(2), conv_bn(48, 64), nn.MaxPool2d(2))
        self.fc = nn.Sequential(nn.Flatten(), nn.Linear(64 * 4 * 6, 128), nn.ReLU(inplace=True), nn.Linear(128, emb))

    def forward(self, x):  # un-normalized embedding; callers L2-normalize
        return self.fc(self.features(x))


def l2norm(x: torch.Tensor) -> torch.Tensor:
    return F.normalize(x, dim=1)


def count_params(m: nn.Module) -> int:
    return int(sum(p.numel() for p in m.parameters()))
