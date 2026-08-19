"""LexOrch-KG — Deterministic Metadata Extractor (Layer 1).
Runs BEFORE the LLM so date/parties/citations/judges can never fail again.
"""
from __future__ import annotations

import re
from typing import Any


def fix_name(n: str) -> str:
    n = re.sub(r'\s+', ' ', n).strip()
    n = re.sub(r'([A-Za-z]+) ([a-z])\b', r'\1\2', n)   # OCR fix: "Ramj i" -> "Ramji"
    return n.strip(' ,;:')


def _f(value: Any, status: str) -> dict[str, Any]:
    return {"value": value, "status": status}


def extract_metadata(text: str) -> dict[str, Any]:
    head  = text[:6000]
    lines = [l.strip() for l in head.split('\n') if l.strip()]
    m: dict[str, Any] = {}

    # 1) Parties via title-split (works for civil AND criminal)
    tl = next((l for l in lines[:8] if re.search(r'\bvs\.?\b|\bv\.\b|\bversus\b', l, re.I)), '')
    if tl:
        # Strip trailing date or ... on line before splitting
        clean_tl = re.sub(r'\s+(?:\.\.\.\s*on|on)\s+\d{1,2}.*$', '', tl, flags=re.I)
        parts = re.split(r'\s+vs\.?\s+|\s+v\.\s+|\s+versus\s+', clean_tl, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            left, right = parts
            p_clean = fix_name(re.sub(r'\.\.\.\s*(?:Appellant|Petitioner|Plaintiff|Applicant)', '', left, flags=re.I))
            r_clean = fix_name(re.sub(r'\.\.\.\s*(?:Respondent|Defendant)', '', right, flags=re.I))
            m['case_title'] = _f(f"{p_clean} vs {r_clean}", 'extracted')
            m['petitioner'] = _f(p_clean, 'extracted')
            m['respondent'] = _f(r_clean, 'extracted')
        else:
            m['case_title'] = m['petitioner'] = m['respondent'] = _f(None, 'not_found')
    else:
        m['case_title'] = m['petitioner'] = m['respondent'] = _f(None, 'not_found')

    # 2) Decision date — any header format
    dm = re.search(r'(?:\.\.\.\s*on|on|decided\s+on|dated)\s+(\d{1,2})[ ,.-]+([A-Z][a-z]+)[ ,.-]+(\d{4})', head, re.I) or \
         re.search(r'(\d{1,2})[ ,]+([A-Z][a-z]+)[ ,]+(\d{4})', head)
    if dm:
        m['decision_date'] = _f(f"{dm.group(1)} {dm.group(2)} {dm.group(3)}", 'extracted')
    else:
        m['decision_date'] = _f(None, 'not_found')

    # 3) Citations — compressed + spaced forms
    cites: list[str] = []
    for pat in (
        r'AIR\s?\d{4}\s?[A-Z]{2,10}\s?\d+',
        r'\(\d{4}\)\s?\d+\s?[A-Z]+\s?\d+',
        r'\d{4}\s?CRILJ\s?\d+',
        r'\[\d{4}\]\s?\d+\s?SCR\s?\d+',
        r'\d{4}\s?SCC\s?\(\w+\)\s?\d+',
        r'ILR\s?\d{4}\s?[A-Z]+\s?\d+'
    ):
        cites += re.findall(pat, head, re.I)
    cites = list(dict.fromkeys(c.strip().replace(" ", "") for c in cites))
    m['citation_numbers'] = _f(cites or None, 'extracted' if cites else 'not_found')

    # 4) Judges — line-start "NAME, J." over WHOLE text (catches concurring judge at end)
    judges: list[str] = []
    found_j = re.findall(r'(?:^|\n)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*J\.', text)
    for j in found_j:
        j_clean = fix_name(j)
        if j_clean and j_clean not in judges and not any(k in j_clean.lower() for k in ['judgment', 'court', 'order', 'state']):
            judges.append(j_clean)

    for tag in ('Author', 'Bench', 'Coram'):
        am = re.search(tag + r':\s*([^\n]+)', head, re.I)
        if am:
            for b_seg in re.split(r',|\band\b|&', am.group(1)):
                b_clean = fix_name(re.sub(r'\b(Hon[\'’]?ble|Justice|Mr\.|Mrs\.|Ms\.|J\.)\b', '', b_seg, flags=re.I))
                if b_clean and b_clean not in judges and not any(k in b_clean.lower() for k in ['judgment', 'court', 'order', 'state']):
                    judges.append(b_clean)

    judges = list(dict.fromkeys(j.strip() for j in judges if j.strip()))
    m['presiding_judges'] = _f(judges or None, 'extracted' if judges else 'not_found')

    # 5) COURT MATTER = case number ONLY (never the court name!)
    cm = re.search(r'((?:Special\s+Case|Criminal\s+Appeal|Civil\s+Appeal|Appeal|Writ\s+Petition|Suit)\s+No\.?\s*\d+\s+of\s+\d{4})', head, re.I) or \
         re.search(r'((?:Special\s+Case|Criminal\s+Appeal|Civil\s+Appeal|Appeal|Writ\s+Petition|Suit)\s+No\.?\s*\d+\s+of\s+\d{4})', text, re.I)
    m['court_matter'] = _f(cm.group(1) if cm else None, 'extracted' if cm else 'not_found')

    # 6) COURT = name (inferred from reporter when absent)
    explicit_court = re.search(r'(Supreme\s+Court\s+of\s+India|Bombay\s+High\s+Court|High\s+Court\s+of\s+Bombay|Delhi\s+High\s+Court|High\s+Court\s+of\s+Karnataka|Karnataka\s+High\s+Court|High\s+Court\s+of\s+Mysore|Madras\s+High\s+Court|Calcutta\s+High\s+Court|Allahabad\s+High\s+Court)', head, re.I)
    if explicit_court:
        court, stat = explicit_court.group(1).strip(), 'extracted'
    elif any(re.search(r'BOMLR|BomCR|Bom\s?CR', c, re.I) for c in cites):
        court, stat = 'Bombay High Court', 'inferred'
    elif any(re.search(r'KANT|MYS', c, re.I) for c in cites):
        court, stat = 'High Court of Mysore (Karnataka)', 'inferred'
    elif any(re.search(r'SCR|SCC|SCALE', c, re.I) for c in cites):
        court, stat = 'Supreme Court of India', 'inferred'
    elif any(re.search(r'DLT|DEL', c, re.I) for c in cites):
        court, stat = 'Delhi High Court', 'inferred'
    elif any(re.search(r'MLJ|MAD', c, re.I) for c in cites):
        court, stat = 'Madras High Court', 'inferred'
    else:
        court, stat = None, 'not_found'
    m['court'] = _f(court, stat)

    # 7) Filing number — only explicit labels
    fn = re.search(r'((?:Filing|Registration)\s+No\.?\s*[\d/]+)', head, re.I)
    m['filing_number'] = _f(fn.group(1) if fn else None, 'extracted' if fn else 'not_found')

    # 8) Category + basics
    crim  = len(re.findall(r'accused|prosecution|FIR|NDPS|Narcotic|conviction|sentence|pancha', text, re.I))
    civil = len(re.findall(r'plaintiff|defendant|suit|decree|policy|insurance', text, re.I))
    m['case_category']  = 'criminal' if crim > civil else 'civil'
    m['document_type']  = _f('judgment' if re.search(r'\bJUDGMENT\b', head, re.I) else 'order', 'extracted')
    m['jurisdiction']   = _f('India', 'extracted')
    m['language']       = _f('English', 'extracted')
    m['word_count']     = len(text.split()) if text else 0
    return m
