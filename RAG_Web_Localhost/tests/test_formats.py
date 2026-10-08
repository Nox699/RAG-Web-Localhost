from pathlib import Path

from docx import Document
from pypdf import PdfWriter

from app.core import extract_text


def test_docx_extraction(tmp_path: Path):
    path = tmp_path / "note.docx"
    doc = Document()
    doc.add_paragraph("Hello from DOCX")
    doc.save(path)
    assert "Hello from DOCX" in extract_text(path)


def test_text_extraction_utf8_bom(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("Hej æøå", encoding="utf-8-sig")
    assert extract_text(path) == "Hej æøå"
