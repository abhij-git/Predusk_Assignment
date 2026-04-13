import json
import tempfile
from pathlib import Path

from app.processing_logic import build_structured_result, extract_keywords, guess_category


def test_guess_category_invoice() -> None:
    assert guess_category("Invoice total due", "inv.txt") == "invoice"


def test_extract_keywords() -> None:
    kw = extract_keywords("alpha beta gamma alpha delta beta", limit=3)
    assert "alpha" in kw


def test_build_structured_result(tmp_path: Path) -> None:
    f = tmp_path / "note.txt"
    f.write_text("Project roadmap for machine learning platform deployment.", encoding="utf-8")
    out = build_structured_result(
        original_filename="note.txt",
        stored_path=str(f),
        mime_type="text/plain",
        file_size_bytes=f.stat().st_size,
    )
    assert out["category"] == "general"
    assert "metadata" in out
    data = json.dumps(out)
    assert len(data) > 10
