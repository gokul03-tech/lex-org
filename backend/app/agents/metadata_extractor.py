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
    tail  = text[-1500:] if len(text) > 1500 else text
    lines = [l.strip() for l in head.split('\n') if l.strip()]
    m: dict[str, Any] = {}

    # 1) Parties via title-split (works for civil AND criminal).
    # Skip lines that are ONLY a separator word ("VERSUS", "vs.") so we never
    # capture the separator itself as a party name. Prefer a line where both
    # sides of the separator have real content.
    BAD_SEP_ONLY = re.compile(r'^(?:versus|vs\.?|v\.?)$', re.I)
    tl = None
    for i, l in enumerate(lines[:12]):
        # Multi-line SC style: "NAME\nVERSUS\nNAME" — stitch neighbours first
        if BAD_SEP_ONLY.match(l.strip()):
            if i > 0 and i + 1 < len(lines):
                stitch = f"{lines[i - 1]} versus {lines[i + 1]}"
                tl = stitch
                break
            continue
        if not re.search(r'\bvs\.?\b|\bv\.\b|\bversus\b', l, re.I):
            continue
        parts_try = re.split(r'\s+vs\.?\s+|\s+v\.\s+|\s+versus\s+', l, maxsplit=1, flags=re.I)
        if len(parts_try) == 2 and parts_try[0].strip() and parts_try[1].strip() \
                and not BAD_SEP_ONLY.match(parts_try[0].strip()) \
                and not BAD_SEP_ONLY.match(parts_try[1].strip()):
            tl = l
            break
        if tl is None:
            tl = l
    if tl:
        if BAD_SEP_ONLY.match(tl.strip()):
            tl_idx = next((i for i, l in enumerate(lines[:12]) if l.strip() == tl.strip()), -1)
            if tl_idx > 0 and tl_idx + 1 < len(lines):
                tl = f"{lines[tl_idx - 1]} versus {lines[tl_idx + 1]}"
        clean_tl = re.sub(r'\s+(?:\.\.\.\s*on|on)\s+\d{1,2}.*$', '', tl, flags=re.I)
        parts = re.split(r'\s+vs\.?\s+|\s+v\.\s+|\s+versus\s+', clean_tl, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            left, right = parts
            p_clean = fix_name(re.sub(r'\s*\.\.\.\s*(?:Appellant|Petitioner|Plaintiff|Applicant)s?\s*$', '', left, flags=re.I))
            r_clean = fix_name(re.sub(r'\s*\.\.\.\s*(?:Respondent|Defendant)s?\s*$', '', right, flags=re.I))
            # Reject separator-only or junk captures
            def _ok(n: str) -> bool:
                if not n or len(n) < 3:
                    return False
                if re.fullmatch(r'(?:versus|vs\.?|v\.?|and|or)', n, re.I):
                    return False
                if re.search(r'^(?:IN THE|SUPREME COURT|HIGH COURT)', n, re.I) and len(n) < 30:
                    return False
                return True
            if _ok(p_clean) and _ok(r_clean):
                m['case_title'] = _f(f"{p_clean} vs {r_clean}", 'extracted')
                m['petitioner'] = _f(p_clean, 'extracted')
                m['respondent'] = _f(r_clean, 'extracted')
            else:
                m['case_title'] = m['petitioner'] = m['respondent'] = _f(None, 'not_found')
        else:
            m['case_title'] = m['petitioner'] = m['respondent'] = _f(None, 'not_found')
    else:
        m['case_title'] = m['petitioner'] = m['respondent'] = _f(None, 'not_found')

    # 2) Decision date — prefer signature-block / tail date, then header.
    #    Accept ALL-CAPS months ("15 AUGUST 2024") as well as title-case.
    MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    DMY = rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH})\.?\s+(\d{{4}})'
    tail500 = text[-500:] if len(text) > 500 else text
    tail_date = re.search(
        rf'(?:decided\s+on|dated|pronounced|on|NEW DELHI)\s+{DMY}',
        tail, re.I) or re.search(DMY, tail500)
    dm = tail_date or \
         re.search(rf'(?:\.\.\.\s*on|on|decided\s+on|dated)\s+{DMY}', head, re.I) or \
         re.search(DMY, head)
    if dm:
        raw = dm.group(0)
        # Normalize to "D Month YYYY" (strip city / "NEW DELHI" / "decided on" prefixes)
        parts = re.search(DMY, raw, re.I)
        if parts:
            norm_d = f"{parts.group(1)} {parts.group(2)} {parts.group(3)}"
        else:
            norm_d = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', raw.replace(',', '').strip())
            norm_d = re.sub(
                r'^(?:NEW DELHI|NEW\s+DELHI|DECIDED\s+ON|DATED|PRONOUNCED|ON)\s+',
                '', norm_d, flags=re.I,
            ).strip()
        m['decision_date'] = _f(norm_d, 'extracted')
    else:
        m['decision_date'] = _f(None, 'not_found')

    # 3) Citations — only before "JUDGMENT" to avoid body precedent contamination
    head_pre_judgment = text.split("JUDGMENT")[0] if "JUDGMENT" in text else text[:2000]
    cites: list[str] = []
    for pat in (
        r'\(\d{4}\)\s?\d+\s?[A-Z]+\s?CR\s?\d+',
        r'\d{4}\s?Cri\s?LJ\s?\d+',
        r'AIR\s?\d{4}\s?[A-Z]{2,10}\s?\d+',
        r'\(\d{4}\)\s?\d+\s?[A-Z]+\s?\d+',
        r'\[\d{4}\]\s?\d+\s?SCR\s?\d+',
        r'\d{4}\s?SCC\s?\(\w+\)\s?\d+',
        r'ILR\s?\d{4}\s?[A-Z]+\s?\d+'
    ):
        cites += re.findall(pat, head_pre_judgment, re.I)
    cites = list(dict.fromkeys(c.strip() for c in cites))
    m['citation_numbers'] = _f(cites or None, 'extracted' if cites else 'not_found')

    # 4) Judges — line-start "NAME, J." over WHOLE text + full signature block
    judges: list[str] = []

    def _add_judge(raw: str) -> None:
        j_clean = raw
        # Strip titles repeatedly — "HON'BLE MR. JUSTICE X" leaves "MR. X" after one pass
        # if Mr\. is not followed by a word-boundary before a space.
        for _ in range(3):
            prev = j_clean
            j_clean = re.sub(
                r"(?:\bHon['’]?ble\s+|\bMr\.|\bMrs\.|\bMs\.|\bDr\.|\bJustice\s+"
                r"|\bCJI\b|\bJudge\b|\bJ\.|\bJ\b)",
                '', j_clean, flags=re.I,
            )
            j_clean = fix_name(j_clean)
            j_clean = re.sub(r',?\s*\b(?:J\.|CJI|Judge|J)\b\.?$', '', j_clean, flags=re.I).strip(' ,;.')
            if j_clean == prev:
                break
        if not j_clean or len(j_clean) < 3:
            return
        # Reject fragment initials like "D.Y." or bare "B.R"
        if re.fullmatch(r'(?:[A-Z]\.){1,4}', j_clean) or re.fullmatch(r'(?:[A-Z]\.?){1,4}', j_clean):
            return
        packed = re.sub(r'[\s.]+', '', j_clean).lower()
        if 'judgment' in packed or 'judgement' in packed:
            return
        if any(k in j_clean.lower() for k in ('judgment', 'judgement', 'court', 'order', 'state', 'versus', 'appellant', 'petitioner', "hon'ble", 'honble')):
            return
        # Reject pure initials without a surname (e.g. "D Y")
        tokens = [t for t in re.split(r'[\s.]+', j_clean) if t]
        if all(len(t) <= 2 for t in tokens):
            return
        # Reject spaced-letter fragments ("J U D G M E N T ...")
        if re.search(r'(?:\b[A-Z]\b\s*){3,}', j_clean):
            return
        # Deduplicate by packed key so "MR. D.Y. CHANDRACHUD" == "D.Y. CHANDRACHUD"
        existing = {re.sub(r'[\s.]+', '', j).lower() for j in judges}
        if packed not in existing:
            judges.append(j_clean)

    # Signature-block judges in brackets: "[D.Y. CHANDRACHUD]"
    sig = text[-2000:] if len(text) > 2000 else text
    for j in re.findall(r'\[([A-Z][A-Za-z.\s\'-]+)\]', sig):
        _add_judge(j)
    # Line-start "NAME, CJI" / "NAME, J." — do not span newlines inside the name
    for j in re.findall(r'(?:^|\n)\s*([A-Z][A-Za-z. \'\-]+?),\s*(?:J\.|CJI|J\b)', text):
        _add_judge(j)
    # Full bench line anywhere: "A, CJI; B, J.; C, J."
    for bm in re.finditer(r'(?:Bench|Coram|Before|Author)\s*:\s*([^\n]+)', text, re.I):
        for seg in re.split(r';|\band\b|&|,(?=\s*[A-Z])', bm.group(1)):
            _add_judge(seg)
    # Header: "HON'BLE MR. JUSTICE D.Y. CHANDRACHUD, CJI HON'BLE MR. JUSTICE B.R. GAVAI ..."
    for j in re.findall(r"JUSTICE\s+([A-Z][A-Za-z.\s'-]+?)(?:,\s*(?:CJI|J\b)|\s+HON'BLE|\s*$|\n)", head):
        _add_judge(j)
    # Dateline author line: "D.Y. CHANDRACHUD, CJI." — do not span newlines inside the name
    for j in re.findall(r'(?:^|\n)\s*([A-Z][A-Za-z. \'\-]+),\s*(?:CJI|J)\.', head):
        _add_judge(j)

    # Final packed-key dedupe: "MR. D.Y. CHANDRACHUD" == "D.Y. CHANDRACHUD"
    _seen: set[str] = set()
    _deduped: list[str] = []
    for j in judges:
        j = j.strip()
        if len(j) <= 2 or j.lower() in ['j.', 'cji', 'justice', 'honble', "hon'ble", 'bench', 'author', 'coram']:
            continue
        pk = re.sub(r'[\s.]+', '', j).lower()
        if pk in _seen:
            continue
        _seen.add(pk)
        _deduped.append(j)
    judges = _deduped
    m['presiding_judges'] = _f(judges or None, 'extracted' if judges else 'not_found')
    m['judges'] = m['presiding_judges']
    m['bench'] = _f(', '.join(judges) if judges else None, 'extracted' if judges else 'not_found')

    # 5) COURT MATTER = case / CR / FIR / Appeal number ONLY (never the court name!)
    cm = re.search(r'((?:C\.?R\.?|FIR|Special\s+Case|Criminal\s+Appeal|Civil\s+Appeal|Appeal|Writ\s+Petition|Suit)\s+No\.?\s*[\d/]+(?:\s+of\s+\d{4})?)', text, re.I)
    m['court_matter'] = _f(cm.group(1) if cm else None, 'extracted' if cm else 'not_found')

    # 6) COURT = explicit header beats inference
    court, stat = None, 'not_found'
    for line in lines[:4]:
        if 'COURT' in line.upper():
            cu = line.upper()
            if 'BOMBAY' in cu: court, stat = 'High Court of Judicature at Bombay', 'extracted'
            elif 'DELHI' in cu: court, stat = 'High Court of Delhi at New Delhi', 'extracted'
            elif 'SUPREME COURT' in cu: court, stat = 'Supreme Court of India', 'extracted'
            elif 'MADRAS' in cu: court, stat = 'High Court of Judicature at Madras', 'extracted'
            elif 'CALCUTTA' in cu: court, stat = 'High Court of Calcutta', 'extracted'
            elif 'KARNATAKA' in cu: court, stat = 'High Court of Karnataka', 'extracted'
            elif 'ALLAHABAD' in cu: court, stat = 'High Court of Judicature at Allahabad', 'extracted'
            else: court, stat = re.sub(r'^IN THE\s+', '', line, flags=re.I).strip().title(), 'extracted'
            break

    if not court:
        explicit_court = re.search(r'(Supreme\s+Court\s+of\s+India|Bombay\s+High\s+Court|High\s+Court\s+of\s+Bombay|Delhi\s+High\s+Court|High\s+Court\s+of\s+Delhi|High\s+Court\s+of\s+Karnataka|Karnataka\s+High\s+Court|High\s+Court\s+of\s+Mysore|Madras\s+High\s+Court|Calcutta\s+High\s+Court|Allahabad\s+High\s+Court)', head, re.I)
        if explicit_court:
            court, stat = explicit_court.group(1).strip(), 'extracted'
        elif any(re.search(r'BOMLR|BomCR|Bom\s?CR', c, re.I) for c in cites):
            court, stat = 'High Court of Judicature at Bombay', 'inferred'
        elif any(re.search(r'KANT|MYS', c) for c in cites):
            court, stat = 'High Court of Karnataka', 'inferred'
        elif any(re.search(r'SCR|SCC|SCALE', c) for c in cites):
            court, stat = 'Supreme Court of India', 'inferred'
        elif any(re.search(r'DLT|DEL', c, re.I) for c in cites):
            court, stat = 'High Court of Delhi at New Delhi', 'inferred'
        elif any(re.search(r'MLJ|MAD', c, re.I) for c in cites):
            court, stat = 'High Court of Judicature at Madras', 'inferred'
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
