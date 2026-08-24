"""A minimal Vision Transformer (patch embedding + a couple of transformer encoder blocks +
a class-token head), written from scratch rather than downloading a pretrained ViT -- keeps
the model laptop-trainable and avoids a multi-hundred-MB weights download, while still
implementing the real ViT mechanics (patchify, positional embedding, multi-head self-attention,
class token) the course covers, at a scale appropriate for the small synthetic dataset."""
from __future__ import annotations

import torch
import torch.nn as nn


class PatchEmbed(nn.Module):
    def __init__(self, img_size: int, patch_size: int, in_ch: int, embed_dim: int):
        super().__init__()
        self.n_patches = (img_size // patch_size) ** 2
        self.proj = nn.Conv2d(in_ch, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)                # (B, embed_dim, H/p, W/p)
        x = x.flatten(2).transpose(1, 2)  # (B, n_patches, embed_dim)
        return x


class TinyViT(nn.Module):
    def __init__(
        self, n_classes: int, img_size: int = 64, patch_size: int = 8,
        embed_dim: int = 48, depth: int = 3, n_heads: int = 4, mlp_ratio: float = 2.0,
    ):
        super().__init__()
        self.patch_embed = PatchEmbed(img_size, patch_size, 3, embed_dim)
        n_patches = self.patch_embed.n_patches
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, n_patches + 1, embed_dim))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
        nn.init.trunc_normal_(self.cls_token, std=0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=n_heads, dim_feedforward=int(embed_dim * mlp_ratio),
            dropout=0.1, batch_first=True, activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=depth)
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b = x.shape[0]
        tokens = self.patch_embed(x)
        cls = self.cls_token.expand(b, -1, -1)
        tokens = torch.cat([cls, tokens], dim=1) + self.pos_embed
        tokens = self.encoder(tokens)
        cls_out = self.norm(tokens[:, 0])
        return self.head(cls_out)
