"""Document parser module supporting PDF, DOCX, and TXT formats.

Uses PyMuPDF for text PDFs, pdfplumber for complex layouts,
and python-docx for DOCX files. Falls back gracefully.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger


class DocumentParser:
    """Multi-format document parser for legal documents.

    Supports: PDF (text + scanned via OCR), DOCX, TXT.
    """

    SUPPORTED_MIMETYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "doc",
        "text/plain": "txt",
        "application/rtf": "rtf",
    }

    def __init__(self) -> None:
        pass

    def parse(self, file_path: str | Path, mime_type: str | None = None) -> dict[str, Any]:
        """Parse a document and extract text content.

        Args:
            file_path: Path to the document file.
            mime_type: Optional MIME type hint.

        Returns:
            Dict with keys: text, pages, metadata, format, needs_ocr.
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf" or mime_type == "application/pdf":
            return self._parse_pdf(file_path)
        elif suffix in (".docx", ".doc") or "wordprocessingml" in (mime_type or ""):
            return self._parse_docx(file_path)
        elif suffix == ".txt" or mime_type == "text/plain":
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _parse_pdf(self, file_path: Path) -> dict[str, Any]:
        """Parse a PDF document using PyMuPDF + pdfplumber fallback."""
        text_pages: list[str] = []
        metadata: dict[str, Any] = {}
        needs_ocr = False

        # Try PyMuPDF first (faster, handles text PDFs well)
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(file_path))
            metadata = dict(doc.metadata)
            total_chars = 0

            for page in doc:
                page_text = page.get_text("text")
                text_pages.append(page_text)
                total_chars += len(page_text.strip())

            doc.close()

            # If very little text extracted, flag for OCR
            if total_chars < 100 and len(text_pages) > 0:
                needs_ocr = True
                logger.info(f"Low text extraction ({total_chars} chars), OCR fallback triggered: {file_path.name}")
                try:
                    from app.document_pipeline.ocr import OCREngine
                    ocr = OCREngine()
                    if ocr.ocr is not None:
                        ocr_text = ocr.extract_text_from_pdf(file_path)
                        if ocr_text.strip():
                            text_pages = ocr_text.split("\n\n")
                            needs_ocr = False
                            logger.info(f"OCR successfully extracted {len(ocr_text)} characters across {len(text_pages)} pages.")
                except Exception as ocr_exc:
                    logger.error(f"OCR fallback failed: {ocr_exc}")

        except ImportError:
            logger.warning("PyMuPDF not installed. Falling back to pdfplumber.")
            text_pages, metadata = self._parse_pdf_with_pdfplumber(file_path)
        except Exception as exc:
            logger.error(f"PyMuPDF parsing failed: {exc}. Trying pdfplumber.")
            try:
                text_pages, metadata = self._parse_pdf_with_pdfplumber(file_path)
            except Exception as exc2:
                logger.error(f"pdfplumber also failed: {exc2}")
                raise RuntimeError(f"Failed to parse PDF: {file_path.name}") from exc2

        full_text = "\n\n".join(text_pages)
        return {
            "text": full_text,
            "pages": text_pages,
            "page_count": len(text_pages),
            "metadata": metadata,
            "format": "pdf",
            "needs_ocr": needs_ocr,
        }

    def _parse_pdf_with_pdfplumber(self, file_path: Path) -> tuple[list[str], dict]:
        """Fallback PDF parser using pdfplumber."""
        import pdfplumber

        text_pages: list[str] = []
        metadata: dict[str, Any] = {}

        with pdfplumber.open(str(file_path)) as pdf:
            metadata = pdf.metadata or {}
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_pages.append(text)

        return text_pages, metadata

    def _parse_docx(self, file_path: Path) -> dict[str, Any]:
        """Parse a DOCX document using python-docx."""
        try:
            from docx import Document

            doc = Document(str(file_path))
            full_text = "\n".join(para.text for para in doc.paragraphs)

            return {
                "text": full_text,
                "pages": [full_text],
                "page_count": 1,
                "metadata": {},
                "format": "docx",
                "needs_ocr": False,
            }
        except ImportError:
            raise ImportError("python-docx is required for DOCX parsing")
        except Exception as exc:
            raise RuntimeError(f"Failed to parse DOCX: {file_path.name}") from exc

    def _parse_txt(self, file_path: Path) -> dict[str, Any]:
        """Parse a plain text file."""
        with open(file_path, encoding="utf-8", errors="replace") as f:
            text = f.read()

        return {
            "text": text,
            "pages": [text],
            "page_count": 1,
            "metadata": {},
            "format": "txt",
            "needs_ocr": False,
        }
