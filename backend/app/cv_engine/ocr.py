"""
Stage 3 -- OCR / information extraction.

Uses pytesseract (wraps the Tesseract OCR engine). If the Tesseract binary is not
installed on the host machine, this module degrades gracefully: it returns an empty
result with a clear warning rather than crashing the request (section 30: never let
bad data silently produce misleading results).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

try:
    import shutil
    from pathlib import Path

    import pytesseract
    from pytesseract import Output
    _TESSERACT_IMPORT_OK = True

    if shutil.which("tesseract") is None:
        # Common Windows install location (e.g. via the UB-Mannheim installer / winget)
        # not always on PATH within a given shell session.
        for candidate in (
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ):
            if candidate.exists():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                break
except ImportError:
    _TESSERACT_IMPORT_OK = False


@dataclass
class OcrWord:
    text: str
    conf: float
    x: int
    y: int
    w: int
    h: int


@dataclass
class OcrResult:
    words: list[OcrWord] = field(default_factory=list)
    raw_text: str = ""
    available: bool = True
    warning: str | None = None


NUMBER_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?")
DATE_RE = re.compile(r"\b\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
INSTRUMENT_RE = re.compile(
    r"\b(USD/?INR|EUR/?INR|GBP/?INR|EUR/?USD|10Y|5Y|2Y|1Y|6M|3M|1M|30Y|G-?SEC|GS\s?\d)\b", re.IGNORECASE,
)


def run_ocr(gray: np.ndarray) -> OcrResult:
    if not _TESSERACT_IMPORT_OK:
        return OcrResult(available=False, warning="pytesseract is not installed in this environment")
    try:
        data = pytesseract.image_to_data(gray, output_type=Output.DICT)
    except Exception as exc:  # tesseract binary missing / misconfigured
        return OcrResult(
            available=False,
            warning=f"Tesseract OCR engine not available on this machine ({exc}). "
                    "Install the Tesseract binary to enable OCR; the rest of the pipeline still ran.",
        )

    words: list[OcrWord] = []
    texts: list[str] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        conf_raw = data["conf"][i]
        try:
            conf = float(conf_raw)
        except (TypeError, ValueError):
            conf = -1.0
        if not text or conf < 0:
            continue
        words.append(OcrWord(
            text=text, conf=conf / 100.0,
            x=int(data["left"][i]), y=int(data["top"][i]),
            w=int(data["width"][i]), h=int(data["height"][i]),
        ))
        texts.append(text)

    return OcrResult(words=words, raw_text=" ".join(texts), available=True)


def extract_numbers(words: list[OcrWord]) -> list[tuple[str, OcrWord]]:
    hits = []
    for w in words:
        m = NUMBER_RE.fullmatch(w.text.replace(",", ""))
        if m:
            hits.append((w.text, w))
    return hits


def extract_instrument_mentions(words: list[OcrWord]) -> list[tuple[str, OcrWord]]:
    hits = []
    for w in words:
        if INSTRUMENT_RE.search(w.text):
            hits.append((w.text.upper().replace(" ", ""), w))
    return hits


def extract_dates(words: list[OcrWord]) -> list[tuple[str, OcrWord]]:
    hits = []
    for w in words:
        if DATE_RE.search(w.text):
            hits.append((w.text, w))
    return hits
