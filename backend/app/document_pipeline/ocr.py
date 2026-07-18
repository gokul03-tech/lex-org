"""OCR module for scanned PDF documents using PaddleOCR.

Detects whether OCR is needed based on text extraction ratio
and processes scanned pages to extract text from images.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class OCREngine:
    """PaddleOCR-based OCR engine for scanned legal documents.

    Used as a fallback when PyMuPDF/pdfplumber cannot extract
    sufficient text from a PDF (indicating scanned images).
    """

    def __init__(self, lang: str | None = None, use_gpu: bool | None = None) -> None:
        """Initialize the OCR engine.

        Args:
            lang: OCR language code (default from settings).
            use_gpu: Whether to use GPU acceleration (default from settings).
        """
        self.lang = lang or settings.OCR_LANG
        self.use_gpu = use_gpu if use_gpu is not None else settings.OCR_USE_GPU
        self._ocr = None

    @property
    def ocr(self):
        """Lazy-load the PaddleOCR instance."""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(lang=self.lang, use_gpu=self.use_gpu)
                logger.info(f"PaddleOCR initialized: lang={self.lang}, gpu={self.use_gpu}")
            except ImportError:
                logger.warning(
                    "PaddleOCR not installed. OCR will be unavailable. "
                    "Install with: pip install paddleocr"
                )
                self._ocr = None
            except Exception as exc:
                logger.error(f"Failed to initialize PaddleOCR: {exc}")
                self._ocr = None
        return self._ocr

    def needs_ocr(self, extracted_text: str, page_count: int) -> bool:
        """Determine if OCR is needed based on text extraction quality.

        A page is considered scanned if it has fewer than ~50 characters
        of extractable text on average.

        Args:
            extracted_text: Text extracted by PyMuPDF/pdfplumber.
            page_count: Number of pages in the document.

        Returns:
            True if OCR should be applied.
        """
        if page_count == 0:
            return False
        chars_per_page = len(extracted_text.strip()) / page_count
        return chars_per_page < 50

    def extract_text_from_image(self, image_path: str | Path) -> str:
        """Extract text from a single image file.

        Args:
            image_path: Path to an image file (PNG, JPG, etc.).

        Returns:
            Extracted text string.
        """
        if self.ocr is None:
            logger.warning("OCR not available. Returning empty text.")
            return ""

        try:
            result = self.ocr.ocr(str(image_path), cls=True)
            if not result or not result[0]:
                return ""

            lines: list[str] = []
            for line_info in result[0]:
                if line_info and len(line_info) >= 2:
                    text = line_info[1][0] if isinstance(line_info[1], (list, tuple)) else str(line_info[1])
                    lines.append(text)

            return "\n".join(lines)
        except Exception as exc:
            logger.error(f"OCR failed for {image_path}: {exc}")
            return ""

    def extract_text_from_pdf(
        self,
        pdf_path: str | Path,
        dpi: int = 300,
        first_page_only: bool = False,
    ) -> str:
        """Extract text from a scanned PDF by converting pages to images.

        Args:
            pdf_path: Path to the PDF file.
            dpi: DPI for page-to-image conversion (higher = better OCR).
            first_page_only: If True, only process the first page.

        Returns:
            Concatenated OCR text from all pages.
        """
        if self.ocr is None:
            logger.warning("OCR not available. Returning empty text.")
            return ""

        try:
            import fitz  # PyMuPDF for page-to-image conversion

            doc = fitz.open(str(pdf_path))
            pages_to_process = [0] if first_page_only else range(len(doc))

            all_text: list[str] = []
            for page_num in pages_to_process:
                page = doc[page_num]
                # Render page to image
                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")

                # Save temporarily for PaddleOCR (which works with file paths)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name

                try:
                    text = self.extract_text_from_image(tmp_path)
                    all_text.append(text)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            doc.close()
            return "\n\n".join(all_text)

        except ImportError:
            logger.error("PyMuPDF (fitz) required for PDF-to-image conversion in OCR")
            return ""
        except Exception as exc:
            logger.error(f"OCR PDF processing failed for {pdf_path}: {exc}")
            return ""

    def process_pdf_with_ocr(
        self,
        pdf_path: str | Path,
        base_text: str = "",
    ) -> dict[str, Any]:
        """Process a PDF document, applying OCR where needed.

        Args:
            pdf_path: Path to the PDF file.
            base_text: Any text already extracted via non-OCR methods.

        Returns:
            Dict with keys: text, ocr_text, combined_text, ocr_page_count.
        """
        pdf_path = Path(pdf_path)

        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1

        ocr_text = ""
        if self.needs_ocr(base_text, page_count):
            logger.info(f"OCR triggered for {pdf_path.name} ({page_count} pages)")
            ocr_text = self.extract_text_from_pdf(pdf_path)
        else:
            logger.info(f"OCR not needed for {pdf_path.name}")

        combined = ocr_text if len(ocr_text) > len(base_text) else base_text

        return {
            "text": base_text,
            "ocr_text": ocr_text,
            "combined_text": combined,
            "needs_ocr": bool(ocr_text),
            "page_count": page_count,
        }
