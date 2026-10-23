"""Vision-LLM OCR fallback for badly scanned PDFs.

When PyMuPDF extracts too little text or too much noise, the pages are rendered
to images and read by an OpenRouter multimodal model. This bypasses brittle
text-layer extraction entirely and corrects visual OCR errors in context, while
still degrading to the existing PyMuPDF/PaddleOCR output when the call fails.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings

# Characters that legitimately appear in extracted legal prose. Anything else
# (control glyphs, mojibake, stray symbols) counts as "garbage".
_ALLOWED_PUNCT = set(" \n\t\r.,;:()[]{}\"'`/\\-–—_&*%#@!?+=<>|")


def garbage_ratio(text: str) -> float:
    """Fraction of characters that are not alphanumerics or common punctuation."""
    if not text:
        return 1.0
    junk = sum(1 for c in text if not c.isalnum() and c not in _ALLOWED_PUNCT)
    return junk / len(text)


def needs_vlm_ocr(text: str, *, min_chars: int = 500, max_garbage: float = 0.15) -> bool:
    """True when extraction looks like a bad scan.

    Mirrors the ``extract_text_smart`` gate: too little text (< 500 chars) or a
    garbage-character ratio above 15% means the text layer is unusable.
    """
    if not text or not text.strip():
        return True
    if len(text.strip()) < min_chars:
        return True
    return garbage_ratio(text) > max_garbage


VLM_OCR_PROMPT = """You are an expert legal document digitizer for Indian court judgments.
Read the text from these images accurately.
CRITICAL RULES:
1. Fix visual ambiguities (e.g. if a number looks like "52g" but context implies
   "528", output "528").
2. Fix garbled words (e.g. "Indran" -> "Indian", "fillr-rg" -> "filing").
3. Preserve the exact legal structure, dates, case numbers and section numbers.
4. Return ONLY the clean, extracted text. Do not add conversational filler."""


def _render_pdf_pages(pdf_path: str | Path, max_pages: int, dpi: int = 200) -> list[bytes]:
    """Render the first ``max_pages`` pages of a PDF to PNG bytes."""
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    try:
        images: list[bytes] = []
        for page_num in range(min(len(doc), max_pages)):
            pix = doc.load_page(page_num).get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
        return images
    finally:
        doc.close()


def vlm_ocr_fallback(
    pdf_path: str | Path,
    provider: Any = None,
    max_pages: int | None = None,
) -> str:
    """Read the leading pages of a scanned PDF with a multimodal LLM.

    Returns the extracted text, or "" when disabled/unavailable/failed so the
    caller keeps the PyMuPDF/PaddleOCR result.
    """
    if not settings.VLM_OCR_ENABLED:
        return ""
    pages = max_pages or settings.VLM_OCR_MAX_PAGES
    try:
        images = _render_pdf_pages(pdf_path, pages)
    except Exception as exc:  # noqa: BLE001 - fallback must never raise
        logger.warning(f"VLM OCR: could not render {pdf_path}: {exc}")
        return ""
    if not images:
        return ""

    if provider is None:
        from app.llm.routing import get_vision_provider

        provider = get_vision_provider()
    if not hasattr(provider, "generate_with_images"):
        logger.warning("VLM OCR: active provider has no multimodal support; skipping.")
        return ""

    try:
        text = provider.generate_with_images(
            VLM_OCR_PROMPT, images, max_tokens=8000, temperature=0.0
        )
    except Exception as exc:  # noqa: BLE001 - degrade to text layer
        logger.error(f"VLM OCR request failed: {exc}")
        return ""
    if not text or text.startswith("Model response unavailable"):
        return ""
    logger.info(
        f"VLM OCR extracted {len(text)} chars from {len(images)} page(s) of "
        f"{Path(pdf_path).name}"
    )
    return text
