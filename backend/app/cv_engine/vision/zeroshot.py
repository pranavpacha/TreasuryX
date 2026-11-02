"""
Feature 11 -- Zero-shot, text-driven search over financial screenshots.

Two backends, chosen automatically and ALWAYS reported in the response:
  clip      : a real CLIP model (default openai/clip-vit-base-patch32 through `transformers`), used only if
              `transformers`+`torch` are importable AND the weights are already in the local Hugging Face cache
              (or TREASURYX_ALLOW_MODEL_DOWNLOAD=1). Scores are cosine similarities between image and text
              embeddings.
  fallback  : NOT CLIP and NOT semantic. A transparent keyword heuristic: the query is matched against synonym
              lists for each document type, weighted by this project's own document-type classifier (feature 9),
              plus word overlap with the screenshot's OCR text. It exists so the page works where CLIP cannot run
              (e.g. the free-tier deployment); the response says `clip_ran: false`.

Scores are semantic-similarity / heuristic match scores, NOT calibrated probabilities.
"""
from __future__ import annotations

import os
import re

import cv2
import numpy as np

from app.cv_engine.vision import runtime, synth

CLIP_MODEL = os.environ.get("TREASURYX_CLIP_MODEL", "openai/clip-vit-base-patch32")
ALLOW_DOWNLOAD = os.environ.get("TREASURYX_ALLOW_MODEL_DOWNLOAD") == "1"
_clip = {"tried": False, "model": None, "proc": None, "error": None}

SYNONYMS = {
    "yield_curve": ["yield curve", "government securities", "g-sec", "gsec", "sovereign", "tenor", "curve", "steepening", "flattening", "inverted", "par yield", "bond yields"],
    "fx_line_chart": ["fx", "exchange rate", "usd inr", "usd/inr", "eur usd", "eur/usd", "currency", "spot", "rupee", "dollar", "forex", "line chart"],
    "candlestick_chart": ["candlestick", "ohlc", "candle", "price action", "candles"],
    "bond_table": ["bond", "valuation", "table", "quotes", "coupon", "yield table", "price table", "benchmark bond", "rates monitor"],
    "market_report": ["market report", "commentary", "morning note", "wrap", "research", "strategy", "market wrap", "daily note"],
    "risk_dashboard": ["risk", "var", "value at risk", "expected shortfall", "dv01", "dashboard", "exposure", "portfolio risk", "risk report", "duration"],
    "portfolio_chart": ["portfolio", "allocation", "asset mix", "pie", "holdings", "breakdown", "allocation chart"],
    "financial_statement": ["statement", "income", "balance sheet", "financials", "profit", "revenue", "annual results", "financial summary"],
}


def clip_status() -> dict:
    if not _clip["tried"]:
        _clip["tried"] = True
        try:
            import torch  # noqa: F401
            from transformers import CLIPModel, CLIPProcessor
            _clip["model"] = CLIPModel.from_pretrained(CLIP_MODEL, local_files_only=not ALLOW_DOWNLOAD).eval()
            _clip["proc"] = CLIPProcessor.from_pretrained(CLIP_MODEL, local_files_only=not ALLOW_DOWNLOAD)
        except Exception as exc:  # noqa: BLE001 -- reported verbatim
            _clip["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    ok = _clip["model"] is not None
    return {"available": ok, "model": CLIP_MODEL if ok else None, "reason": None if ok else (_clip["error"] or "not initialised"),
            "how_to_enable": "pip install transformers torch ; then run once with TREASURYX_ALLOW_MODEL_DOWNLOAD=1 to cache the weights locally (~600 MB). Not available on the free-tier deployment."}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9/\-]+", text.lower()))


def rank_clip(query: str, images: list[np.ndarray]) -> list[float]:
    import torch
    from PIL import Image
    m, proc = _clip["model"], _clip["proc"]
    pil = [Image.fromarray(cv2.cvtColor(i, cv2.COLOR_BGR2RGB)) for i in images]
    with torch.no_grad():
        inp = proc(text=[query], images=pil, return_tensors="pt", padding=True)
        ie = m.get_image_features(pixel_values=inp["pixel_values"])
        te = m.get_text_features(input_ids=inp["input_ids"], attention_mask=inp["attention_mask"])
        ie, te = ie / ie.norm(dim=-1, keepdim=True), te / te.norm(dim=-1, keepdim=True)
        return (ie @ te.T).squeeze(1).tolist()


def _query_kind_match(query: str) -> dict[str, float]:
    q = query.lower()
    qt = _tokens(q)
    out = {}
    for kind, syns in SYNONYMS.items():
        best = 0.0
        for s in syns:
            st = _tokens(s)
            if s in q:
                best = max(best, 1.0)
            elif st and st <= qt:
                best = max(best, 0.9)
            elif st & qt:
                best = max(best, 0.35 * len(st & qt) / len(st))
        out[kind] = best
    return out


def rank_fallback(query: str, images: list[np.ndarray], with_ocr: bool = True) -> list[dict]:
    qmatch = _query_kind_match(query)
    qtok = _tokens(query) - {"a", "an", "the", "of", "showing", "chart", "with", "that", "is", "for"}
    out = []
    for img in images:
        probs = {}
        cls = runtime.classify(img, ("cnn",)).get("cnn", {})
        if cls.get("available"):
            probs = cls["probabilities"]
        kind_score = max((qmatch[k] * probs.get(k, 0.0) for k in qmatch), default=0.0) if probs else 0.0
        words: set[str] = set()
        if with_ocr:
            from app.cv_engine.ocr import run_ocr
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if max(g.shape) < 900:
                g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            r = run_ocr(g)
            words = _tokens(r.raw_text) if r.available else set()
        overlap = (len(qtok & words) / len(qtok)) if qtok else 0.0
        score = 0.65 * kind_score + 0.35 * overlap
        top = max(probs, key=probs.get) if probs else None
        out.append({"score": round(float(score), 4), "evidence": {"classifier_top_type": top, "type_match_x_probability": round(kind_score, 3), "ocr_query_word_overlap": round(overlap, 3), "matched_words": sorted(qtok & words)}})
    return out


def reference_gallery(per_kind: int = 2) -> list[tuple[str, np.ndarray]]:
    """Synthetic reference screenshots (held-out test templates) so the search has something to rank without uploads."""
    items = []
    for kind in synth.KINDS:
        for t in range(25, 25 + per_kind):
            d = synth.render(kind, t, 0, scale=1)
            items.append((f"synthetic:{kind}#{t}", d.image))
    return items


def search(query: str, named_images: list[tuple[str, np.ndarray]], backend: str = "auto") -> dict:
    status = clip_status()
    use_clip = status["available"] and backend in ("auto", "clip")
    if backend == "clip" and not status["available"]:
        raise RuntimeError(f"CLIP backend requested but unavailable: {status['reason']}")
    imgs = [i for _, i in named_images]
    if use_clip:
        scores = rank_clip(query, imgs)
        rows = [{"name": n, "score": round(float(s), 4), "evidence": None} for (n, _), s in zip(named_images, scores)]
        explain = "Cosine similarity between CLIP image and text embeddings. Higher = more semantically similar; it is not a probability and is not calibrated (typical matches sit around 0.2-0.35)."
    else:
        fb = rank_fallback(query, imgs)
        rows = [{"name": n, **f} for (n, _), f in zip(named_images, fb)]
        explain = "FALLBACK keyword heuristic (CLIP did not run): query words matched against document-type synonyms weighted by the project's own classifier, plus OCR word overlap. It cannot judge visual properties such as 'steepening'."
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return {"query": query, "backend": "clip" if use_clip else "fallback_keyword_heuristic", "clip_ran": bool(use_clip), "clip_status": status, "results": rows,
            "score_meaning": explain,
            "limitations": ["Scores rank candidates against each other; a high score on a poor candidate set is still a poor match.",
                            "Direction/shape phrases ('steepening', 'inverted') are not reliably resolved by CLIP and not at all by the fallback."]}
