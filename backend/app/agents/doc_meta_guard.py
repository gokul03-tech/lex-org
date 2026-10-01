"""Guard against "poison pill" meta-text and non-narrative regions.

Documents that are dossiers, study guides or teaching material carry sections
that describe the document itself rather than the litigation ("CASE STUDY FOR
LEGAL-AI", "CONCLUSION AND REFERENCES", "WHY THIS IS A CYBER-CRIME CASE",
bibliographies). Those blocks poison three modules at once:

  * the conclusion / IRAC (it grabbed section 20, a self-description)
  * the action plan (it emitted "This expanded dossier is intended to...")
  * the timeline (it pulled dates out of the References list)

This module locates those regions once so every consumer can exclude them.
"""

from __future__ import annotations

import re
from typing import Any

# Section headings that describe the DOCUMENT, not the litigation.
META_SECTION_PATTERNS = [
    r'CASE\s+STUDY\s+FOR\s+LEGAL[\s\-]*AI',
    r'CONCLUSION\s+AND\s+REFERENCES',
    r'REFERENCES?',
    r'BIBLIOGRAPHY',
    r'WORKS?\s+CITED',
    r'LIST\s+OF\s+AUTHORITIES',
    r'WHY\s+THIS\s+IS\s+A[\s\-]',
    r'ACADEMIC\s+(?:CASE\s+)?DOSSIER',
    r'CASE\s+SIGNIFICANCE\s+AND\s+CRITICAL\s+ANALYSIS',
    r'(?:VICTIM[\s\-]*PROTECTION|VICTIM)\s+AND\s+CYBERSECURITY\s+LESSONS',
    r'COMPARISON\s+WITH\s+MODERN\s+INVESTIGATIONS',
    r'DIGITAL\s+FORENSICS\s+ANALYSIS',
    r'HOW\s+TO\s+USE\s+THIS\s+(?:DOCUMENT|DOSSIER)',
    r'NOTE\s+FOR\s+(?:STUDENTS|READERS)',
    r'ABOUT\s+THIS\s+(?:DOCUMENT|DOSSIER)',
]

# Phrases that betray self-referential commentary when they appear mid-text.
META_SENTENCE_PATTERNS = [
    r'this\s+(?:expanded\s+)?(?:dossier|document|section|study\s+guide)\s+is\s+intended',
    r'this\s+document\s+is\s+(?:an?\s+)?(?:expanded|academic|not\s+a)',
    r'for\s+academic\s+(?:work|use|purposes)',
    r'this\s+section\s+(?:is|provides|covers|presents)',
    r'the\s+(?:original\s+)?(?:judgment|court)\s+and\s+official\s+statutory\s+sources\s+should',
    r'readers?\s+(?:should|may)\s+refer',
    r'suitable\s+for\s+(?:students?|projects?|classroom)',
    r'structured\s+(?:for|around)\s+(?:students?|academic)',
    r'avoiding\s+invented\s+facts',
    r'historical\s+(?:facts|value|importance)\s+should\s+be\s+preserved',
    r'presenting\s+commentary\s+as',
    r'india\s+code\s*[—\-]',
    r'\bEnd\s+of\s+(?:case\s+)?document\b',
    # Methodological self-description: the document explaining its own sourcing
    # or quoting conventions rather than anything about the litigation.
    r'this\s+(?:dossier|document|section|study\s+guide|exhibit)\s+(?:does\s+not|'
    r'is\s+not\s+intended|does\s+not\s+present|omits|quotes|summari[sz]es|'
    r'separates|avoids|restates)',
    r'because\s+secondary\s+sources?\s+(?:sometimes|may|often)',
    r'(?:does\s+not|not)\s+present\s+a\s+long\s+quotation',
    r'long\s+quotation\s+as\s+though\s+it\s+were',
    r'\bcertified\s+original\b',
    r'quoting\s+conventions?',
    r'is\s+intended\s+to\s+provide\s+a\s+clear',
]

_META_SECTION_RE = re.compile(
    # Anchored on a line, but allow trailing sub-text on the heading line itself
    # ("20. CONCLUSION AND REFERENCES", "19. CASE STUDY FOR LEGAL-AI /
    # CYBERSECURITY PROJECTS" wrapped across two lines). A strict "end of line"
    # anchor missed every heading that carried a qualifier after the pattern.
    r'^[ \t]*(?:\d+\s*[.)]\s*)?(?:%s)' % '|'.join(META_SECTION_PATTERNS),
    re.IGNORECASE | re.MULTILINE,
)
_META_SENTENCE_RE = re.compile('|'.join(META_SENTENCE_PATTERNS), re.IGNORECASE)
_REFERENCES_HEADING_RE = re.compile(
    r'^[ \t]*(?:\d+\s*[.)]\s*)?(?:REFERENCES|BIBLIOGRAPHY|WORKS\s+CITED)\b',
    re.IGNORECASE,
)


def meta_section_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of document-about-the-document sections."""
    if not text:
        return []
    spans: list[tuple[int, int]] = []
    for m in _META_SECTION_RE.finditer(text):
        start = m.start()
        # Section runs to the next numbered/uppercase heading.
        nxt = re.compile(
            r'^[ \t]*(?:\d{1,2}\s*[.)]\s*)?[A-Z][A-Z &/,\'-]{5,70}[ \t]*$',
            re.MULTILINE,
        ).search(text, m.end())
        spans.append((start, nxt.start() if nxt else len(text)))
    return spans


def strip_meta_sections(text: str) -> str:
    """Remove dossier/meta sections so downstream extraction sees the record only."""
    if not text:
        return text
    spans = meta_section_spans(text)
    if not spans:
        return text
    out, cursor = [], 0
    for start, end in sorted(spans):
        if start < cursor:
            continue
        out.append(text[cursor:start])
        cursor = end
    out.append(text[cursor:])
    return re.sub(r'\n{3,}', '\n\n', ''.join(out)).strip()


def strip_reference_blocks(text: str) -> str:
    """Drop trailing bibliography content (numbered citation lists)."""
    if not text:
        return text
    matches = list(_REFERENCES_HEADING_RE.finditer(text))
    if not matches:
        return text
    last = matches[-1]
    return text[: last.start()].rstrip()


def is_meta_text(text: str) -> bool:
    """True when a snippet is self-referential commentary, not case content."""
    if not text:
        return False
    return bool(_META_SENTENCE_RE.search(text))


def filter_meta_items(items: list[Any], text_key: str = 'text') -> list[Any]:
    """Drop list entries whose content is document-about-the-document prose."""
    out: list[Any] = []
    for item in items or []:
        value = item
        if isinstance(item, dict):
            value = item.get(text_key) or item.get('fact') or item.get('event') or ''
        if isinstance(value, str) and is_meta_text(value):
            continue
        out.append(item)
    return out
