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
FX_PAIR_RE = re.compile(r"\b(USD/?INR|EUR/?INR|GBP/?INR|EUR/?USD)\b", re.IGNORECASE)
# A general tenor pattern (1-2 digits + M/Y), not an enumerated list -- covers the full
# standard Treasury/G-Sec ladder (1M..30Y) including ones a hand-picked list would miss
# (3Y, 7Y, 15Y, 20Y, ...), and tolerates an OCR-introduced space ("10 Y" -> "10Y").
TENOR_RE = re.compile(r"\b(\d{1,2})\s?([MY])\b", re.IGNORECASE)
# "G-SEC" / "G SEC" / "GSEC" identify the ASSET CLASS (government security) -- this is
# document/context metadata, not a tradable instrument, so it must never be paired with a
# nearby number as if it were a row's value (that previously produced "Unknown bond G-SEC"
# with a garbage value grabbed from whatever number happened to be closest on the page).
# Matched per-word in detect_asset_class() below, not via a regex on the raw text.


def run_ocr(gray: np.ndarray) -> OcrResult:
    if not _TESSERACT_IMPORT_OK:
        return OcrResult(available=False, warning="pytesseract is not installed in this environment")
    try:
        # PSM 6 ("assume a single uniform block of text") reads a chart/table screenshot's
        # short, disconnected tokens (tenor labels, numeric callouts) far more reliably
        # than Tesseract's default PSM 3 (assumes a full page of prose) -- measurably fewer
        # misreads on financial tables/charts, the image type this pipeline targets.
        data = pytesseract.image_to_data(gray, output_type=Output.DICT, config="--psm 6")
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


def extract_fx_pair_mentions(words: list[OcrWord]) -> list[tuple[str, OcrWord]]:
    hits = []
    for w in words:
        m = FX_PAIR_RE.search(w.text)
        if m:
            hits.append((m.group(1).upper().replace(" ", ""), w))
    return hits


def extract_tenor_mentions(words: list[OcrWord]) -> list[tuple[str, OcrWord]]:
    """Tenor labels (3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 15Y, 20Y, 30Y, ...), normalized to a
    canonical NUMBER+UNIT form (no space) regardless of OCR spacing/case variants."""
    hits = []
    for w in words:
        m = TENOR_RE.search(w.text)
        if m:
            n, unit = m.groups()
            hits.append((f"{n}{unit.upper()}", w))
    return hits


def detect_asset_class(words: list[OcrWord]) -> str | None:
    """Document/asset-class context (e.g. a 'G-Sec Yield Curve' header) -- metadata about
    what the whole image is, never itself paired with a numeric value. Checked per OCR
    WORD by stripping non-letters and comparing the result, rather than a regex applied
    directly to the raw concatenated text: a stray misread character Tesseract sometimes
    inserts between 'G' and '-Sec' (e.g. 'G�-Sec') would otherwise break a regex
    word-boundary match while still obviously being the same token to a human reader.
    Deliberately narrower than a bare "SEC" substring check so it doesn't fire on
    unrelated words like "Securities" or "Sector"."""
    for w in words:
        cleaned = re.sub(r"[^A-Za-z]", "", w.text).upper()
        if cleaned in ("GSEC", "SEC"):
            return "government_security"
    return None


def extract_dates(words: list[OcrWord]) -> list[tuple[str, OcrWord]]:
    hits = []
    for w in words:
        if DATE_RE.search(w.text):
            hits.append((w.text, w))
    return hits
