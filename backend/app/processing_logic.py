"""Simulated document processing — replace with real parsers/OCR as needed."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any, Optional


def read_text_sample(path: str, max_bytes: int = 256_000) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    data = p.read_bytes()[:max_bytes]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def guess_category(text: str, filename: str) -> str:
    lower = (text + " " + filename).lower()
    if any(w in lower for w in ("invoice", "total due", "bill to")):
        return "invoice"
    if any(w in lower for w in ("resume", "curriculum", "experience")):
        return "resume"
    if any(w in lower for w in ("contract", "agreement", "party of the first")):
        return "contract"
    return "general"


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    freq: dict[str, int] = {}
    stop = {"that", "this", "with", "from", "have", "will", "your", "been", "were", "they"}
    for w in words:
        if w in stop:
            continue
        freq[w] = freq.get(w, 0) + 1
    sorted_w = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_w[:limit]]


def build_structured_result(
    *,
    original_filename: str,
    stored_path: str,
    mime_type: Optional[str],
    file_size_bytes: int,
) -> dict[str, Any]:
    text = read_text_sample(stored_path)
    title = original_filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")[:120] or "Untitled"
    if text:
        first_line = text.strip().splitlines()[0][:200] if text.strip() else title
        if len(first_line) > 10:
            title = first_line
    category = guess_category(text, original_filename)
    summary_source = text[:2000] if text else original_filename
    summary = (summary_source[:500] + "…") if len(summary_source) > 500 else summary_source
    keywords = extract_keywords(text or original_filename)
    ext = Path(original_filename).suffix.lower() or mimetypes.guess_extension(mime_type or "") or ""
    return {
        "title": title.strip() or original_filename,
        "category": category,
        "summary": summary.strip(),
        "extracted_keywords": keywords,
        "status": "extracted",
        "metadata": {
            "filename": original_filename,
            "mime_type": mime_type,
            "size_bytes": file_size_bytes,
            "detected_extension": ext,
            "parsed_char_count": len(text),
        },
    }
