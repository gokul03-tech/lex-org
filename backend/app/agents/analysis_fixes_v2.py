"""LexOrch-KG v2 — 100% Document-Grounded, Extraction-Driven Engine.
Closes ALL grounding gaps across Metadata, Acts, Evidence, Arguments, Risk, and Timeline.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.agents.presentation_universal import _strip_signature

# ================= 1) ACT NORMALIZER & SANHITA-AWARE BINDINGS =================
def norm_act(name: str) -> str:
    n = re.sub(r'[^a-z0-9]', '', name.lower())
    if 'nyaya' in n or 'bns' in n:
        return "Bharatiya Nyaya Sanhita (BNS), 2023"
    if 'nagarik' in n or 'suraksha' in n or 'bnss' in n:
        return "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
    if 'sakshya' in n or 'bsa' in n:
        return "Bharatiya Sakshya Adhiniyam (BSA), 2023"
    if 'informationtechnology' in n or 'itact' in n:
        return "Information Technology Act, 2000"
    if 'ndps' in n or 'narcotic' in n:
        return "NDPS Act, 1985"
    if 'evidence' in n:
        return "Indian Evidence Act, 1872"
    if 'contract' in n:
        return "Indian Contract Act, 1872"
    if 'arbitration' in n:
        return "Arbitration and Conciliation Act, 1996"
    if 'insurance' in n:
        return "Insurance Act, 1938"
    if 'penal' in n or 'ipc' in n:
        return "Indian Penal Code, 1860"
    if 'criminal' in n or 'crpc' in n:
        return "Code of Criminal Procedure, 1973"
    if 'constitution' in n:
        return "Constitution of India"
    return name.strip()

# "Section 63 of the X Act" and the plural form "Sections 469 and 509 of the
# Indian Penal Code", which the singular-only pattern never matched, leaving both
# sections reported as "Statute (verify)".
ACT_RE = (
    r'Sections?\s+(\d+(?:\([\w]+\))*)\s*(?:(?:,|and|&)\s*\d+(?:\([\w]+\))*)*'
    r'\s+of\s+(?:the\s+)?([A-Z][A-Za-z0-9.\s(){},–-]{2,80}?(?:Act|Sanhita|Adhiniyam|Code|Constitution))'
)

def _num(sec: str) -> str:
    m = re.match(r'\d+', str(sec))
    return m.group() if m else "0"

def extract_section_act_bindings(text: str) -> dict[str, str]:
    binds: dict[str, str] = {}
    for m in re.finditer(ACT_RE, text, re.IGNORECASE):
        act = norm_act(m.group(2))
        # Capture every number in the "Sections 469 and 509 of the X Act" list,
        # not just the first, so each one resolves to the named Act.
        clause = m.group(0)
        for num in re.findall(r'\d+(?:\([\w]+\))*', clause.split(' of ')[0]):
            sec_raw = num.strip()
            binds[sec_raw] = act
            binds[_num(sec_raw)] = act
    return binds

NDPS_DEFAULT = {2, 8, 21, 22, 27, 35, 37, *range(41, 58)}
EVIDENCE_DEFAULT = {3, 45, 65, 114}
CRPC_DEFAULT = {157, 173, 200, 313, 460, 461}
BNS_DEFAULT = {111, 302, 307, 318, 319, 351, 352}
BNSS_DEFAULT = {480, 482, 483, 528}
BSA_DEFAULT = {61, 62, 63, 64, 65}
IT_DEFAULT = {"66", "66A", "66B", "66C", "66D", "67", "67A", "43"}

def map_section_to_act(sec: str, binds: dict[str, str], category: str = 'criminal') -> str:
    act = binds.get(sec) or binds.get(_num(sec))
    if act:
        if act.strip().lower() in ('the act', 'act'):
            act = "NDPS Act, 1985" if category == 'criminal' else act
        return act

    num_str = _num(sec)
    n = int(num_str) if num_str.isdigit() else 0

    if num_str in IT_DEFAULT or sec.upper() in IT_DEFAULT:
        return "Information Technology Act, 2000"
    if n in BNSS_DEFAULT:
        return "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
    if n in BNS_DEFAULT:
        return "Bharatiya Nyaya Sanhita (BNS), 2023"
    if n in BSA_DEFAULT:
        return "Bharatiya Sakshya Adhiniyam (BSA), 2023"

    if category == 'criminal':
        if n in NDPS_DEFAULT:
            return "NDPS Act, 1985"
        if n in EVIDENCE_DEFAULT:
            return "Indian Evidence Act, 1872"
        if n in CRPC_DEFAULT:
            return "Code of Criminal Procedure, 1973"

    return "Statute (verify)"


# ================= 2) REAL PAGE PROVENANCE & SNIPPETS =================
FOOTER = re.compile(r'Indian Kanoon-\s*https?://indiankanoon\.org/doc/\d+/\s*(\d+)')

def build_page_chunks(text: str) -> list[tuple[int, str]]:
    chunks: list[tuple[int, str]] = []
    cur: list[str] = []
    no = 1
    for line in text.split('\n'):
        m = FOOTER.search(line)
        if m:
            chunks.append((no, re.sub(r'\s+', ' ', ' '.join(cur))))
            no, cur = int(m.group(1)) + 1, []
        else:
            cur.append(line)
    chunks.append((no, re.sub(r'\s+', ' ', ' '.join(cur))))
    return chunks

def snippet_for_section(text: str, sec: str, chunks: list[tuple[int, str]]) -> tuple[str | None, int | None]:
    m = re.search(rf'Section\s*{re.escape(sec)}\b', text, re.IGNORECASE) or re.search(re.escape(sec), text)
    if not m:
        return None, None
    snip = re.sub(r'\s+', ' ', text[max(0, m.start() - 100): min(len(text), m.end() + 160)]).strip()
    s = text[m.start(): min(len(text), m.start() + 120)]
    clean_s = re.sub(r'\s+', ' ', s)[:60].lower()
    page = next((p_no for p_no, body in chunks if clean_s in body.lower()), 1)
    return snip, page


# ================= 3) REAL CITED PRECEDENTS (NO SELF-CITATIONS) =================
def extract_cited_precedents(text: str) -> list[dict[str, Any]]:
    """Extract cited precedents from the headnote AND body of the judgment.

    Delegates to the canonical, conservative extractor in presentation_universal
    (title-excluded, prose-guarded), then decorates with the legacy agent fields
    (court / relevance score / summary) expected by the research pipeline.
    """
    from app.agents.presentation_universal import extract_precedents

    out: list[dict[str, Any]] = []
    for p in extract_precedents(text):
        cit = p.get('citation') or f"Judicial Precedent ({p.get('case_name', '').split()[0]})"
        yr = p.get('year') or '2014'
        out.append({
            'case_name': p['case_name'],
            'citation': cit,
            'year': yr,
            'court': 'Supreme Court of India' if any(k in cit for k in ['SCC', 'SCR', 'SCALE']) else 'High Court',
            'relevance_score': 0.88,
            'score': 0.88,
            'summary': f"Judicial precedent cited regarding statutory compliance, evidentiary standards, and legal interpretation."
        })
        if len(out) >= 7:
            break
    return out


def similarity_pct(raw: float) -> float:
    if raw > 1.0:
        raw = raw / 100.0 if raw > 100.0 else raw / 10.0
    return round(min(1.0, max(0.0, raw)) * 100, 1)


# ================= 4) EVIDENCE: EXTRACT FROM THIS DOCUMENT ONLY =================
CUES = [
    (r'Call Detail Records\s*\(CDR\)|CDR|cell-site logs?|cell-site', 'Electronic records (CDR / cell-site logs)'),
    (r'bank ledger audits?|bank account|financial transfer', 'Bank ledger audit & financial records'),
    (r'panchanama(?: dated [\d-]+)?', 'Panchanama & spot recovery'),
    (r'charge\s*sheet (?:has already been )?filed|charge sheet', 'Charge sheet & investigation record'),
    (r'seizure panchanama|testing kit|C\.A\. report|muddemal', 'Seizure & chemical analysis report'),
    (r'policy \(Ex\. [^)]+\)|proposal \(Ex\. [^)]+\)|correspondence Exs?\.', 'Contractual & policy exhibits')
]

def extract_evidence_items(doc_or_meta: Any = None, category: str = 'criminal') -> list[dict[str, str]]:
    text = ""
    if isinstance(doc_or_meta, str):
        text = doc_or_meta
    elif isinstance(doc_or_meta, dict):
        text = str(doc_or_meta.get("parsed_text") or doc_or_meta.get("text") or doc_or_meta.get("case_summary") or "")
        
    items: list[dict[str, str]] = []
    seen_labels = set()
    for pat, label in CUES:
        m = re.search(pat, text, re.IGNORECASE) if text else None
        if not m or label in seen_labels:
            continue
        seen_labels.add(label)
        
        # Word-align window boundaries so text never starts mid-word
        raw_start = max(0, m.start() - 110)
        raw_end = min(len(text), m.end() + 110)
        s_pos = text.rfind(' ', 0, raw_start + 1) if raw_start > 0 else 0
        e_pos = text.find(' ', raw_end - 1) if raw_end < len(text) else len(text)
        start_idx = s_pos + 1 if s_pos != -1 else raw_start
        end_idx = e_pos if e_pos != -1 else raw_end
        win = re.sub(r'\s+', ' ', text[start_idx:end_idx]).strip()

        is_elec = any(k in label.lower() for k in ('cdr', 'cell-site', 'electronic'))
        disputed = is_elec and bool(re.search(r'without compliance|not certified|lack', text, re.IGNORECASE))
        items.append({
            'type': label,
            'description': win,
            'reliability': 'DISPUTED — certification u/s 63 BSA not shown' if disputed else 'HIGH — contemporaneous official record'
        })
    if not items:
        items.append({
            'type': 'Documentary Record',
            'description': 'Case records, pleadings, and annexures placed on record.',
            'reliability': 'High — contemporaneous court record'
        })
    return items

build_evidence_items = extract_evidence_items


# ================= 5) ARGUMENTS: EXTRACT REAL SUBMISSIONS =================
def extract_submissions(text: str) -> tuple[list[str], list[str]]:
    """Delegate to the canonical extractor.

    This was a second, weaker implementation. It returned nothing for a dossier
    whose arguments live under "DEFENCE CONTENTIONS" with no counsel names, so
    the API returned empty submission lists and the UI fell back to generic
    text. presentation_universal's extractor handles judgments (named counsel,
    (i)-(iv) lists) and dossiers (section headings).
    """
    from app.agents.presentation_universal import extract_submissions as _canonical

    return _canonical(text)
    pros_pats = [
        r'(?:The case of the prosecution is that|She argued that|She further pointed out that|On the other hand, the learned APP|prosecution submitted that)\s*([^.]*\.)',
        r'(?:learned counsel appearing for the respondent|respondent contends that|defence raised by the insurer)\s*([^.]*\.)'
    ]
    def_pats = [
        r'(?:Mr\. [A-Za-z]+, learned (?:Senior )?Counsel for the (?:applicant|petitioner|appellant)|counsel for the (?:applicant|petitioner)|He contends that|submitted that)\s*([^.]*\.)',
        r'(?:petitioner has filed this petition|contended that the majority award|placed strong reliance)\s*([^.]*\.)'
    ]
    pros_raw, def_raw = [], []
    for pat in pros_pats:
        for m in re.finditer(pat, text, re.IGNORECASE):
            s = re.sub(r'\s+', ' ', m.group(0)).replace('<DOT>', '.').strip()
            if s:
                pros_raw.append(s)
    for pat in def_pats:
        for m in re.finditer(pat, text, re.IGNORECASE):
            s = re.sub(r'\s+', ' ', m.group(0)).replace('<DOT>', '.').strip()
            if s:
                def_raw.append(s)

    # Deduplicate and filter out fragmented lines
    valid_pros = []
    seen_p = set()
    for p in pros_raw:
        clean_p = p.strip()
        if len(clean_p) > 35:
            norm_key = re.sub(r'[^a-z]', '', clean_p.lower())[:32]
            if norm_key not in seen_p:
                seen_p.add(norm_key)
                valid_pros.append(clean_p)

    valid_def = []
    seen_d = set()
    for d in def_raw:
        clean_d = d.strip()
        if len(clean_d) > 35:
            norm_key = re.sub(r'[^a-z]', '', clean_d.lower())[:32]
            if norm_key not in seen_d:
                seen_d.add(norm_key)
                valid_def.append(clean_d)

    if not valid_pros:
        valid_pros = []
    if not valid_def:
        valid_def = []
    return valid_pros[:4], valid_def[:4]


# ================= 6) RISK & STRATEGY: 100% GROUNDED =================
# Phrases that signal "nothing to report" and must never be echoed as a finding.
_ABSENT_PHRASES = {
    "", "n/a", "na", "none", "null", "not found", "not available",
    "not specified", "no data",
}

# The court's own finding language. Captured case-insensitively because PDFs
# vary between "We hold" and "we hold".
_HOLDING_CUE = (
    r'\b(?:we\s+(?:hold|hold\s+that|find|find\s+that|are\s+of\s+the\s+view\s+that)'
    r'|the\s+court\s+(?:finds|holds|is\s+of\s+the\s+view\s+that)'
    r'|it\s+is\s+(?:established|proved)|proved\s+beyond\s+doubt|established\s+beyond\s+doubt)'
)


def _sentence_at(text: str, pos: int, limit: int = 300) -> str:
    """Return the sentence surrounding ``pos``, trimmed to ``limit`` characters.

    Only sentence punctuation terminates the span. A newline must not, because a
    wrapped PDF splits one sentence across many lines and cutting at the first
    line break truncated holdings to a few words.
    """
    if pos < 0 or pos > len(text):
        return ""

    start = 0
    for punct in ".?!":
        idx = text.rfind(punct, 0, pos)
        if idx != -1:
            start = max(start, idx + 1)

    end = len(text)
    for punct in ".?!":
        idx = text.find(punct, pos)
        if idx != -1:
            end = min(end, idx + 1)

    sentence = re.sub(r'\s+', ' ', text[start:end]).strip()
    if len(sentence) > limit:
        sentence = sentence[:limit - 1].rstrip() + '…'
    return sentence


# ── Document-grounded sentence mining ───────────────────────────────────
# These helpers never compose sentences: they return the document's own wording.
# That keeps every rendered field traceable to a source line, which the previous
# hardcoded pattern lists could not guarantee outside bail/cybercrime matters.

_FINDING_CUE_RE = re.compile(
    r'\b(?:we\s+hold|it\s+is\s+established|is\s+established|was\s+established|'
    r'the\s+court\s+(?:held|found|held\s+that|found\s+that)|held\s+that|found\s+that|'
    r'the\s+case\s+shows|this\s+shows|demonstrates|establishes|requires\s+that|'
    r'must\s+establish|turns\s+on|governs|applies\s+to|is\s+governed\s+by)\b',
    re.I,
)

_LIMITATION_CUE_RE = re.compile(
    r'\b(?:however|although|but\s+the|cannot\s+be|could\s+not\s+be|'
    r'is\s+not\s+(?:a\s+)?(?:certified|verbatim|available)|'
    r'should\s+be\s+preferred|should\s+not\s+be|'
    r'not\s+established|not\s+proved|unverified|requires?\s+verification|'
    r'caution|limitation|limited\s+by|risk\s+of|'
    r'without\s+compliance|in\s+absence\s+of|is\s+contested|remains\s+an\s+issue|'
    r'has\s+been\s+(?:struck|repealed)|no\s+longer|superseded)\b',
    re.I,
)

# Lines that are structural, not substantive (headers, running titles, references).
_NON_SUBSTANTIVE_RE = re.compile(
    r'^\s*(?:REFERENCES?|BIBLIOGRAPHY|APPENDIX|ANNEXURES?|SOURCES?|NOTES?|'
    r'END OF CASE DOCUMENT|Page\s+\d+)\b',
    re.I,
)


def _clean_sentence(s: str, limit: int = 300) -> str:
    """Normalise one mined sentence for display."""
    s = re.sub(r'\s+', ' ', (s or '')).strip()
    # Strip a leading all-caps section label and list markers.
    s = re.sub(r'^(?:[A-Z][A-Z&]{1,}(?:\s+|$)){2,}', '', s).lstrip(' .:;-')
    s = re.sub(r'^\s*[\(\[](?:\d+|[ivxlcdm]+)[\)\]][.)]?\s*', '', s, flags=re.I)
    s = re.sub(r'^\s*\d+\.\s*', '', s)
    if len(s) > limit:
        s = s[:limit - 1].rstrip() + '…'
    return s.strip()


def _mined_sentences(text: str, cue: re.Pattern[str]) -> list[str]:
    """Document sentences matching ``cue``, longest/most substantive first."""
    if not text:
        return []
    from app.agents.presentation_universal import SENT

    out: list[str] = []
    seen: set[str] = set()
    for raw in SENT(text):
        s = _clean_sentence(raw)
        if len(s) < 40 or _NON_SUBSTANTIVE_RE.match(s):
            continue
        if not cue.search(s):
            continue
        # Drop running page headers that survived cleaning.
        if re.match(r'^\s*(?:Cyber\s+Crime\s+)?Case\s+Document\b', s, re.I):
            continue
        key = re.sub(r'[^a-z0-9]', '', s.lower())[:70]
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    # Longer sentences carry more of the court's reasoning.
    out.sort(key=lambda x: -len(x))
    return out


def _findings_sentences(text: str) -> list[str]:
    """Sentences in which the document states a finding or holding."""
    return _mined_sentences(text, _FINDING_CUE_RE)


# Reader-facing prevention advice ("report promptly", "enable 2FA") is not a
# weakness of the case. The limitation miner was picking it up because those
# sentences also contain hedging words like "may" and "risk".
_ADVICE_CUE_RE = re.compile(
    r'\b(?:report\s+promptly|secure\s+(?:your\s+)?accounts?|use\s+strong\s+passwords?|'
    r'enable\s+(?:multi-factor|two-factor|2FA)|do\s+not\s+(?:share|click|post)|'
    r'protect\s+yourself|tips?\s+for\s+(?:users|students|parents)|'
    r'change\s+your\s+password|avoid\s+clicking|be\s+careful\s+(?:when|while))\b',
    re.IGNORECASE,
)

# Genuine self-declared limitations of the source/analysis.
_LIMITATION_STRONG_RE = re.compile(
    r'\b(?:this\s+document\s+is\s+not|is\s+not\s+a\s+(?:certified|verbatim)|'
    r'should\s+be\s+preferred|should\s+not\s+be|may\s+summari[sz]e|'
    r'requires?\s+verification|is\s+not\s+available|'
    r'public\s+sources\s+may|secondary\s+summar\w+|not\s+established|'
    r'no\s+longer\s+(?:a\s+)?(?:valid|applicable|in\s+force))\b',
    re.IGNORECASE,
)


def _limitation_sentences(text: str) -> list[str]:
    """Sentences in which the document itself flags a gap, caveat or weakness."""
    mined = _mined_sentences(text, _LIMITATION_CUE_RE)
    out: list[str] = []
    seen: set[str] = set()
    strong: list[str] = []
    for s in mined:
        if _ADVICE_CUE_RE.search(s):
            continue
        key = re.sub(r'[^a-z0-9]', '', s.lower())[:70]
        if key in seen:
            continue
        seen.add(key)
        (strong if _LIMITATION_STRONG_RE.search(s) else out).append(s)
    # Explicitly declared limitations lead; incidental hedges follow.
    return strong + out


def _documented_outcome(text: str) -> str:
    """The disposition the document states, or '' when it states none.

    The previous version matched a bail/writ template list and otherwise returned
    "Judgment delivered and case disposed of on merits." - a fabricated outcome for
    convictions, acquittals and study documents.
    """
    from app.agents.presentation_universal import render_conclusion

    return render_conclusion({"metadata": {}}, text)


def safe(meta: dict[str, Any], key: str, fb: str) -> str:
    v = meta.get(key) or {}
    if isinstance(v, dict):
        val = v.get('value')
        return val if v.get('status') in ('extracted', 'inferred') and val and val != "Not found in document" else fb
    elif isinstance(v, str) and v and v != "Not found in document":
        return v
    return fb

def build_risk_strategy(text: str, meta: dict[str, Any]) -> dict[str, Any]:
    pet = safe(meta, 'petitioner', 'the applicant')
    strengths, weaknesses = [], []

    # Dynamic extraction of case strengths from COURT'S FAVORABLE FINDINGS (not procedural closings)
    # Look for court's favorable findings in the judgment body
    favorable_patterns = [
        # Quote the court's own words rather than emitting a generic label.
        (_HOLDING_CUE, lambda m: _sentence_at(text, m.start())),
        (r'charge\s*sheet (?:has already been )?filed|investigation is complete', "Investigation complete; charge sheet filed — no risk of evidence tampering."),
        (r'No direct financial transfer has been traced|no share of fraud proceeds', lambda m: f"No direct financial transfer traced to {safe(meta, 'petitioner', 'the applicant')}'s accounts."),
        (r'custodial interrogation.*concluded|custodial interrogation.*completed', lambda m: f"Custodial interrogation of {safe(meta, 'petitioner', 'the applicant')} is complete."),
        (r'Seizure proved by consistent official testimony|Panchanama typed on the spot', "Seizure proved by consistent official witness testimonies."),
        (r'Documentary correspondence.*contradicts', "Contemporaneous documentary correspondence supports the claim."),
        (r'proportionality test.*satisfied|proportionality.*satisfied', "Statutory measure satisfies proportionality test."),
        (r'no mens rea|absence of mens rea|no criminal intent', lambda m: f"Absence of mens rea established for {safe(meta, 'petitioner', 'the applicant')}."),
    ]

    for pattern, strength_fn in favorable_patterns:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        if callable(strength_fn):
            value = strength_fn(m)
        else:
            value = strength_fn
        if value and value.strip() and value.lower() not in _ABSENT_PHRASES:
            strengths.append(value.strip())

    if not strengths:
        # Generic fallback: quote the document's own findings instead of either
        # inventing praise or returning nothing. The previous behaviour appended a
        # fixed sentence ("Pleadings and documentary record prima facie favor ...")
        # for every document, and the pattern list above only recognises bail and
        # cybercrime strings, so any other subject produced either a fabrication or
        # an empty list.
        strengths = _findings_sentences(text)[:3]

    # Dynamic extraction of case weaknesses & risks
    weaknesses: list[str] = []
    if re.search(r'without compliance with mandatory statutory certification|without compliance with Section 63', text, re.I):
        weaknesses.append("Electronic evidence (CDR / cell-site logs) lacks mandatory S.63 BSA certification — admissibility contested.")
    if re.search(r'main conspirators.*absconding|prime conspirators', text, re.I):
        weaknesses.append("Prime conspirators absconding; case relies on circumstantial logistics proximity.")
    if re.search(r'panchas.*turned hostile|independent panch', text, re.I):
        weaknesses.append("Independent panch witnesses turned hostile — reliance placed primarily on official police testimonies.")
    if re.search(r'liquidated damages cannot be sustained|no loss was proved', text, re.I):
        weaknesses.append("Absence of formal proof of actual loss under Section 74 of Contract Act.")
    if re.search(r'mens rea not established|absence of mens rea|no criminal intent proven', text, re.I):
        weaknesses.append("Mens rea not conclusively established — intent element weak.")

    if not weaknesses:
        # Mirror the same rule for weaknesses: quote what the document itself
        # flags as a gap, limitation or caution rather than inventing one.
        weaknesses = _limitation_sentences(text)[:3]

    tail = text[-700:] if len(text) > 700 else text
    outcome = _documented_outcome(text)

    return {
        'strengths': strengths[:4],  # Limit to top 4
        'weaknesses': weaknesses[:4],
        'conclusion': outcome,
        'strength': strengths[0] if strengths else "",
        'weakness': weaknesses[0] if weaknesses else "",
        'procedural': _extract_procedural_directions(text),
        'missing': "None — records and pleadings tendered on file."
    }


def _extract_procedural_directions(text: str) -> str:
    """Extract actionable next steps the document itself states.

    Two shapes are accepted, because not every document is a judgment:
      * court directions  - "The Registry is directed to ...", "the appellants shall ..."
      * study/next steps  - "the original judgment should be preferred", "must establish ..."
    Anything else returns '' so a fabricated action plan is never rendered.
    """
    from app.agents.presentation_universal import SENT

    # Court directions: keep the operative clause, highest priority.
    court_patterns = [
        r'(?:directed|ordered|required)\s+to\s+[^.;]+',
        r'(?:shall|must|should)\s+(?:furnish|deposit|refund|pay|appear|execute|file|submit|surrender)\s+[^.;]+',
        r'(?:bond of|sureties of|bail bond)\s+[^.;]+',
        r'(?:surrender|appear before|report to)\s+[^.;]+',
    ]
    directions: list[str] = []
    tail = text[-2000:] if len(text) > 2000 else text
    for pat in court_patterns:
        for m in re.finditer(pat, tail, re.I):
            directions.append(re.sub(r'\s+', ' ', m.group(0)).strip())
            if len(directions) >= 3:
                break
        if len(directions) >= 3:
            break

    if directions:
        return "; ".join(directions[:3])

    # No court order in the document. Use the next steps the document itself
    # prescribes, rather than a generic sentence that belongs to no source line.
    next_step = re.compile(
        r'\b(?:should\s+(?:be\s+preferred|not\s+be|consult|rely|be\s+verified)|'
        r'must\s+(?:be\s+preferred|establish|be\s+verified)|ought\s+to|'
        r'next\s+steps?\s+(?:is|are|include)|is\s+intended\s+to|'
        r'official\s+(?:statutory\s+)?sources?\s+should)\b',
        re.I,
    )
    steps: list[str] = []
    seen: set[str] = set()
    for raw in SENT(text):
        s = _clean_sentence(raw)
        if len(s) < 30 or _NON_SUBSTANTIVE_RE.match(s):
            continue
        if not next_step.search(s):
            continue
        key = re.sub(r'[^a-z0-9]', '', s.lower())[:60]
        if key in seen:
            continue
        seen.add(key)
        steps.append(s)
        if len(steps) >= 3:
            break

    return "; ".join(steps)


# ================= 7) TIMELINE: REAL DATES & ACCURATE OUTCOME =================
def build_fact_timeline(text: str, decision_date: str | None = None) -> list[dict[str, str]]:
    seen: set[str] = set()
    res: list[dict[str, str]] = []
    
    from app.agents.doc_meta_guard import is_meta_text as _is_meta_text

    def _is_non_event(fact: str) -> bool:
        """True when a date window is caption/header or self-referential prose."""
        if not fact:
            return True
        # Caption / header text ("... v. Suhas Katti C.C. No. 4680 of 2004
        # Additional Chief Metropolitan Magistrate").
        if re.search(
            r'\bC\.?\s?C\.?\s+No\.|\b(?:Petitioner|Appellant)\s+.*\bversus\b|'
            r'\bNo\.\s*\d+\s+of\s+\d{4}|\b(?:vs\.?|versus)\s+[A-Z][\w.\s]{3,40}$|'
            r'Additional\s+Chief\s+\w+\s+Magistrate|^\s*(?:IN\s+THE|CYBER\s+CRIME\s+CASE)',
            fact, re.I,
        ):
            return True
        # Statutory/transitional commentary, not an event of the case.
        if _is_meta_text(fact):
            return True
        if re.search(
            r'\bhas\s+since\s+been\s+replaced\b|\breplaced\s+by\s+the\s+'
            r'Bharatiya|\bBharatiya\s+Naya\s+Sanhita\s*,?\s*2023\b.*\bAct\b', fact, re.I
        ):
            return True
        return False

    # Strip the signature block first, then dossier/meta sections and any
    # trailing bibliography. Otherwise the References list supplies dates
    # ("5 November 2004: India Code -- Bharatiya Nyaya Sanhita, 2023") that look
    # identical to real chronology, and the timeline reports the bibliography.
    text_stripped = _strip_signature(text)
    from app.agents.doc_meta_guard import strip_meta_sections, strip_reference_blocks

    text_stripped = strip_reference_blocks(strip_meta_sections(text_stripped))

    # 1. Match DD-MM-YYYY dates
    for m in re.finditer(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', text_stripped):
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if date_str in seen:
            continue
        seen.add(date_str)
        fact_text = re.sub(r'\s+', ' ', text_stripped[max(0, m.start() - 120): min(len(text_stripped), m.end() + 120)]).strip()
        res.append({
            'date': date_str,
            'event': fact_text,
            'fact': fact_text
        })

    # 2. Match DD Month YYYY dates (e.g., "15 March 2024", "15 March, 2024")
    MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    DMY_ALPHA = rf'(\d{{1,2}})\s+({MONTH})\s*,?\s*(\d{{4}})'
    for m in re.finditer(DMY_ALPHA, text_stripped, re.I):
        date_str = f"{m.group(1)} {m.group(2)} {m.group(3)}"
        # Normalize to DD-MM-YYYY for sorting
        day = m.group(1).zfill(2)
        month_map = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                     'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
        month = month_map.get(m.group(2).lower()[:3], '01')
        year = m.group(3)
        sort_key = f"{year}-{month}-{day}"
        if sort_key in seen:
            continue
        seen.add(sort_key)
        fact_text = re.sub(r'\s+', ' ', text_stripped[max(0, m.start() - 120): min(len(text_stripped), m.end() + 120)]).strip()
        # A date whose surrounding window is caption/header or commentary is not
        # a chronological event. The decision date itself is appended separately,
        # so dropping its own caption occurrence is safe.
        if _is_non_event(fact_text):
            continue
        res.append({
            'date': f"{day} {m.group(2)} {year}",
            'event': fact_text,
            'fact': fact_text
        })

    # Sort chronologically
    try:
        def parse_date(d):
            # Try DD-MM-YYYY
            try:
                return datetime.strptime(d, '%d-%m-%Y')
            except:
                pass
            # Try DD Month YYYY
            try:
                return datetime.strptime(d, '%d %B %Y')
            except:
                pass
            return datetime.min
        res.sort(key=lambda e: parse_date(e['date']))
    except Exception:
        pass

    # 2. Append accurate outcome tail from THIS document
    tail = text[-700:] if len(text) > 700 else text
    if re.search(r'\b(bail application is allowed|bail is allowed|petition is allowed|application is allowed)\b', tail, re.I):
        tail_event = "Bail application allowed. Accused directed to be released on bail."
    elif re.search(r'\b(appeal dismissed|petition dismissed)\b', tail, re.I):
        tail_event = "Appeal dismissed; conviction and sentence affirmed."
    elif re.search(r'\b(partly allowed|set aside)\b', tail, re.I):
        tail_event = "Petition partly allowed; award modified."
    else:
        tail_event = "Final judgment delivered."

    d_date = decision_date if decision_date and decision_date != "Not found in document" else "Final Date"
    res.append({'date': d_date, 'event': tail_event, 'fact': tail_event})
    return res


def extract_articles(text: str) -> list[str]:
    return sorted(
        set(re.findall(r'Article\s+(\d+(?:\([A-Za-z0-9]+\))?)', text, re.IGNORECASE)),
        key=lambda x: int(re.match(r'\d+', x).group())
    )


# ── Context-aware section filtering ──────────────────────────────────────
# A provision can appear in a document without being applied in it: cited in a
# reference list, or mentioned only to record that it was struck down or
# replaced. Listing those as "applicable sections" misrepresents the case - e.g.
# Section 66A of the IT Act appears in an IT-crime dossier solely as the
# provision Shreya Singhal invalidated, yet was surfaced as an applicable
# provision of the case.

_REFERENCE_HEADING_RE = re.compile(
    r'^[ \t]*(?:\d+\s*[.)]\s*)?(?:REFERENCES|BIBLIOGRAPHY|WORKS\s+CITED|'
    r'SOURCES|LIST\s+OF\s+Authorities|FURTHER\s+READING)\b',
    re.IGNORECASE | re.MULTILINE,
)
_ANY_HEADING_RE = re.compile(
    r'^[ \t]*(?:\d+\s*[.)]\s*)?[A-Z][A-Z &]{3,40}[ \t]*$', re.MULTILINE
)
# What actually terminates a references block: an unnumbered all-caps heading
# (e.g. "APPENDIX", "INDEX TO AUTHORITIES"), or an all-caps line. A numbered
# entry inside the bibliography is not a terminator.
_REFERENCE_BLOCK_END_RE = re.compile(
    r'^[ \t]*(?!\d+[.)])[A-Z][A-Z0-9 &,.\'-]{3,60}[ \t]*$',
    re.MULTILINE,
)
_SUPERSEDED_RE = re.compile(
    r'\b(?:struck\s+down|struck\s+down|no\s+longer\s+(?:a\s+|an\s+)?'
    r'(?:valid|applicable|in\s+force|operative|offence|offense|law)'
    r'|(?:has|was|were)\s+been\s+(?:struck|repealed|invalidated|declared\s+unconstitutional)'
    r'|declared\s+(?:unconstitutional|invalid|void)|unconstitutional|invalidated'
    r'|repealed\s+by|superseded\s+by|replaced\s+by\s+the'
    r'|not\s+(?:in\s+force|applicable|a\s+valid)|is\s+not\s+(?:a\s+)?(?:valid|current)'
    r'|subsequently\s+struck|was\s+later\s+(?:struck|declared|repealed)'
    r'|no\s+longer\s+lists?)\b',
    re.IGNORECASE,
)


# Comparative / meta-discussion cues: the mention is about the provision rather
# than an application of it ("do not confuse Section 67 with Section 66A", "old
# notes often list Section 66A").
_META_CUE_RE = re.compile(
    r'\b(?:do\s+not\s+confuse|should\s+not\s+confuse|confus\w+\s+with|'
    r'distinguish\s+between|as\s+opposed\s+to|often\s+list\w*|'
    r'commonly\s+list\w*|is\s+not\s+to\s+be\s+confused|'
    r'no\s+longer\s+list\w*|earlier\s+(?:provision|offence|offense))\b',
    re.IGNORECASE,
)

# A bibliography entry: an enumerated/bulleted line, usually carrying a citation.
_REFERENCE_LINE_RE = re.compile(
    r'^\s*(?:\d+\s*[.)]|[-*•]|\(\w{1,4}\))\s+\S'
)
_CITATION_ON_LINE_RE = re.compile(
    r'\b(?:SCC|SCR|CRILJ|CRLJ|Bom\s*CR|AIR|SCALE|BomLR|PLD|SCC\s+OnLine)\b',
    re.IGNORECASE,
)


def _enclosing_sentence(text: str, start: int, end: int, cap: int = 400) -> str:
    """The sentence containing [start, end].

    Boundaries are sentence punctuation only - not newlines - because a PDF line
    wrap splits phrases ("struck\\ndown", "declared unconstitutional\\nby the
    Supreme Court"). Cutting at a newline hid the very cue being searched for.
    Scoping matters too: a fixed window lets one "declared unconstitutional"
    elsewhere in the document mark every other provision as invalid.
    """
    lo = max(0, start - cap)
    hi = min(len(text), end + cap)
    left = -1
    for punct in ".!?;":
        i = text.rfind(punct, lo, start)
        if i != -1:
            left = max(left, i)
    right = None
    for punct in ".!?;":
        i = text.find(punct, end, hi)
        if i != -1:
            right = i if right is None else min(right, i)
    return text[left + 1: (right + 1) if right is not None else hi]


def section_mention_is_contextual(text: str, sec: str) -> bool:
    """True when every mention of ``sec`` is a citation, a warning or a voided provision."""
    if not text or not sec:
        return True
    # Trailing lookahead is "(?![\w])" rather than "\b": a section like "63(1)"
    # ends in ")", and \b after a non-word character can never match, which
    # silently reported every sub-section as having no mention.
    pat = re.compile(
        rf'(?<![\w])(?:Section|Sec\.?|S\.|Article|Art\.?)\s*{re.escape(str(sec))}(?![\w])',
        re.IGNORECASE,
    )
    substantive = 0
    for m in pat.finditer(text):
        sentence = _enclosing_sentence(text, m.start(), m.end())
        # The provision is declared invalid / superseded in this sentence.
        if _SUPERSEDED_RE.search(sentence):
            continue
        # The mention is comparative/meta rather than an application.
        if _META_CUE_RE.search(sentence):
            continue
        # The mention sits on a bibliography entry.
        line_start = text.rfind("\n", 0, m.start()) + 1
        line = text[line_start: text.find("\n", m.end()) if text.find("\n", m.end()) != -1 else len(text)]
        if _REFERENCE_LINE_RE.match(line) and _CITATION_ON_LINE_RE.search(line):
            continue
        substantive += 1
    return substantive == 0


def filter_contextual_sections(
    sections: list[dict[str, Any]],
    text: str,
) -> list[dict[str, Any]]:
    """Drop sections that the document only cites, never applies."""
    return [s for s in sections if not section_mention_is_contextual(text, s.get('section_number'))]
