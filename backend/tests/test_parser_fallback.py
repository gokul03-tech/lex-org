"""Regression tests for DocumentParser fallback paths (item: parser indentation)."""

from __future__ import annotations

import sys

import pytest

from app.document_pipeline.parser import DocumentParser


def test_fallback_parsers_are_real_class_methods() -> None:
    """Regression: the fallback parsers must be class methods, not dead nested code.

    Previously `_parse_pdf_with_pdfplumber`, `_parse_docx` and `_parse_txt` were
    indented inside the module-level `_strip_markup` helper after its `return`,
    making them unreachable and breaking DOCX/TXT/pdfplumber parsing entirely.
    """
    for name in ("_parse_pdf_with_pdfplumber", "_parse_docx", "_parse_txt"):
        assert callable(getattr(DocumentParser, name)), f"{name} is not a method"


def test_parse_txt_strips_markup_and_entities(tmp_path) -> None:
    """Plain-text parsing works and normalises HTML markup/entities."""
    path = tmp_path / "sample.txt"
    path.write_text("<b>Case:</b> State of TN v. Katti &amp; Co", encoding="utf-8")

    out = DocumentParser().parse(str(path))

    assert out["format"] == "txt"
    assert out["text"] == "Case: State of TN v. Katti & Co"
    assert out["page_count"] == 1


def test_parse_docx(tmp_path) -> None:
    """DOCX parsing is reachable (regression for the dead nested method)."""
    pytest.importorskip("docx")
    from docx import Document

    document = Document()
    document.add_paragraph("Petition under Section 483 of the BNSS, 2023")
    path = tmp_path / "sample.docx"
    document.save(str(path))

    out = DocumentParser().parse(str(path))

    assert out["format"] == "docx"
    assert "483" in out["text"]


def test_pdf_falls_back_to_pdfplumber_when_fitz_missing(tmp_path, monkeypatch) -> None:
    """When PyMuPDF is unavailable, parsing delegates to the pdfplumber path."""
    monkeypatch.setitem(sys.modules, "fitz", None)

    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 minimal")

    called: dict[str, bool] = {}

    def _fake_fallback(self, file_path):
        called["hit"] = True
        return (["fallback page text"], {"Producer": "test"})

    monkeypatch.setattr(DocumentParser, "_parse_pdf_with_pdfplumber", _fake_fallback)

    out = DocumentParser().parse(str(path))

    assert called.get("hit") is True
    assert "fallback page text" in out["text"]
    assert out["format"] == "pdf"
