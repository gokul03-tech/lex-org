"""Text cleaner for legal documents.

Removes artifacts from OCR and PDF extraction:
headers/footers, page numbers, encoding issues, excess whitespace.
"""

from __future__ import annotations

import re
from typing import Any


class TextCleaner:
    """Clean and normalize extracted legal text."""

    # Common patterns in legal PDF extracts
    PAGE_NUMBER_PATTERNS = [
        re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE),  # Standalone page numbers
        re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\s*-\s*\d+\s*-\s*$", re.MULTILINE),  # - 42 -
    ]

    HEADER_FOOTER_PATTERNS = [
        re.compile(r"^THE\s+\w+\s+ACT,\s+\d{4}\s*$", re.MULTILINE),  # "THE ... ACT, 2023"
        re.compile(r"^\s*\[?\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\]?\s*$", re.MULTILINE),
        re.compile(r"^\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", re.MULTILINE),  # Date lines
    ]

    def __init__(self) -> None:
        pass

    def clean(self, text: str, remove_headers: bool = True) -> str:
        """Clean and normalize extracted text.

        Args:
            text: Raw extracted text.
            remove_headers: Whether to strip detected headers/footers.

        Returns:
            Cleaned and normalized text.
        """
        if not text or not text.strip():
            return ""

        # Fix common encoding issues
        text = self._fix_encoding(text)

        # Remove page numbers
        text = self._remove_page_numbers(text)

        # Remove headers/footers
        if remove_headers:
            text = self._remove_headers_footers(text)

        # Normalize whitespace
        text = self._normalize_whitespace(text)

        # Remove excessive newlines (more than 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove lines that are just punctuation
        text = re.sub(r"^\s*[-_=]{3,}\s*$", "", text, flags=re.MULTILINE)

        # Fix hyphenated line breaks (word broken across lines)
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

        return text.strip()

    def _fix_encoding(self, text: str) -> str:
        """Fix common PDF extraction encoding issues."""
        replacements = {
            "\u2018": "'",  # Left single quote
            "\u2019": "'",  # Right single quote
            "\u201c": '"',  # Left double quote
            "\u201d": '"',  # Right double quote
            "\u2013": "-",  # En dash
            "\u2014": "--", # Em dash
            "\u00a0": " ",  # Non-breaking space
            "\u00ad": "",   # Soft hyphen
            "\ufb01": "fi", # fi ligature
            "\ufb02": "fl", # fl ligature
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _remove_page_numbers(self, text: str) -> str:
        """Remove standalone page numbers."""
        for pattern in self.PAGE_NUMBER_PATTERNS:
            text = pattern.sub("", text)
        return text

    def _remove_headers_footers(self, text: str) -> str:
        """Remove common header/footer patterns."""
        for pattern in self.HEADER_FOOTER_PATTERNS:
            text = pattern.sub("", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace without collapsing paragraph breaks."""
        # Collapse multiple spaces within lines
        lines = text.split("\n")
        cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
        return "\n".join(cleaned_lines)

    def extract_sections(self, text: str) -> dict[str, Any]:
        """Attempt to identify legal section boundaries in cleaned text.

        Args:
            text: Cleaned legal text.

        Returns:
            Dict with 'sections' list and 'preamble' text.
        """
        # Pattern for Indian legal sections: "1. Title" or "Section 1 - Title"
        section_pattern = re.compile(
            r"(?:^|\n)(?:(?:Section|Sec\.?)\s*)?(\d+[A-Z]?)\.?\s*[-–—:]?\s*(.+?)(?=\n(?:(?:Section|Sec\.?)\s*)?\d+[A-Z]?\.?\s|$)",
            re.MULTILINE | re.DOTALL,
        )

        sections: list[dict[str, Any]] = []
        preamble = text

        matches = list(section_pattern.finditer(text))
        if matches:
            first_match_start = matches[0].start()
            preamble = text[:first_match_start].strip()

            for match in matches:
                section_num = match.group(1)
                section_content = match.group(2).strip()
                sections.append({
                    "section_number": section_num,
                    "content": section_content,
                    "char_count": len(section_content),
                })

        return {
            "preamble": preamble,
            "sections": sections,
            "section_count": len(sections),
        }
