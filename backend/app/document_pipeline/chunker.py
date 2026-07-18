"""Semantic text chunking for legal documents.

Uses LangChain's RecursiveCharacterTextSplitter with section-aware
splitting to preserve section boundaries in legal documents.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from app.core.config import settings


class LegalChunker:
    """Semantic chunker optimized for legal documents.

    Splits text into overlapping chunks while preserving:
    - Section boundaries (numbered legal sections)
    - Paragraph integrity
    - Citation context
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        """Initialize the chunker.

        Args:
            chunk_size: Target chunk size in characters.
            chunk_overlap: Overlap between adjacent chunks.
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # Legal section boundary pattern: "1. Title" or "SECTION 1:" etc.
        self.section_boundary = re.compile(
            r"(?:^|\n)(?:(?:SECTION|Section|Art\.|Article)\s+)?\d{1,4}[A-Z]?\.?\s+[A-Z]",
            re.MULTILINE,
        )

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Split text into semantic chunks.

        Args:
            text: The cleaned document text.
            metadata: Optional metadata to attach to each chunk.

        Returns:
            List of dicts with keys: text, chunk_index, metadata, char_count.
        """
        if not text or not text.strip():
            return []

        # First, split at section boundaries to preserve them
        sections = self._split_at_sections(text)

        # Then chunk each section if it's too large
        chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for section_text in sections:
            if len(section_text) <= self.chunk_size:
                chunks.append({
                    "text": section_text.strip(),
                    "chunk_index": chunk_index,
                    "metadata": metadata or {},
                    "char_count": len(section_text.strip()),
                })
                chunk_index += 1
            else:
                # Chunk large sections with overlap
                sub_chunks = self._chunk_text(section_text)
                for sub in sub_chunks:
                    chunks.append({
                        "text": sub.strip(),
                        "chunk_index": chunk_index,
                        "metadata": metadata or {},
                        "char_count": len(sub.strip()),
                    })
                    chunk_index += 1

        # Merge very small chunks with neighbors
        chunks = self._merge_small_chunks(chunks)

        logger.info(f"Chunked text into {len(chunks)} chunks (avg size: {sum(c['char_count'] for c in chunks) / max(len(chunks), 1):.0f} chars)")

        return chunks

    def _split_at_sections(self, text: str) -> list[str]:
        """Split text at legal section boundaries."""
        boundaries = [m.start() for m in self.section_boundary.finditer(text)]

        if not boundaries or boundaries[0] > 0:
            boundaries = [0] + boundaries

        sections: list[str] = []
        for i, start in enumerate(boundaries):
            end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)

        return sections if sections else [text]

    def _chunk_text(self, text: str) -> list[str]:
        """Split a single large text block into overlapping chunks."""
        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunks.append(text[start:])
                break

            # Try to break at a sentence boundary (period followed by space/newline)
            chunk = text[start:end]
            break_point = self._find_sentence_boundary(chunk)
            if break_point > self.chunk_size // 2:
                end = start + break_point

            chunks.append(text[start:end])
            start = end - self.chunk_overlap
            if start >= text_len:
                break

        return chunks

    def _find_sentence_boundary(self, text: str) -> int:
        """Find the best sentence boundary near the end of the text."""
        # Look for period + space/newline near the end
        for pattern in [r"\.\s+[A-Z]", r"\.\n", r"\n\n", r"\n", r"\s+"]:
            matches = list(re.finditer(pattern, text))
            if matches:
                # Get the last match that's not too close to the start
                for m in reversed(matches):
                    if m.start() > len(text) * 0.5:
                        return m.start() + 1
        return len(text)

    def _merge_small_chunks(
        self, chunks: list[dict[str, Any]], min_size: int = 100
    ) -> list[dict[str, Any]]:
        """Merge chunks smaller than min_size with their neighbors."""
        if len(chunks) <= 1:
            return chunks

        merged: list[dict[str, Any]] = []
        buffer = chunks[0]

        for chunk in chunks[1:]:
            if buffer["char_count"] < min_size:
                # Merge buffer into next chunk
                buffer["text"] = buffer["text"] + "\n\n" + chunk["text"]
                buffer["char_count"] = len(buffer["text"])
            else:
                merged.append(buffer)
                buffer = chunk

        merged.append(buffer)
        return merged

    def chunk_with_metadata(
        self,
        text: str,
        source: str,
        doc_type: str = "unknown",
        act: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Chunk text with full legal metadata.

        Args:
            text: The document text.
            source: Source identifier (filename or path).
            doc_type: Document type (petition, evidence, act, etc.).
            act: Applicable act name if known.
            extra: Any additional metadata.

        Returns:
            List of chunk dicts with enriched metadata.
        """
        metadata = {
            "source": source,
            "doc_type": doc_type,
            "act": act or "",
            **(extra or {}),
        }
        return self.chunk(text, metadata)
