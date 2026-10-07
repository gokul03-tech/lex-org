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
    r'AUTHORITIES\s+AND\s+SOURCE\s+NOTE',
    r'^\s*LIST\s+OF\s+AUTHORITIES',
    r'TABLE\s+OF\s+(?:CONTENTS|AUTHORITIES)',
    r'CERTIFICATE\s+AND\s+DECLARATION',
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
    # The subject may be a *file* or *case* rather than the noun set above.
    # "This educational file does not independently conclude ..." and "The Suhas
    # Katti case itself should not be rewritten ..." both describe how the
    # document was produced, and both were being mined as findings and
    # limitations -- so a disclaimer was reported as the case's key strength.
    r'this\s+(?:educational|illustrative|fictional|training|sample|demonstration|'
    r'practice|teaching)\s+(?:file|case|dossier|document)',
    r'\b(?:case|file|document)\s+itself\s+should\s+not\s+be\s+'
    r'(?:rewritten|re-?written|recast|updated|moderni[sz]ed)',
    r'because\s+secondary\s+sources?\s+(?:sometimes|may|often)',
    r'(?:does\s+not|not)\s+present\s+a\s+long\s+quotation',
    r'long\s+quotation\s+as\s+though\s+it\s+were',
    r'\bcertified\s+original\b',
    r'quoting\s+conventions?',
    r'is\s+intended\s+to\s+provide\s+a\s+clear',
    # Academic-compilation disclaimers: self-description, not case outcome.
    r'this\s+case\s+file\s+is\s+an?\s+academic\s+compilation',
    r'based\s+on\s+the\s+case\s+material\s+supplied\s+with\s+the\s+task',
    r'should\s+not\s+be\s+(?:relied|treated)\s+on',
    r'this\s+document\s+is\s+prepared\s+for\s+academic\s+purposes',
    r'for\s+study\s+and\s+presentation',
    # Methodology instruction: the document telling the READER how to analyse a
    # case, rather than either side arguing it. These are not submissions and
    # must not be attributed to a party.
    r'a\s+proper\s+case\s+analysis\s+should',
    r'(?:should|must)\s+be\s+(?:read|understood|analyse[d]?|analyze[d]?|treated)\s+'
    r'(?:with|as|in\s+light\s+of)',
    r"the\s+phrase\s+['\"][^'\"]+['\"]\s+must\s+be\s+read",
    r'(?:is|are)\s+therefore\s+treated\s+as?\b',
    r'case\s+analysis\s+should\s+separate',
    r'this\s+(?:file|document)\s+should\s+be\s+read\s+as',
    # Evidentiary hedge about the record itself. "The actual contract is not
    # included in the supplied text" describes a gap in the file, not an
    # argument by anyone; as a submission bullet it misattributes a caveat.
    r'\bis\s+not\s+(?:included|provided|reproduced|set\s+out|available)\s+in\s+'
    r'(?:the\s+|this\s+)?(?:supplied|given|provided)?\s*'
    r'(?:text|extract|file|record|document)s?\b',
    r'\bthe\s+extract\s+does\s+not\s+(?:provide|contain|include|state|specify)\b',
    r"\bthis\s+is\s+the\s+State['\u2019]?s\s+submission,\s*not\s+a\s+(?:final\s+)?finding\b",
    # Trailing fragment of the methodology paragraph above. "A proper case
    # analysis should separate ..." is caught, but the sentence that follows it
    # in the same paragraph ("These categories are not interchangeable.") is
    # the conclusion of that advice rather than an argument by anyone. It was
    # the first item in the State's submission column, which misattributes the
    # document's own editorial instruction to the prosecution.
    r'\bthese\s+(?:categories|distinctions)\s+are\s+not\s+interchangeable\b',
    r'\bsuch\s+details\s+should\s+not\s+be\s+added\b',
    r'\bthose\s+details\s+should\s+not\s+be\s+(?:added|inferred|fabricated)\b',
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


# Standalone noise markers: single lines that carry no case content but that
# the model otherwise reads as argument ("ACADEMIC CASE STUDY", "ILLUSTRATIVE
# ONLY", a bare page stamp). These survive strip_meta_sections because they are
# not sections - there is no body to bound them - so they need their own pass.
_STANDALONE_NOISE_RE = re.compile(
    r'^[ \t]*(?:'
    r'ACADEMIC\s+(?:CASE\s+)?(?:STUDY|DOSSIER|EXERCISE|PURPOSE)[^\n]{0,60}'
    r'|CASE\s+STUDY\s+FOR\s+LEGAL[^\n]{0,40}'
    r'|ILLUSTRATIVE\s+ONLY(?:[ \t]*[\u2014\u2013-][^\n]{0,110})?'
    r'|FOR\s+(?:ACADEMIC|EDUCATIONAL|TRAINING)\s+PURPOSES?\s+ONLY'
    r'|CASE\s+FILE\s+SUMMARY'
    r'|END\s+NOTE\s*:?[^\n]{0,80}'
    r'|\(?\s*PAGE\s+\d{1,4}(?:\s+OF\s+\d{1,4})?\s*\)?'
    r'|\[?\s*PAGE\s+\d{1,4}\s*\]?'
    r')[ \t]*$',
    re.IGNORECASE | re.MULTILINE,
)


def strip_standalone_noise(text: str) -> str:
    """Remove single-line academic/page markers that carry no case content.

    Applied to text bound for an LLM prompt. These markers repeat on many
    pages and are pure document furniture: a model that reads "ILLUSTRATIVE
    ONLY" twenty times treats it as a party assertion, which is how an
    illustrative file ends up quoted as if it were a holding.
    """
    if not text:
        return text
    out = _STANDALONE_NOISE_RE.sub('', text)
    # A watermark is sometimes mid-line rather than alone on its line.
    out = re.sub(r'[ \t]*(?:ACADEMIC\s+CASE\s+STUDY|ILLUSTRATIVE\s+ONLY)[ \t]*', ' ', out, flags=re.IGNORECASE)
    return re.sub(r'\n{3,}', '\n\n', out).strip()


# Full-sentence academic disclaimers. Unlike the standalone line stamps above,
# these run as complete sentences ("This educational file does not
# independently conclude ...", "END NOTE: This is an expanded educational case
# study"), so a line-level regex leaves them in the prompt, where the model
# reads them as party assertions or findings. They must be removed at the
# sentence level.
ACADEMIC_NOISE_PHRASES = (
    "this educational file does not independently conclude",
    "this document is prepared for academic purposes",
    "this case file is fictional",
    "fictional case file",
    "this is not an official court record",
    "not an official court record",
    "illustrative only",
    "academic case study",
    "this is an expanded educational case study",
    "for academic and training purposes",
)

_ACADEMIC_NOISE_RE = re.compile(
    '|'.join(re.escape(p) for p in ACADEMIC_NOISE_PHRASES),
    re.IGNORECASE,
)


def strip_academic_noise(text: str) -> str:
    """Remove whole sentences that describe the document, not the litigation.

    A dossier disclaimer survives section- and line-level stripping when it is
    a grammatical sentence rather than a bare stamp ("ILLUSTRATIVE ONLY" as a
    line is already handled). Splitting into sentences so the removal never
    cuts mid-sentence or joins the disclaimer to a real finding on either side.
    """
    if not text:
        return text
    changed = False
    paragraphs = []
    for para in text.split('\n\n'):
        # Sentence boundary: [.!?] followed by whitespace and an uppercase/
        # quote/opening-bracket start, so "Case No. 123" keeps its fragment.
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\u201c\u2018(\[])', para)
        kept = [s for s in sentences if not _ACADEMIC_NOISE_RE.search(s)]
        if len(kept) != len(sentences):
            changed = True
        paragraphs.append(' '.join(kept))
    if not changed:
        return text
    return re.sub(r'\n{3,}', '\n\n', '\n\n'.join(paragraphs)).strip()


def filter_url_artifacts(text: str) -> str:
    """Remove URL artifacts from extracted text."""
    # Remove Indian Kanoon URLs (citation breadcrumbs, often glued to a label)
    text = re.sub(r'Indian Kanoon[-\s]*http[s]?://[^\s]+', '', text)
    # Remove standalone URLs and their trailing punctuation residue
    text = re.sub(r'http[s]?://[^\s]+', '', text)
    # Tidy the whitespace left behind by a removed URL
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


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
