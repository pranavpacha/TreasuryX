"""A small CNN classifier -- deliberately shallow (laptop-CPU trainable in seconds),
covering the syllabus's "CNN for recognition" concept (conv -> pool -> conv -> pool -> FC)
without pretending to be Fast R-CNN/RetinaNet-scale."""
from __future__ import annotations

import torch
import torch.nn as nn


class TinyCNN(nn.Module):
    def __init__(self, n_classes: int, img_size: int = 64):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),   # 64->32
            nn.Conv2d(16, 32, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),  # 32->16
            nn.Conv2d(32, 32, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),  # 16->8
        )
        flat = 32 * (img_size // 8) * (img_size // 8)
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(flat, 64), nn.ReLU(), nn.Dropout(0.2), nn.Linear(64, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))
