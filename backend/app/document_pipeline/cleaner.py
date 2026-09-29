"""Text cleaner for legal documents.

Removes artifacts from OCR and PDF extraction:
headers/footers, page numbers, encoding issues, HTML leakage, excess whitespace.
"""

from __future__ import annotations

import html
import re
from typing import Any

# Tags whose *content* is markup, not prose, and must be dropped wholesale.
_DROP_CONTENT_TAGS = ("script", "style", "head", "noscript", "iframe", "svg")

# A tag is only markup if it looks like `<name ...>` / `</name>` / `<name/>`.
# Anchoring the name to a real tag vocabulary keeps prose like "a < b > c",
# "Section 3 < 5", or "x <= y" from being silently deleted.
_HTML_TAG_RE = re.compile(
    r"""
    <!--.*?-->                                   # comments
    | <!(?:DOCTYPE|doctype)[^>]*>                # doctype / bogus type
    | <\?[\s\S]*?\?>                             # processing instructions
    | </?(?:%s)\b(?:"[^"]*"|'[^']*'|[^>"'])*/?>   # known tags with attributes
    """
    % "|".join(_DROP_CONTENT_TAGS + (
        "a", "abbr", "address", "area", "article", "aside", "b", "base", "bdi",
        "bdo", "big", "blockquote", "body", "br", "caption", "center", "cite",
        "code", "col", "colgroup", "data", "dd", "del", "details", "dfn",
        "div", "dl", "dt", "em", "fieldset", "figcaption", "figure", "footer",
        "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr",
        "html", "i", "img", "input", "ins", "kbd", "label", "legend", "li",
        "link", "main", "map", "mark", "menu", "meta", "meter", "nav", "ol",
        "optgroup", "option", "output", "p", "param", "picture", "pre",
        "progress", "q", "rp", "rt", "ruby", "s", "samp", "script", "section",
        "select", "small", "source", "span", "strike", "strong", "style",
        "sub", "summary", "sup", "table", "tbody", "td", "template",
        "textarea", "tfoot", "th", "thead", "time", "title", "tr", "track",
        "u", "ul", "var", "video", "wbr",
    ))
    ,
    re.VERBOSE | re.IGNORECASE | re.DOTALL,
)

# Full elements whose content is non-prose: drop from open tag to close tag.
_DROP_BLOCK_RE = re.compile(
    r"<(%s)\b[^>]*>[\s\S]*?</\1\s*>" % "|".join(_DROP_CONTENT_TAGS),
    re.IGNORECASE,
)

# Tags that imply a line break in the rendered text.
_BLOCKISH_TAGS_RE = re.compile(
    r"</?(?:p|div|br|tr|li|h[1-6]|table|section|article|header|footer|blockquote)\b[^>]*>",
    re.IGNORECASE,
)

# Inline tags whose removal must leave a word boundary behind (e.g. <td>a</td><td>b</td>).
_INLINE_SEPARATOR_TAGS_RE = re.compile(
    r"</?(?:td|th|span|a|em|strong|b|i|u|small|sub|sup|code|mark|time|abbr)\b[^>]*>",
    re.IGNORECASE,
)


def clean_html_tags(text: str) -> str:
    """Strip HTML/XML markup from ``text``, keeping the human-readable content.

    Indian Kanoon and several judgment portals serve HTML-wrapped extracts, so raw
    tags otherwise leak into every downstream regex (party names, section numbers,
    judge names) and silently break extraction.

    Unlike a bare ``re.sub(r'<[^>]+>', '', text)``, this:
      * removes <script>/<style>/<head> bodies, not just their tags,
      * drops comments, doctypes and processing instructions,
      * preserves non-markup angle brackets (``a < b``, ``x <= y``),
      * converts <br>/<p> to newlines so paragraph structure survives,
      * unescapes entities (``&amp;`` -> ``&``, ``&nbsp;`` -> space).

    Args:
        text: Raw text that may contain HTML markup.

    Returns:
        The same text with markup removed and entities decoded.
    """
    if not text or "<" not in text and "&" not in text:
        return text or ""

    # 1. Drop non-prose elements together with their content.
    cleaned = _DROP_BLOCK_RE.sub("\n", text)

    # 2. Preserve block structure, then remove the remaining tags.
    cleaned = _BLOCKISH_TAGS_RE.sub("\n", cleaned)
    cleaned = _INLINE_SEPARATOR_TAGS_RE.sub(" ", cleaned)
    cleaned = _HTML_TAG_RE.sub("", cleaned)

    # 3. Unescape entities last so "&lt;p&gt;" cannot re-introduce markup.
    cleaned = html.unescape(cleaned)

    # 4. Normalize exotic spaces (nbsp and friends) that unescape() can reveal.
    cleaned = cleaned.replace("\xa0", " ").replace("\u200b", "")

    # 5. Tidy whitespace introduced by tag removal without collapsing structure.
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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

        # Remove HTML markup (Indian Kanoon and portal extracts are HTML-wrapped)
        text = clean_html_tags(text)

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

    # ── Running headers / footers across pages ────────────────────────
    _PAGE_LABEL_RE = re.compile(r'^\s*(?:page\s+)?\d{1,4}(?:\s+of\s+\d{1,4})?\s*$', re.I)

    def clean_pages(self, pages: list[str]) -> list[str]:
        """Clean a page list and drop headers/footers that repeat across pages.

        A multi-page judgment or dossier repeats its title on every page
        ("Cyber Crime Case Document - State of Tamil Nadu v. Suhas Katti") and
        stamps a page number on each. Those lines sit in the caption region, so
        leaving them in corrupts party names, the self-title guard and keyword
        extraction. A line is treated as running furniture only when it appears at
        the top or bottom of at least 40% of pages (and at least 2 pages), which
        keeps a one-off heading that happens to repeat inside the body.
        """
        cleaned = [self.clean(p or "") for p in pages]
        if len(cleaned) < 2:
            return cleaned

        edge_counts: dict[str, int] = {}
        for page in cleaned:
            lines = [ln.strip() for ln in page.split("\n") if ln.strip()]
            if len(lines) < 3:
                continue
            for ln in {*lines[:2], *lines[-2:]}:
                key = re.sub(r'\s+', ' ', ln).strip().lower()
                if key and not self._PAGE_LABEL_RE.match(ln):
                    edge_counts[key] = edge_counts.get(key, 0) + 1

        threshold = max(2, int(0.4 * len(cleaned)))
        running = {k for k, v in edge_counts.items() if v >= threshold}
        if not running:
            return cleaned

        out: list[str] = []
        for page in cleaned:
            kept = [
                ln for ln in page.split("\n")
                if not (
                    re.sub(r'\s+', ' ', ln).strip().lower() in running
                    or self._PAGE_LABEL_RE.match(ln.strip())
                )
            ]
            out.append("\n".join(kept).strip())
        return out

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
        text = clean_html_tags(text)
        if not text:
            return {"preamble": "", "sections": [], "section_count": 0}

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
