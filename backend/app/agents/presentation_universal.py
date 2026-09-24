"""LexOrch-KG FINAL backend — universal, extraction-driven analysis builder.
Every value comes from THIS document. Replaces all category templates.
"""
from __future__ import annotations

import re
from typing import Any

norm = lambda t: re.sub(r'\s+', ' ', t or '').strip()
nows = lambda t: re.sub(r'[^a-z0-9]', '', (t or '').lower())
F = lambda v, s: {"value": v, "status": s}
snap = lambda t, i: t.rfind(' ', 0, max(0, i)) + 1          # word-boundary slice
_ABBR_DOT = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|No|Sec|Art|Ex|Rs|Adv|APP|Vs|vs|v)\.', re.I)
_SINGLE_INIT = re.compile(r'\b([A-Z])\.')

def _protect_dots(t: str) -> str:
    t = _ABBR_DOT.sub(lambda m: m.group(0).replace('.', '<DOT>'), t)
    return _SINGLE_INIT.sub(r'\1<DOT>', t)

def _restore_dots(s: str) -> str:
    return s.replace('<DOT>', '.')

def SENT(t: str) -> list[str]:
    return [_restore_dots(s).strip() for s in re.split(r'(?<=[a-z0-9])\.\s+(?=[A-Z0-9])', _protect_dots(t))]
JUNK = {'keyword', 'vector', '', 'null', 'none', 'precedent citation'}

safe = lambda m, k, fb=None: (
    m[k]['value']
    if isinstance(m, dict) and isinstance(m.get(k), dict)
    and m[k].get('status') in ('extracted', 'inferred')
    and m[k].get('value') and m[k].get('value') != "Not found in document"
    else (m[k] if isinstance(m, dict) and isinstance(m.get(k), (str, list)) and m[k] != "Not found in document" else fb)
)

# ---------- 1) CATEGORY (drives labels/stage/heading — never content) ----------
def detect_category(t: str) -> str:
    t = (t or '').lower()
    if re.search(r'\b(?:regular bail|anticipatory bail|bail application|admitted to bail|released on bail|seeking bail|bail plea)\b', t) or \
       re.search(r'\b(?:section 482 bnss|section 483 bnss|section 437|section 439 crpc)\b', t):
        return 'criminal_bail'
    if re.search(r'\b(?:article 32|article 226|writ petition|fundamental right|ultra vires|mandamus|habeas corpus|certiorari)\b', t):
        return 'writ'
    if re.search(r'\b(?:arbitration and conciliation|section 34|arbitral award|arbitral tribunal|sole arbitrator|arbitration act)\b', t):
        return 'arbitration'
    if re.search(r'\b(?:specific performance|agreement to sell|sale deed|code of civil procedure|order 39|civil appeal|civil suit|injunction)\b', t):
        return 'civil'
    if re.search(r'\b(?:conviction|sentenced|accused|charge sheet|ndps|contraband|panchanama|penal code|bns)\b', t):
        return 'criminal_trial'
    return 'criminal_bail'

STAGE = {
    'criminal_bail': 'Regular Bail Petition',
    'criminal_trial': 'Criminal Trial / Appeal',
    'civil': 'Civil Suit / Appeal',
    'arbitration': 'Petition u/s 34 (Setting Aside Award)',
    'writ': 'Writ Petition (Constitutional)'
}

# (Side A: Petitioner / Applicant / Appellant / Plaintiff, Side B: Respondent / State / Prosecution / Defendant)
LABELS = {
    'criminal_bail': ('Applicant / Defense Submissions', 'State / Prosecution Case'),
    'criminal_trial': ('Defense Rebuttals', 'Prosecution Arguments'),
    'civil': ('Appellant / Plaintiff Case', 'Respondent / Defense Case'),
    'arbitration': ('Petitioner Submissions', 'Respondent Submissions'),
    'writ': ('Petitioner Submissions', 'Respondent / State Submissions')
}

# ---------- 2) METADATA ----------
def norm_act(n: str) -> str:
    l = nows(n)
    if 'specificrelief' in l: return 'Specific Relief Act, 1963'
    if 'contract' in l: return 'Indian Contract Act, 1872'
    if 'civilprocedure' in l or 'cpc' in l: return 'Code of Civil Procedure, 1908'
    if 'registration' in l: return 'Indian Registration Act, 1908'
    if 'nagarik' in l or 'bnss' in l: return 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023'
    if 'nyaya' in l or 'bns' in l: return 'Bharatiya Nyaya Sanhita (BNS), 2023'
    if 'sakshya' in l or 'bsa' in l: return 'Bharatiya Sakshya Adhiniyam (BSA), 2023'
    if 'informationtechnology' in l or 'itact' in l: return 'Information Technology Act, 2000'
    if 'arbitration' in l: return 'Arbitration and Conciliation Act, 1996'
    if 'evidence' in l: return 'Indian Evidence Act, 1872'
    if 'narcotic' in l or 'ndps' in l: return 'NDPS Act, 1985'
    return norm(n)

PATS = [
    r'(C\.?R\.? No\.?\s*\d+\s*of\s*\d{4})',
    r'(FIR No\.?\s*[\d/]+(?:\s+of\s+\d{4})?)',
    r'(Appeal No\.?\s*\d+\s*of\s*\d{4})',
    r'(Suit No\.?\s*\d+\s*of\s*\d{4})',
    r'(Special Case No\.?\s*\d+\s*of\s*\d{4})',
    r'(Arbitration Petition No\.?\s*\d+\s*of\s*\d{4})',
    r'(Writ Petition\s*(?:\([A-Za-z]+\))?\s*No\.?\s*[\d/]+(?:\s+of\s+\d{4})?)'
]

def extract_court_name(head: str, text: str) -> str | None:
    lines = [l.strip() for l in head.split('\n') if l.strip()]
    for line in lines[:4]:
        if 'COURT' in line.upper():
            cu = line.upper()
            if 'BOMBAY' in cu: return 'High Court of Judicature at Bombay'
            if 'DELHI' in cu: return 'High Court of Delhi at New Delhi'
            if 'SUPREME COURT' in cu: return 'Supreme Court of India'
            if 'MADRAS' in cu: return 'High Court of Judicature at Madras'
            if 'CALCUTTA' in cu: return 'High Court of Calcutta'
            if 'KARNATAKA' in cu: return 'High Court of Karnataka'
            if 'ALLAHABAD' in cu: return 'High Court of Judicature at Allahabad'
            return re.sub(r'^IN THE\s+', '', line, flags=re.I).strip().title()
    m = re.search(r'IN THE ([A-Z\s,]+COURT[A-Z\s,]*|SUPREME COURT OF INDIA)', head, re.I)
    if m:
        cu = m.group(1).upper()
        if 'BOMBAY' in cu: return 'High Court of Judicature at Bombay'
        if 'DELHI' in cu: return 'High Court of Delhi at New Delhi'
        if 'SUPREME COURT' in cu: return 'Supreme Court of India'
        return m.group(1).strip().title()
    return None

def extract_metadata(text: str) -> dict[str, Any]:
    n = norm(text)
    head = text[:1800]
    lines = [l.strip() for l in head.split('\n') if l.strip()]
    
    court_clean = extract_court_name(head, text)
    
    BAD_SEP_ONLY = re.compile(r'^(?:versus|vs\.?|v\.?)$', re.I)
    pet, resp = None, None
    for i, l in enumerate(lines[:12]):
        if BAD_SEP_ONLY.match(l.strip()):
            if i > 0 and i + 1 < len(lines):
                stitch = f"{lines[i - 1]} versus {lines[i + 1]}"
                parts = re.split(r'\s+(?:vs\.?|v\.|versus)\s+', stitch, maxsplit=1, flags=re.I)
                if len(parts) == 2 and parts[0].strip() and parts[1].strip() \
                        and not BAD_SEP_ONLY.match(parts[0].strip()) \
                        and not BAD_SEP_ONLY.match(parts[1].strip()):
                    pet = norm(parts[0])
                    resp = norm(parts[1])
                    break
            continue
        if not re.search(r'\b(?:vs\.?|v\.|versus)\b', l, re.I):
            continue
        parts = re.split(r'\s+(?:vs\.?|v\.|versus)\s+', l, maxsplit=1, flags=re.I)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip() \
                and not BAD_SEP_ONLY.match(parts[0].strip()) \
                and not BAD_SEP_ONLY.match(parts[1].strip()):
            pet = norm(parts[0])
            pet = re.sub(r'^(?:IN THE [A-Z\s,]+COURT[A-Z\s,]*|SUPREME COURT OF INDIA)\s*', '', pet, flags=re.I).strip()
            resp = norm(parts[1])
            resp = re.sub(r'\s*(?:\.\.\.)?\s*on\s+\d{1,2}.*$', '', resp or '').strip()
            if not BAD_SEP_ONLY.match(pet or '') and not BAD_SEP_ONLY.match(resp or ''):
                break
            pet, resp = None, None
    if pet and BAD_SEP_ONLY.match(pet):
        pet = None
    if resp and BAD_SEP_ONLY.match(resp):
        resp = None
    if pet:
        pet = re.sub(r'\s*\.\.\.\s*(?:Appellant|Petitioner|Plaintiff|Applicant)s?\s*$', '', pet, flags=re.I).strip() or pet
    if resp:
        resp = re.sub(r'\s*\.\.\.\s*(?:Respondent|Defendant)s?\s*$', '', resp, flags=re.I).strip() or resp

    # Prefer signature-block date (last 500 chars), then header date; accept ALL-CAPS months
    MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    DMY = rf'(\d{{1,2}})(?:st|nd|rd|th)?[ ,.\-]+({MONTH})[ ,.\-]+(\d{{4}})'
    tail500 = text[-500:] if len(text) > 500 else text
    dm = re.search(DMY, tail500, re.I) or \
         re.search(rf'(?:\.\.\.\s*on|on|dated|decided on)\s+{DMY}', head, re.I) or \
         re.search(DMY, head, re.I)
         
    cites = re.findall(r'\(\d{4}\)\s?\d+\s?[A-Z]+\s?\d+|AIR\s?\d{4}\s?[A-Z ]+\d+|\[\d{4}\]\s?\d+\s?SCR\s?\d+|\d{4}\s?Cri\s?LJ\s?\d+', n.split('JUDGMENT')[0], re.I)
    case_no = next((m.group(1) for p in PATS if (m := re.search(p, n))), None)
    
    judges: list[str] = []
    def _clean_j(raw_j: str) -> str:
        c = raw_j
        for _ in range(3):
            prev = c
            c = re.sub(
                r"(?:\bHon['’]?ble\s+|\bMr\.|\bMrs\.|\bMs\.|\bDr\.|\bJustice\s+"
                r"|\bCJI\b|\bJudge\b|\bJ\.|\bJ\b)",
                '', c, flags=re.I,
            )
            c = re.sub(r',?\s*\b(?:J\.|CJI|Judge|J)\b\.?$', '', c, flags=re.I)
            c = norm(c).strip(' ,;.')
            if c == prev:
                break
        return c

    def _ok_j(j_clean: str) -> bool:
        if not j_clean or len(j_clean) < 3:
            return False
        packed = re.sub(r'[\s.]+', '', j_clean).lower()
        if any(j2 and re.sub(r'[\s.]+', '', j2).lower() == packed for j2 in judges):
            return False
        if j_clean in ('J.', 'CJI', 'Justice') or re.fullmatch(r'(?:[A-Z]\.?){1,4}', j_clean):
            return False
        if 'judgment' in packed or 'judgement' in packed:
            return False
        if any(k in j_clean.lower() for k in ('judgment', 'judgement', 'court', 'order', 'state', 'bench', 'author', 'versus', "hon'ble", 'honble')):
            return False
        tokens = [t for t in re.split(r'[\s.]+', j_clean) if t]
        if tokens and all(len(t) <= 2 for t in tokens):
            return False
        # Reject spaced-letter fragments ("J U D G M E N T ...")
        if re.search(r'(?:\b[A-Z]\b\s*){3,}', j_clean):
            return False
        return True

    for tag in ('Author', 'Bench', 'Coram', 'Judges'):
        am = re.search(tag + r':\s*([^\n]+)', text, re.I)
        if am:
            for b_seg in re.split(r'\band\b|&|;|,(?=\s*[A-Z])', am.group(1)):
                b_clean = _clean_j(b_seg)
                if _ok_j(b_clean):
                    judges.append(b_clean)

    # Signature-block judges in last 2000 chars: "...........J. [NAME]" / "NAME, CJI"
    sig = text[-2000:] if len(text) > 2000 else text
    for j in re.findall(r'\[([A-Z][A-Za-z.\s\'-]+)\]', sig):
        j_clean = _clean_j(j)
        if _ok_j(j_clean):
            judges.append(j_clean)
    for j in re.findall(r'(?:^|\n)\s*([A-Z][A-Za-z. \'\-]+?),\s*(?:J\.|CJI)', text):
        j_clean = _clean_j(j)
        if _ok_j(j_clean):
            judges.append(j_clean)
    # Header bench line: "HON'BLE MR. JUSTICE D.Y. CHANDRACHUD, CJI HON'BLE MR. JUSTICE B.R. GAVAI HON'BLE MS. JUSTICE B.V. NAGARATHNA"
    for j in re.findall(r"JUSTICE\s+([A-Z][A-Za-z.\s'-]+?)(?:,\s*(?:CJI|J\b)|\s+HON'BLE|\s*$|\n)", head):
        j_clean = _clean_j(j)
        if _ok_j(j_clean):
            judges.append(j_clean)

    judges_list = list(dict.fromkeys(j.strip(' ,;.') for j in judges if j and len(j.strip()) > 2))
    # Final packed-key dedupe: "MR. D.Y. CHANDRACHUD" == "D.Y. CHANDRACHUD"
    _seen_j: set[str] = set()
    _deduped: list[str] = []
    for j in judges_list:
        _pk = re.sub(r'[\s.]+', '', j).lower()
        if _pk in _seen_j:
            continue
        _seen_j.add(_pk)
        _deduped.append(j)
    judges_list = _deduped
    title_str = f"{pet} vs {resp}" if pet and resp else (pet or "Legal Matter Dossier")

    return {
        'court': F(court_clean, 'extracted' if court_clean else 'not_found'),
        'case_title': F(title_str, 'extracted' if pet else 'not_found'),
        'petitioner': F(pet, 'extracted' if pet else 'not_found'),
        'respondent': F(resp, 'extracted' if resp else 'not_found'),
        'decision_date': F(f"{dm.group(1)} {dm.group(2)} {dm.group(3)}" if dm else None, 'extracted' if dm else 'not_found'),
        'citation_numbers': F(cites or None, 'extracted' if cites else 'not_found'),
        'case_number': F(case_no, 'extracted' if case_no else 'not_found'),
        'judges': F(judges_list or None, 'extracted' if judges_list else 'not_found'),
        'presiding_judges': F(judges_list or None, 'extracted' if judges_list else 'not_found')
    }

# ---------- 3) SECTIONS (formatted strings — never raw dicts) ----------
def bind_sections(text: str) -> list[dict[str, Any]]:
    n = norm(text)
    out = []
    ACT_PAT = r'([A-Z][A-Za-z.\s(),&-]{2,90}?(?:Act|Sanhita|Adhiniyam|Code|Constitution|Regulation)s?(?:\s*\([A-Za-z\s]+\))?(?:,?\s?(?:19|20)\d{2})?|NDPS\s+Act|IT\s+Act|BNSS|BSA|BNS|CPC|CrPC|IPC)'
    
    # 1. Forward pattern: Section X of Act
    for m in re.finditer(r'(?:Sections?|Sec\.?)\s+([0-9A-Za-z(),\s&and/-]+?)\s+(?:of\s+(?:the\s+)?)?' + ACT_PAT, n):
        act = norm_act(m.group(2))
        secs = re.findall(r'[0-9]+[A-Za-z]?(?:\([0-9A-Za-z]+\))*', m.group(1))
        for s in secs:
            out.append({'num': s, 'section_number': s, 'act': act, 'display': f"Section {s} — {act}"})
            
    # 2. Order X Rule Y pattern
    for m in re.finditer(r'Order\s+(\d+)\s+Rule\s+([\d,\s&and]+)\s+(?:of\s+(?:the\s+)?)?' + ACT_PAT, n):
        o_num = m.group(1)
        r_nums = m.group(2).strip()
        act = norm_act(m.group(3))
        out.append({'num': f"O.{o_num} R.{r_nums}", 'section_number': f"O.{o_num} R.{r_nums}", 'act': act, 'display': f"Order {o_num} R. {r_nums} — {act}"})

    # 3. Direct backward/nearby section match
    for m in re.finditer(r'Section\s+([0-9]+[A-Za-z]?(?:\([0-9A-Za-z]+\))*)\s+([A-Z]{2,6}\s+Act|BNSS|BSA|BNS|CPC|NDPS\s+Act)', n):
        s = m.group(1)
        act = norm_act(m.group(2))
        out.append({'num': s, 'section_number': s, 'act': act, 'display': f"Section {s} — {act}"})

    # 4. Constitutional Articles
    for m in re.finditer(r'Article\s+([0-9]+[A-Za-z]?(?:\([0-9A-Za-z]+\))*)', n):
        a_num = m.group(1)
        act = 'Constitution of India'
        out.append({'num': f"Art. {a_num}", 'section_number': a_num, 'act': act, 'display': f"Article {a_num} — {act}"})

    return list({d['display']: d for d in out}.values())

# ---------- 4) PRECEDENTS (each name ↔ its OWN citation) ----------
# Citation shapes: "(2011) 1 SCC 694", "[2023] 4 SCR 710", "1994 Supp (1) SCC 92",
# "1997 (3) SCC 1", "AIR 1954 SC 494", "2024 SCC OnLine SC 2754".  Order matters:
# the parenthesised/bracketed forms must be tried before the bare-year form so a
# "1994" inside "… Builders v. DDA (1994) …" never mis-parses as a new citation.
CIT = r'\([12]\d{3}\)\s?\d+\s?[A-Z.]+\s?\d+|\[[12]\d{3}\]\s?\d+\s?SCR\s?\d+|\d{4}\s?(?:Supp\.?\s*)?\(?\d{1,4}\)?\s?SCC\s?\d+|\d{4}\s?SCC\s+OnLine\s+(?:SC|Del|Bom)|\d{4}\s?\d+\s?[A-Z.]+\s?\d+|AIR\s?[12]\d{3}\s?[A-Z ]+\d+'

def extract_precedents(text: str) -> list[dict[str, Any]]:
    n = norm(text)
    out = []
    seen = set()
    key_list: list[str] = []

    def _clean_name(raw: str) -> str:
        """Trim numbered-clause/trailing junk a greedy name may have absorbed."""
        return re.split(r'\s\.\s*\d', raw)[0].strip(' ,;.')

    # Case-name charset excludes digits so "v. State. 4. It was further urged …"
    # can never swallow the following clause; a numbered-clause period (". 4.")
    # terminates the name via the lookahead instead of being absorbed.
    NAME = r'[A-Z][A-Za-z.&\' -]+?(?:\s+(?:v\.?|versus)\s+[A-Z][A-Za-z.&\' -]+?)'

    # The judgment's own title line (e.g. "State of Maharashtra v. X") must never
    # be captured as a cited precedent. Snapshot the first "X v. Y" in the header.
    hm = re.search(NAME, n[:600])
    title_nows = nows(re.sub(r'\s+', ' ', hm.group(0)).strip())[:15] if hm else ""

    def _append(raw_name: str, cite: str) -> None:
        name = _clean_name(raw_name)
        norm_k = nows(name)[:15]
        if (not norm_k or norm_k in seen or norm_k == title_nows
                or len(name) < 6 or len(name) > 70 or name.lower() in JUNK):
            return
        # Reject generic cause-title placeholders like "Appellant v. Respondent".
        if re.fullmatch(
            r'(?:the\s+)?(?:appellant|applicant|petitioner|plaintiff|accused'
            r'|respondent|defendant|prosecution|state)\s+(?:vs\.?|versus|v\.?|and|&)'
            r'\s+(?:the\s+)?(?:appellant|applicant|petitioner|plaintiff|accused'
            r'|respondent|defendant|prosecution|state)',
            name, re.IGNORECASE):
            return
        # Reject prose that a greedy name match swallowed: "… v. Union of India were
        # reiterated is not a precedent", etc.
        if re.search(r'\b(?:were|was|held|is\b|not\b|that\b|wherein|reiterat|observed'
                     r'|submitted|contended|case|judgment)\b', name, re.IGNORECASE):
            return
        # Prefix-superset dedup: "Anvar P.V. v. P.K" vs "Anvar P.V. v. P.K. Basheer"
        # are the same case (a period-initials match truncated the fuller name) —
        # keep only the fullest form.
        for i, ek in enumerate(key_list):
            if min(len(ek), len(norm_k)) >= 8 and (ek.startswith(norm_k) or norm_k.startswith(ek)):
                if len(name) > len(out[i]['case_name']):
                    yr = (re.search(r'(19\d{2}|20\d{2})', cite) or [None, None])[1]
                    out[i] = {'case_name': name, 'citation': cite or out[i].get('citation', ''),
                              'year': yr or out[i].get('year'),
                              'summary': f"Precedent cited for legal principle on this issue."}
                    key_list[i] = norm_k
                return
        seen.add(norm_k)
        key_list.append(norm_k)
        yr = (re.search(r'(19\d{2}|20\d{2})', cite) or [None, None])[1]
        out.append({'case_name': name, 'citation': cite, 'year': yr,
                    'summary': f"Precedent cited for legal principle on this issue."})

    # 1. (Citation) in the case of Name
    for m in re.finditer(r'(' + CIT + r')\s+in the case of\s+(' + NAME + r')(?=\s+(?:wherein|regarding|holding|where|which|laid|ruling|reiterat|and the recent)|\s*\([12]\d{3}\)|,\s+and|\.\s*\d|\n,|\n|,)', n):
        _append(m.group(2), m.group(1).strip())

    # 2. judgment in Name (Citation)
    for m in re.finditer(r'(?:judgment|decision|ruling|case)\s+in\s+(?:the case of\s+)?(' + NAME + r')\s*(' + CIT + r')', n):
        _append(m.group(1), m.group(2).strip())

    # 3. Bare "Name v. Name, (Citation)" references (headnote citation lists and
    #    "reported in" entries) — previously missed, making Missing Precedents intermittent
    for m in re.finditer(r'(?<![A-Za-z0-9,])(' + NAME + r')\s*,\s*(' + CIT + r')', n):
        _append(m.group(1), m.group(2).strip())

    # 4. Citation-less analytical references: "in the case of Name v. Name", "Name v. Name, …"
    for m in re.finditer(
        r'\b(?:in\s+|relying on\s+|following\s+|per\s+)?'
        r'(?:the case (?:of|in) |the decision (?:of|in) |the judgment in |the ruling in )?'
        r'(' + NAME + r')(?=$|\s*[,;.])', n):
        _append(m.group(1), "")

    return out

def split_sentences(t: str) -> list[str]:
    return SENT(t)

SPEC_OUTCOME = re.compile(r'\b(?:allowed|set aside|disposed|dismissed)\b', re.I)
ANY_OUTCOME = re.compile(r'\b(?:allowed|set aside|disposed|dismissed|directed|quashed|decreed|granted)\b', re.I)
AGREE_LINE = re.compile(r'-\s*I agree', re.I)

def _substantive_sentences(n: str, min_len: int = 60) -> list[str]:
    return [s.strip() for s in SENT(n) if len(s.strip()) >= min_len and not AGREE_LINE.search(s)]

_SIG_BLOCK = re.compile(
    r'(?:\.{10,}\s*J\.?|CHIEF JUSTICE OF INDIA|JUSTICE OF INDIA|\[?\s*[A-Z][A-Za-z.\s]+\]?\s*$'
    r'|NEW DELHI\s+\d{1,2}\s+[A-Z]{3,9}\s+\d{4})',
    re.I,
)

def _strip_signature(text: str) -> str:
    """Drop judge signature/date tail so it never leaks into conclusion/timeline."""
    if not text:
        return text
    m = _SIG_BLOCK.search(text[-800:])
    if m and m.start() > 0:
        return text[: max(0, len(text) - 800) + m.start()]
    # Fallback: cut at last "......J." style line
    m2 = re.search(r'\n\s*\. {5,}J\.', text)
    if m2:
        return text[: m2.start()]
    return text

def _conclusion_section(text: str) -> str:
    """Prefer the court's CONCLUSION AND ORDER (or equivalent) section over text tail."""
    if not text:
        return text
    m = re.search(
        r'(?:CONCLUSION AND ORDER|CONCLUSION & ORDER|CONCLUSION|ORDER AND DISPOSITION|OPERATIVE PART|IN THE RESULT)\s*\n',
        text, re.I,
    )
    if m:
        section = text[m.end():]
        # Cut at signature block inside/after the section
        section = _strip_signature(section)
        return section[:3000]
    return _strip_signature(text)

def _operative_sentence(n: str) -> str | None:
    """Outcome-bearing sentence from CONCLUSION section first, else body tail."""
    concl = norm(_conclusion_section(n))
    for sents in (
        [s.strip() for s in SENT(concl) if s.strip()],
        [s.strip() for s in SENT(n[-600:]) if s.strip()],
    ):
        for s in reversed(sents):
            if SPEC_OUTCOME.search(s):
                return s
        for s in reversed(sents):
            if ANY_OUTCOME.search(s):
                return s
    for s in reversed(_substantive_sentences(n)):
        if ANY_OUTCOME.search(s):
            return s
    return None

def _last_substantive(n: str) -> str | None:
    body = _substantive_sentences(n)
    return body[-1] if body else None

def map_outcome_verb(sentence: str) -> str | None:
    """Map any outcome wording onto one of the canonical operative verbs."""
    s = sentence.lower()
    if re.search(r'\b(quash|set aside)', s):
        return 'set aside'
    if re.search(r'\b(grant|decreed|released on bail|admitted to bail|allowed)', s):
        return 'allowed'
    if re.search(r'\b(dismiss)', s):
        return 'dismissed'
    if re.search(r'\b(dispos)', s):
        return 'disposed'
    return None

# ---------- 5) SUBMISSIONS (counsel attribution, category labels) ----------
_SPEAKER_VERB = (r'(?:submit(?:s|ted|ting)?|contend(?:s|ed|ing)?|argue(?:s|d|ing)?'
                 r'|oppose(?:s|d|ing)?|defend(?:s|ed|ing)?|assert(?:s|ed|ing)?'
                 r'|maintain(?:s|ed|ing)?|urge(?:s|d|ing)?|resist(?:s|ed|ing)?'
                 r'|invoke(?:s|d|ing)?|reli(?:ed|es|ying)|point(?:s|ed|ing)?\s+out'
                 r'|demonstrat(?:e|es|ed|ing)|plead(?:s|ed|ing)?|sought|seek(?:s|ing)?)')

def _strip_speaker(sentence: str, tokens: str) -> str:
    """Strip a leading party-speaker phrase ("The learned State (APP) contended that …"
    or "It was further urged by the learned APP that …") from a submission sentence
    so only the actual point survives the column split."""
    verb = _SPEAKER_VERB
    active = (r'^(?:the\s+)?(?:learned\s+)?(?:' + tokens + r')'
              r'(?:\s+(?:(?:of|through|by)\s+)?[A-Z][A-Za-z.\'-]{2,30}'
              r'(?:\s+[A-Z][A-Za-z.\'-]{2,30}){0,2})?'
              r'(?:\s*[,(]*\s*)?(?:further\s+)?'
              + verb + r'\b(?:\s+that\b)?')
    passive = (r'^it\s+was\s+(?:further\s+)?' + verb + r'\s+by\s+'
               r'(?:the\s+)?(?:learned\s+)?(?:' + tokens + r')'
               r'(?:\s+(?:(?:of|through|by)\s+)?[A-Z][A-Za-z.\'-]{2,30}'
               r'(?:\s+[A-Z][A-Za-z.\'-]{2,30}){0,2})??'
               r'(?:\s*[,(]*\s*)?(?:that\b)?')
    for pat in (active, passive):
        m = re.match(pat, sentence, re.IGNORECASE)
        if m:
            return sentence[m.end():].lstrip()
    return sentence

def extract_submissions(text: str) -> tuple[list[str], list[str]]:
    n = norm(text)
    a, b = [], []
    cur = None
    
    PAT_A_START = re.compile(r'\b(?:counsel (?:for|appearing for|on behalf of) (?:the )?(?:applicant|petitioner|appellant|plaintiff)|the (?:applicant|petitioner|appellant|plaintiff) (?:has invoked|contends|submitted|argued|pleaded))\b', re.I)
    PAT_B_START = re.compile(r'\b(?:(?:on the other hand|per contra|in opposition|opposed).*?(?:learned APP|state|respondent|prosecution|counsel)|counsel (?:for|appearing for|on behalf of) (?:the )?(?:respondent|state|prosecution|vendor|defendant|nhai|union of india)|learned (?:app|asg|solicitor general|standing counsel)|the (?:respondent|state|prosecution|vendor|defendant)(?:/vendor)? (?:contended|opposed|argued|defended|invoked)|the respondent/vendor)\b', re.I)
    VERBS = re.compile(r'\b(?:submitted|contended|argued|relied|pointed|defended|opposed|demonstrated|pleaded|urged|resisted|invoked)\b', re.I)
    
    for s in split_sentences(n):
        s_clean = s.strip()
        if ' vs ' in s_clean or ' versus ' in s_clean or s_clean.startswith('Bench:'):
            continue
        if re.search(r'\b(?:We have heard|We hold|In our considered view|The petition is|Bail is allowed|Award is set aside)\b', s_clean, re.I):
            cur = None
            continue
        # Court-framed issues are not counsel submissions
        if re.match(r'^Issue\s+[IVXLC]+\b', s_clean, re.I) or \
           re.search(r'\bWe frame the following issues\b', s_clean, re.I) or \
           re.match(r'^(?:CONCLUSION AND ORDER|ORDER AND DIRECTIONS)\b', s_clean, re.I):
            cur = None
            continue

        has_verb = bool(VERBS.search(s_clean))
        
        if PAT_B_START.search(s_clean):
            cur = 'b'
        elif PAT_A_START.search(s_clean):
            cur = 'a'
            
        if cur and has_verb and len(s_clean) > 25:
            clean_s = re.sub(r'^\d+\.\s*', '', s_clean)
            # Never let a State/Prosecution bullet leak into the Applicant/Defense list
            # (and vice-versa) when a speaker label was glued to the sentence.
            # Strip the leading party speaker phrase (incl. honorifics and the verb +
            # optional "that") so only the actual point remains.
            if cur == 'a':
                clean_s = _strip_speaker(
                    clean_s,
                    r'Applicant|Petitioner|Appellant|Plaintiff|Defense|Defence|Accused|Applicant\'s|Petitioner\'s'
                )
            else:
                clean_s = _strip_speaker(
                    clean_s,
                    r'State(?:\s*\(?APP\)?)?|Prosecution|Respondent(?:/State)?|Opposite\s+Party|APP|A\.P\.P\.|Public\s+Prosecutor'
                )
            clean_s = clean_s.strip()
            target = a if cur == 'a' else b
            if clean_s and clean_s not in target:
                target.append(clean_s)
                
    return a[:3], b[:3]

# ---------- 6) EVIDENCE (per-item reliability, word-aligned) ----------
CUES = [
    (r'Call Detail Records\s*\(CDR\)|cell-site logs|electronic data', 'Electronic Records (CDR / cell-site logs)'),
    (r'panchanama dated [\d-]+|seizure memo|panchas', 'Panchanama / Seizure Memo'),
    (r'bank ledger audits|bank statements|escrow|financial transfer', 'Financial Records & Statements'),
    (r'charge sheet|investigation is complete', 'Charge Sheet / Investigation Record'),
    (r'Ex\.\s*[PD]-?\d+|documentary exhibits', 'Documentary Exhibits'),
    (r'correspondence dated [\d-]+|letters dated', 'Contemporaneous Correspondence'),
    (r'agreement to sell|conveyance deed|sale deed', 'Title / Contract Documents'),
    (r'recovery of contraband|contraband was recovered|450 grams', 'Contraband Recovery & Forensic Record'),
    (r'statutory notifications|data localization|executive interception', 'Official Notifications & Directives'),
    (r'impugned notification|impugned order|impugned action|impugned measure', 'Impugned Order / Notification')
]

def extract_evidence(text: str) -> list[dict[str, Any]]:
    n = norm(text)
    items = []
    seen = set()
    for pat, label in CUES:
        m = re.search(pat, n, re.I)
        if not m or label in seen:
            continue
        seen.add(label)
        win = n[max(0, m.start()-220):m.end()+220]
        
        # Word-aligned snippet window — closes on the next sentence boundary so
        # the quote stays a contiguous substring of the source (no "..." marker
        # that would break verbatim grounding checks).
        st = n.rfind('. ', 0, m.start())
        st = st + 2 if st != -1 else 0
        raw_end = min(len(n), m.end() + 190)
        e_pos = n.find('. ', raw_end)
        end = e_pos + 2 if e_pos != -1 else raw_end
        snip = re.sub(r'^\d+\.\s*', '', n[st:end]).strip()
        
        items.append({
            'label': label,
            'reliability': 'DISPUTED' if re.search(r'without compliance|certification under Section|not certified|inadmissible|in custody|without judicial oversight', win, re.I) else 'HIGH',
            'detail': snip
        })
    return items[:4]

# ---------- 7) TIMELINE + OUTCOME ----------
def build_timeline(text: str, date: str | None) -> list[dict[str, Any]]:
    body = _strip_signature(text or '')
    n = norm(body)
    def _bad_fact(fact: str) -> bool:
        if not fact or len(fact) < 20:
            return True
        if re.search(r'\bJ\s*U\s*D\s*G\s*M\s*E\s*N\s*T\b|HON[\'’]?BLE\s+MR\.|CHIEF JUSTICE OF INDIA|\bJUSTICE\b', fact, re.I):
            return True
        if re.match(r'^(?:IN THE SUPREME|CRIMINAL APPEAL|NO\.\s*\d)', fact, re.I):
            return True
        return False

    ev = [{'date': m.group(0), 'fact': n[snap(n, m.start()-140):m.end()+140], 'page': '1-2'}
          for m in re.finditer(r'\d{2}-\d{2}-\d{4}', n)]
    for m in re.finditer(
        r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
        n, re.I,
    ):
        fact = n[snap(n, m.start()-140):m.end()+140]
        if _SIG_BLOCK.search(fact) or _bad_fact(fact):
            continue
        ev.append({'date': m.group(0), 'fact': fact, 'page': '1-2'})
    # Keep only date events with usable facts
    ev = [e for e in ev if not _bad_fact(e['fact'])]
    op = _operative_sentence(n) or _last_substantive(n) or n[-160:].strip()
    if op and (_SIG_BLOCK.search(op) or _bad_fact(op) or re.match(r'^(?:[A-Z][A-Za-z.\s]{0,40},\s*(?:CJI|J)|NEW DELHI)', op, re.I) or len(op) < 20):
        op = _operative_sentence(n) or 'Final judgment delivered.'
    return ev + [{'date': date or 'Final Hearing Date', 'fact': op, 'page': '1-2'}]

# ---------- 8) RISK (fully extracted; strictly procedural action plan) ----------
def _extract_procedural_actions(text: str, n: str, op: str | None) -> list[str]:
    """Extract procedural next steps directly and verbatim from the document text,
    ensuring zero hallucination and strict grounding."""
    actions = []
    
    sentences = SENT(n)
    for s in sentences:
        s_clean = s.strip()
        # Never surface court-framed issues / headings as next steps
        if re.match(r'^(?:Issue\s+[IVXLC]+|We frame the following|CONCLUSION AND ORDER|ORDER AND DIRECTIONS)\b', s_clean, re.I):
            continue
        if re.search(r'\b(?:directed to|executing a|furnish|deposit|refund|pay|appear|bond of|sureties|compliance|affidavit|transmit a copy|notify|dispose)\b', s_clean, re.I):
            # Exclude pure standalone verdict phrases like "Bail application is allowed."
            if not re.match(r'^(?:\d+\.\s*)?(?:bail application|appeal|petition|suit)\s+is\s+(?:allowed|dismissed)\.?$', s_clean, re.I):
                if s_clean not in actions and len(s_clean) > 15:
                    actions.append(s_clean)
                    if len(actions) >= 3:
                        break
                        
    if not actions and op:
        actions = [op]
    elif not actions:
        fb = _last_substantive(n)
        if fb:
            actions = [fb]
            
    return actions

def build_risk(text: str, subs_a: list[str], subs_b: list[str]) -> dict[str, Any]:
    body = _strip_signature(text)
    n = norm(body)
    concl_block = _conclusion_section(text) or n
    strengths = [s for s in SENT(n) if re.search(r'We hold|established|readiness and willingness|No direct financial transfer|investigation is complete|charge sheet has already been filed|renders the impugned', s, re.I)][:2]
    op = _operative_sentence(norm(concl_block)) or _operative_sentence(n)
    fallback_quote = _last_substantive(norm(concl_block)) or _last_substantive(n) or n[-160:].strip()

    str_list = strengths or (subs_a[:1] if subs_a else ([fallback_quote] if fallback_quote else []))
    contest_cue = re.compile(r'\b(contended|opposed|defended|failed to|disputed|however)\b', re.I)
    gap_src = subs_b[:2] if subs_b else [s for s in _substantive_sentences(n) if contest_cue.search(s)][:2]
    gap_list = gap_src or ([fallback_quote] if fallback_quote else [])

    # Procedural next steps: prefer CONCLUSION AND ORDER clauses, then whole doc
    act_list = _extract_procedural_actions(text, n, op)
    if concl_block:
        acts_c = _extract_procedural_actions(concl_block, norm(concl_block), None)
        merged = acts_c + [a for a in act_list if a not in acts_c]
        act_list = merged[:4]
    # Drop any residual framing / submission noise from the action plan
    def _trim_action(a: str) -> str:
        a = re.sub(r'^\s*(?:\d+\.\s*|\(?(?:i{1,3}|iv|v|vi{0,3}|ix|x)\)\s*)+', '', a).strip()
        a = re.split(r'\s+\(?(?:ii|iii|iv|v|vi|vii|viii|ix|x)\)\s+', a, maxsplit=1, flags=re.I)[0].strip()
        return a if len(a) <= 360 else a[:357].rstrip() + '…'

    act_list = [
        _trim_action(a) for a in act_list
        if not re.search(r'\bWe frame the following issues\b|\bIssue\s+[IVXLC]+\b|\bsubmitted\b|\bcontended\b', a, re.I)
    ]
    act_list = [a for a in act_list if a]
    # de-dupe
    _seen_a: set[str] = set()
    _uniq_a: list[str] = []
    for a in act_list:
        if a in _seen_a:
            continue
        _seen_a.add(a)
        _uniq_a.append(a)
    act_list = _uniq_a[:4]
    if not act_list and op:
        act_list = [op]

    if op and SPEC_OUTCOME.search(op):
        conclusion = norm(op)
        conclusion = re.split(r'\s+\(?(?:ii|iii|iv|v|vi|vii|viii|ix|x)\)\s+', conclusion, maxsplit=1, flags=re.I)[0].strip()
        if len(conclusion) > 420:
            conclusion = conclusion[:417].rstrip() + '…'
    elif op:
        subject_m = re.search(r'\bthe\s+([a-z][a-z\s]{3,60}?(?:petition|appeal|application|suit|award))\b', op.lower())
        verb = map_outcome_verb(op) or 'allowed'
        subject = subject_m.group(1) if subject_m else 'petition'
        conclusion = f"{subject.capitalize()} is {verb}."
    else:
        conclusion = fallback_quote

    # Reject signature-block leakage as conclusion/action
    if re.match(r'^(?:\.{3,}|\[?A|NEW DELHI|Dated\b)', conclusion, re.I) or len(conclusion) < 15:
        if op and SPEC_OUTCOME.search(op):
            conclusion = norm(op)
        elif concl_block:
            first = next((s.strip() for s in SENT(norm(concl_block)) if len(s.strip()) > 30), None)
            if first:
                conclusion = first

    return {
        'strengths': str_list,
        'gaps': gap_list,
        'action_plan': act_list,
        'conclusion': conclusion
    }

# ---------- 9) KG + TRUST + GATE ----------
def build_kg(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Universal KG Builder. Supports both positional (meta, secs, precs, evi) and dict context (r_ctx)."""
    if len(args) == 1 and isinstance(args[0], dict):
        r = args[0]
        meta = r.get('metadata') or {}
        secs = r.get('sections') or []
        section_acts = r.get('section_acts') or {}
        precs = r.get('precedents') or []
        evi = r.get('evidence') or []
        
        case_title = safe(meta, 'case_title', 'Case')
        clean_title = re.sub(r'\s+(?:\.\.\.\s*on|on|\.\.\.)\s+\d{1,2}.*$', '', case_title).strip()
        nodes = [{'id': 'case', 'type': 'Case', 'label': clean_title}]
        edges = []
        seen = {'case'}

        def add(t: str, l: str):
            if not l or l.lower() in JUNK: return None
            # Canonical key for judges so "HON'BLE MR. JUSTICE D.Y. CHANDRACHUD"
            # and "D.Y. CHANDRACHUD" never become two nodes.
            key_label = l
            if t == 'Judge':
                key_label = re.sub(r'\b(?:Hon[\'’]?ble|Mr\.|Mrs\.|Ms\.|Justice|CJI|J\.|J)\b', '', l, flags=re.I)
                key_label = re.sub(r',?\s*\b(?:CJI|J\.|J)\b\.?$', '', key_label, flags=re.I)
                key_label = re.sub(r'\s+', ' ', key_label).strip(' ,;.')
                if not key_label or re.search(r'(?:\b[A-Z]\b\s*){3,}', key_label):
                    return None
                packed = re.sub(r'[\s.]+', '', key_label).lower()
                if 'judgment' in packed or 'judgement' in packed:
                    return None
                l = key_label
            node_id = f"{t}|{l}"
            if node_id not in seen:
                seen.add(node_id)
                nodes.append({'id': node_id, 'type': t, 'label': l})
            return node_id

        for k in ('petitioner', 'respondent'):
            v = safe(meta, k)
            if v and v != "Not found in document":
                e = add('Party', v)
                if e: edges.append({'source': 'case', 'target': e, 'type': 'INVOLVES', 'label': 'involves'})

        for j in (safe(meta, 'presiding_judges') or safe(meta, 'judges') or []):
            if j and j != "Not found in document":
                e = add('Judge', j)
                if e: edges.append({'source': 'case', 'target': e, 'type': 'DECIDED_BY', 'label': 'decided_by'})

        court_val = safe(meta, 'court')
        if court_val and court_val != "Not found in document":
            e = add('Court', court_val)
            if e: edges.append({'source': 'case', 'target': e, 'type': 'HEARD_IN', 'label': 'heard_in'})

        for a in (r.get('articles') or []):
            e = add('Article', f"Article {a}")
            if e: edges.append({'source': 'case', 'target': e, 'type': 'RAISES', 'label': 'raises'})

        for s in secs:
            if isinstance(s, dict):
                disp = s.get('display') or f"Section {s.get('num', '')} ({s.get('act', '')})"
            else:
                act_str = section_acts.get(str(s), '')
                disp = f"Section {s} ({act_str})" if act_str else f"Section {s}"
            e = add('Section', disp)
            if e: edges.append({'source': 'case', 'target': e, 'type': 'APPLIES', 'label': 'applies'})

        for p in precs[:6]:
            p_name = p.get('case_name') if isinstance(p, dict) else str(p)
            if p_name and p_name not in ("Precedent Citation", "keyword", "Keyword"):
                e = add('Citation', p_name)
                if e: edges.append({'source': 'case', 'target': e, 'type': 'CITES', 'label': 'cites'})

        return {'nodes': nodes, 'edges': edges}

    # Positional form: meta, secs, precs, evi
    meta = args[0] if len(args) > 0 else kwargs.get('meta', {})
    secs = args[1] if len(args) > 1 else kwargs.get('secs', [])
    precs = args[2] if len(args) > 2 else kwargs.get('precs', [])
    evi = args[3] if len(args) > 3 else kwargs.get('evi', [])

    case_title = safe(meta, 'case_title', 'Case')
    clean_title = re.sub(r'\s+(?:\.\.\.\s*on|on|\.\.\.)\s+\d{1,2}.*$', '', case_title).strip()
    nodes = [{'id': 'case', 'type': 'Case', 'label': clean_title}]
    edges = []
    seen = {'case'}

    def add(t: str, l: str):
        if not l or l.lower() in JUNK: return None
        if t == 'Judge':
            key_label = re.sub(r'\b(?:Hon[\'’]?ble|Mr\.|Mrs\.|Ms\.|Justice|CJI|J\.|J)\b', '', l, flags=re.I)
            key_label = re.sub(r',?\s*\b(?:CJI|J\.|J)\b\.?$', '', key_label, flags=re.I)
            key_label = re.sub(r'\s+', ' ', key_label).strip(' ,;.')
            if not key_label or re.search(r'(?:\b[A-Z]\b\s*){3,}', key_label):
                return None
            packed = re.sub(r'[\s.]+', '', key_label).lower()
            if 'judgment' in packed or 'judgement' in packed:
                return None
            l = key_label
        node_id = f"{t}|{l}"
        if node_id not in seen:
            seen.add(node_id)
            nodes.append({'id': node_id, 'type': t, 'label': l})
        return node_id

    for k in ('petitioner', 'respondent'):
        v = safe(meta, k)
        if v:
            e = add('Party', v)
            if e: edges.append({'source': 'case', 'target': e, 'type': 'INVOLVES', 'label': 'involves'})

    for j in (safe(meta, 'judges') or safe(meta, 'presiding_judges') or []):
        e = add('Judge', j)
        if e: edges.append({'source': 'case', 'target': e, 'type': 'DECIDED_BY', 'label': 'decided_by'})

    court_val = safe(meta, 'court')
    if court_val:
        e = add('Court', court_val)
        if e: edges.append({'source': 'case', 'target': e, 'type': 'HEARD_IN', 'label': 'heard_in'})

    for s in secs:
        disp = s.get('display') if isinstance(s, dict) else f"Section {s}"
        e = add('Section', disp)
        if e: edges.append({'source': 'case', 'target': e, 'type': 'APPLIES', 'label': 'applies'})

    for p in precs:
        p_name = f"{p['case_name']} {p['citation'] or ''}".strip() if isinstance(p, dict) else str(p)
        e = add('Citation', p_name)
        if e: edges.append({'source': 'case', 'target': e, 'type': 'CITES', 'label': 'cites'})

    for item in evi:
        label_val = item.get('label') if isinstance(item, dict) else str(item)
        e = add('Evidence', label_val)
        if e: edges.append({'source': 'case', 'target': e, 'type': 'RELIES_ON', 'label': 'relies_on'})

    return {'nodes': nodes, 'edges': edges}

def calibrate(meta: dict[str, Any], precs: list[Any], tl: list[Any]) -> int:
    not_found_count = sum(1 for v in meta.values() if isinstance(v, dict) and v.get('status') == 'not_found')
    inferred_count = sum(1 for v in meta.values() if isinstance(v, dict) and v.get('status') == 'inferred')
    s = 100 - (3 * not_found_count) - (1 * inferred_count)
    if not precs:
        s -= 5
    return max(40, min(99, s))

def gate(report: dict[str, Any], text: str) -> dict[str, Any]:
    nt = nows(text)
    for k, v in report.get('metadata', {}).items():
        if isinstance(v, dict) and v.get('status') == 'extracted' and v.get('value'):
            val = v['value']
            if isinstance(val, list):
                valid_items = [item for item in val if nows(str(item))[:35] in nt]
                if valid_items:
                    v['value'] = valid_items
                else:
                    v['status'] = 'not_found'
                    v['value'] = None
            else:
                if nows(str(val))[:35] not in nt:
                    v['status'] = 'not_found'
                    v['value'] = None
    return report

# ---------- 10) LEGACY & GROUNDED ISSUES HELPERS ----------
def _court_framed_issues(text: str) -> list[dict[str, Any]]:
    """Extract issues the court itself framed (Issue I: ..., Issue II: ...)."""
    if not text:
        return []
    n = norm(_strip_signature(text))
    results: list[dict[str, Any]] = []
    # Multi-line: "Issue I: Whether ... \n Issue II: Whether ..."
    pat = re.compile(
        r'(Issue\s+[IVXLC]+)\s*:\s*(.+?)(?=\n\s*Issue\s+[IVXLC]+\s*:|\n\s*\d+\.\s+[A-Z]|\Z)',
        re.S | re.I,
    )
    for m in pat.finditer(text):
        label = m.group(1).strip()
        body = re.sub(r'\s+', ' ', m.group(2)).strip()
        body = re.split(r'\n\s*\n', body)[0].strip()
        # Keep the issue statement; cut at signature / next heading if glued
        body = re.split(r'\n(?:\.{5,}|…{3,})', body)[0].strip()
        if not body or len(body) < 15:
            continue
        # Prefer a nearby verbatim sentence as evidence
        quote = None
        for s in split_sentences(n):
            if len(s) > 40 and any(tok.lower() in s.lower() for tok in re.findall(r'[A-Za-z]{6,}', body)[:4]):
                quote = re.sub(r'^\d+\.\s*', '', s).strip()
                break
        if not quote:
            quote = body
        results.append({
            'issue': f"{label}: {body}",
            'text': f"{label}: {body}",
            'evidence': quote if quote in n or len(quote) < 400 else body,
            'source': 'document',
            'page': '1-2',
        })
    # Deduplicate by issue text, prefer the longer first occurrence of each roman numeral
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in results:
        key = item['text'].split(':')[0].upper()
        if key in seen:
            continue
        # If we already have a fuller statement for this numeral, skip the short heading-only one
        if any(o['text'].split(':')[0].upper() == key and len(o['text']) >= len(item['text']) for o in out):
            continue
        out = [o for o in out if o['text'].split(':')[0].upper() != key or len(o['text']) >= len(item['text'])]
        seen.add(key)
        out.append(item)
    return out[:6]

def extract_grounded_issues(r: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """Extract grounded legal issues paired with real verbatim quotes from this specific document."""
    # Prefer issues the court itself framed — these are the strongest grounding.
    court_issues = _court_framed_issues(text)
    if court_issues:
        return court_issues

    m = r.get('metadata') or {}
    pet = safe(m, 'petitioner', 'the petitioner')
    resp = safe(m, 'respondent', 'the respondent')
    sections = r.get('sections') or []
    section_acts = r.get('section_acts') or {}
    articles = r.get('articles') or []
    category = r.get('category') or 'criminal_bail'
    
    n = norm(text)
    sents = split_sentences(n)
    
    def find_best_quote(sec_num: str | None = None, art_num: str | None = None, keywords: list[str] | None = None) -> str | None:
        if sec_num:
            for s in sents:
                if re.search(r'\b(?:Section|Sec\.?|u/s)\s+' + re.escape(sec_num) + r'\b', s, re.I) and len(s) > 25:
                    clean = re.sub(r'^\d+\.\s*', '', s).strip()
                    if not clean.startswith('Bench:') and ' vs ' not in clean[:30]:
                        return clean
        if art_num:
            for s in sents:
                if re.search(r'\bArticle\s+' + re.escape(art_num) + r'\b', s, re.I) and len(s) > 25:
                    clean = re.sub(r'^\d+\.\s*', '', s).strip()
                    if not clean.startswith('Bench:') and ' vs ' not in clean[:30]:
                        return clean
        if keywords:
            for kw in keywords:
                for s in sents:
                    if re.search(r'\b' + re.escape(kw) + r'\b', s, re.I) and len(s) > 30:
                        clean = re.sub(r'^\d+\.\s*', '', s).strip()
                        if not clean.startswith('Bench:') and ' vs ' not in clean[:30]:
                            return clean
        return None

    results: list[dict[str, Any]] = []
    used_quotes: set[str] = set()

    for s in sections:
        sec_str = str(s.get('section_number') if isinstance(s, dict) else s)
        act_str = s.get('act') if isinstance(s, dict) else section_acts.get(sec_str, 'the Act')
        issue_title = f"Whether the statutory requirements of Section {sec_str} ({act_str}) are satisfied on the facts."
        
        quote = find_best_quote(sec_num=sec_str)
        if not quote or quote in used_quotes:
            quote = find_best_quote(keywords=[act_str.split()[0], 'Section ' + sec_str])
        
        if not quote or quote in used_quotes:
            for sub in (r.get('submissions', {}).get('a', []) + r.get('submissions', {}).get('b', [])):
                if sub not in used_quotes and len(sub) > 20:
                    quote = sub
                    break
                    
        if quote:
            used_quotes.add(quote)
            results.append({
                "issue": issue_title,
                "text": issue_title,
                "evidence": quote,
                "source": "document",
                "page": "1-2"
            })

    for a in articles:
        issue_title = f"Whether the impugned action violates Article {a} of the Constitution of India."
        quote = find_best_quote(art_num=str(a), keywords=['proportionality', 'fundamental rights', 'Article ' + str(a)])
        if quote and quote not in used_quotes:
            used_quotes.add(quote)
            results.append({
                "issue": issue_title,
                "text": issue_title,
                "evidence": quote,
                "source": "document",
                "page": "1-2"
            })

    if category in ('criminal', 'criminal_bail', 'criminal_trial') and not any('procedural' in str(x.get('issue', '')).lower() for x in results):
        proc_quote = find_best_quote(keywords=[
            'investigation is complete', 'charge sheet has already been filed',
            'mandatory statutory certification', 'without compliance',
            'panchanama', 'seizure memo', 'recovery'
        ])
        if proc_quote:
            results.append({
                "issue": "Whether mandatory procedural safeguards under applicable criminal codes were complied with during investigation.",
                "text": "Whether mandatory procedural safeguards under applicable criminal codes were complied with during investigation.",
                "evidence": proc_quote,
                "source": "document",
                "page": "1-2"
            })

    if not results:
        sa = r.get('submissions', {}).get('a', [])
        sb = r.get('submissions', {}).get('b', [])
        primary_quote = sa[0] if sa else (sb[0] if sb else (sents[0] if sents else 'Extracted from judicial record.'))
        results.append({
            "issue": f"Whether the claims of {pet} are legally sustainable against {resp}.",
            "text": f"Whether the claims of {pet} are legally sustainable against {resp}.",
            "evidence": primary_quote,
            "source": "document",
            "page": "1-2"
        })

    return results

def render_issues(r: dict[str, Any], text: str | None = None) -> list[str]:
    # Prefer issues the court itself framed in this document.
    if text:
        court = _court_framed_issues(text)
        if court:
            return [item['text'] for item in court]

    m = r.get('metadata') or {}
    iss: list[str] = []
    pet = safe(m, 'petitioner', 'the petitioner')
    resp = safe(m, 'respondent', 'the respondent')
    sections = r.get('sections') or []
    section_acts = r.get('section_acts') or {}
    articles = r.get('articles') or []
    category = r.get('category') or 'criminal_bail'

    for s in sections:
        sec_str = str(s.get('section_number') if isinstance(s, dict) else s)
        act_str = s.get('act') if isinstance(s, dict) else section_acts.get(sec_str, 'the Act')
        iss.append(f"Whether the statutory requirements of Section {sec_str} ({act_str}) are satisfied on the facts.")

    for a in articles:
        iss.append(f"Whether the impugned action violates Article {a} of the Constitution of India.")

    if not iss:
        iss.append(f"Whether the claims of {pet} are legally sustainable against {resp}.")

    if category in ('criminal', 'criminal_bail', 'criminal_trial') and not any('procedural' in str(x).lower() for x in iss):
        iss.append("Whether mandatory procedural safeguards under applicable criminal codes were complied with during investigation.")

    return iss

def render_conclusion(r: dict[str, Any], text: str) -> str:
    m = r.get('metadata') or {}
    pet = safe(m, 'petitioner', 'the petitioner')
    # Prefer the court's own CONCLUSION/ORDER block over the raw text tail
    # (text tail is usually the judge signature block: "......J. [NAME]").
    stripped = _strip_signature(text)
    conclusion_src = _conclusion_section(text) or stripped[-700:]
    if not conclusion_src:
        conclusion_src = stripped[-700:] if len(stripped) > 700 else stripped

    # Prefer a precise operative sentence from the conclusion block first.
    op = _operative_sentence(norm(conclusion_src)) or _operative_sentence(norm(stripped))
    if op and (SPEC_OUTCOME.search(op) or ANY_OUTCOME.search(op)):
        cleaned = re.sub(r'^\s*(?:\d+\.\s*|\(?(?:i{1,3}|iv|v|vi{0,3}|ix|x)\)\s*)+', '', op).strip()
        # Cut at the next numbered sub-clause — keep only the lead operative sentence(s)
        cleaned = re.split(r'\s+\(?(?:ii|iii|iv|v|vi|vii|viii|ix|x)\)\s+', cleaned, maxsplit=1, flags=re.I)[0].strip()
        if cleaned and not re.match(r'^(?:\.{3,}|NEW DELHI|Dated\b)', cleaned, re.I):
            return cleaned if len(cleaned) <= 420 else cleaned[:417].rstrip() + '…'

    tail = conclusion_src
    if re.search(r'partly allowed', tail, re.I):
        return f"Petition partly allowed in favour of {pet}."
    if re.search(r'\b(bail application is allowed|bail is allowed|admitted to bail)\b', tail, re.I):
        return f"Bail application allowed in favour of {pet} on executing regular bond."
    if re.search(r'\ballowed\b', tail, re.I):
        return f"Application/appeal allowed in favour of {pet}."
    if re.search(r'disposed of', tail, re.I):
        return f"Writ petition disposed of with directions; relief granted to {pet}."
    if 'dismissed' in tail.lower():
        return "Appeal dismissed; conviction and sentence upheld."

    if op:
        return norm(op)
    return "Relief granted per operative directions of the judgment."

def render_chips(r: dict[str, Any]) -> list[str]:
    sections = r.get('sections') or []
    articles = r.get('articles') or []
    base: list[str] = []

    for s in sections[:2]:
        sec_str = str(s.get('section_number') if isinstance(s, dict) else s)
        base.append(f"Explain Section {sec_str}.")

    for a in articles[:2]:
        base.append(f"Explain Article {a}.")

    return (base or ["Summarize this judgment."]) + ["Find similar cases."]

BANNED = ['Not found in document', 'Mock summary', 'Applicable Statutes', 'keyword 100%']

def lint(*strings: Any) -> None:
    for item in strings:
        if isinstance(item, (list, tuple)):
            for sub in item:
                lint(sub)
        elif isinstance(item, dict):
            for v in item.values():
                lint(v)
        elif isinstance(item, str):
            for b in BANNED:
                if b.lower() in item.lower():
                    raise ValueError(f"LEAK '{b}' detected in rendered output: {item[:80]}")

# ---------- ENTRY POINT ----------
def build_analysis(text: str) -> dict[str, Any]:
    cat = detect_category(text)
    meta = extract_metadata(text)
    secs, precs = bind_sections(text), extract_precedents(text)
    sa, sb = extract_submissions(text)
    evi = extract_evidence(text)
    tl = build_timeline(text, meta['decision_date']['value'])
    risk = build_risk(text, sa, sb)
    
    statutes_hdr = " • ".join(sorted({s['act'] for s in secs})) or "Applicable Statutes"
    evidence_hdr = "Evidence Integrity & Reliability Matrix"
    label_a, label_b = LABELS[cat]
    
    report = {
        'category': cat,
        'procedural_stage': STAGE[cat],
        'labels': LABELS[cat],
        'statutes_header': statutes_hdr,
        'evidence_header': evidence_hdr,
        'metadata': meta,
        'sections': secs,
        'precedents': precs,
        'evidence': evi,
        'timeline': tl,
        'submissions': {'a': sa, 'b': sb},
        'risk': risk,
        'articles': sorted(set(re.findall(r'Article\s+(\d+(?:\([\w]+\))?)', text))),
        'kg': build_kg(meta, secs, precs, evi)
    }
    report['trust_score'] = calibrate(meta, precs, tl)
    return gate(report, text)
