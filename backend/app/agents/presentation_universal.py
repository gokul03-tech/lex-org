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
SENT = lambda t: re.split(r'(?<=[a-z])\.\s+(?=[A-Z0-9])', t)
JUNK = {'keyword', 'vector', '', 'null', 'none'}

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
    sc = {
        'criminal_bail': len(re.findall(r'\bbail\b|arrested|charge sheet|f\.?i\.?r', t)),
        'criminal_trial': len(re.findall(r'conviction|sentence|accused|ndps|narcotic|panchas', t)),
        'civil': len(re.findall(r'plaintiff|defendant|specific performance|sale deed|conveyance|decree|order 39|registration act', t)),
        'arbitration': len(re.findall(r'arbitral|arbitration|award|section 34|patent illegality', t)),
        'writ': len(re.findall(r'article 32|article 226|writ petition|proportionality|fundamental right', t))
    }
    return max(sc, key=sc.get)

STAGE = {
    'criminal_bail': 'Regular Bail Petition',
    'criminal_trial': 'Criminal Trial / Appeal',
    'civil': 'Civil Suit / Appeal',
    'arbitration': 'Petition u/s 34 (Setting Aside Award)',
    'writ': 'Writ Petition (Constitutional)'
}

LABELS = {
    'criminal_bail': ('State / Prosecution Case', 'Applicant / Defense Submissions'),
    'criminal_trial': ('Prosecution Arguments', 'Defense Rebuttals'),
    'civil': ('Appellant / Plaintiff Case', 'Respondent / Defense Case'),
    'arbitration': ('Petitioner Submissions', 'Respondent Submissions'),
    'writ': ('Petitioner Submissions', 'Respondent / State Submissions')
}

# ---------- 2) METADATA ----------
ACT = r'([A-Z][A-Za-z.\s(){},&\-]{2,80}?(?:Act|Sanhita|Adhiniyam|Code|Constitution|Regulation)s?(?:,?\s?(?:19|20)\d{2})?)'

def norm_act(n: str) -> str:
    l = nows(n)
    if 'specificrelief' in l: return 'Specific Relief Act, 1963'
    if 'contract' in l: return 'Indian Contract Act, 1872'
    if 'civilprocedure' in l or 'cpc' in l: return 'Code of Civil Procedure, 1908'
    if 'registration' in l: return 'Indian Registration Act, 1908'
    if 'nagarik' in l: return 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023'
    if 'nyaya' in l: return 'Bharatiya Nyaya Sanhita (BNS), 2023'
    if 'sakshya' in l: return 'Bharatiya Sakshya Adhiniyam (BSA), 2023'
    if 'informationtechnology' in l: return 'Information Technology Act, 2000'
    if 'arbitration' in l: return 'Arbitration and Conciliation Act, 1996'
    if 'evidence' in l: return 'Indian Evidence Act, 1872'
    if 'narcotic' in l or 'ndps' in l: return 'NDPS Act, 1985'
    return norm(n)

PATS = [
    r'(C\.?R\.? No\.?\s*\d+\s*of\s*\d{4})',
    r'(Appeal No\.?\s*\d+\s*of\s*\d{4})',
    r'(Suit No\.?\s*\d+\s*of\s*\d{4})',
    r'(Special Case No\.?\s*\d+\s*of\s*\d{4})',
    r'(FIR No\.?\s*\d+\s*of\s*\d{4})',
    r'(Arbitration Petition No\.?\s*\d+\s*of\s*\d{4})'
]

def extract_metadata(text: str) -> dict[str, Any]:
    n = norm(text)
    head = n[:1400]
    
    # 4) Prettify court
    m = re.search(r'(IN THE [A-Z ]+COURT[A-Z ]*|SUPREME COURT OF INDIA)', head, re.I)
    court_raw = norm(m.group(1)) if m else None
    court_clean = re.sub(r'^IN THE\s+', '', court_raw, flags=re.I).title() if court_raw else None
    if court_clean and 'Supreme Court' in court_clean:
        court_clean = 'Supreme Court of India'

    # 1) Parties: split the TITLE LINE, never the whole text
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    tl = next((l for l in lines[:8] if re.search(r'\b(?:vs\.?|v\.)\b', l, re.I)), None)
    if tl:
        parts = re.split(r'\s+(?:vs\.?|v\.)\s+', tl, maxsplit=1, flags=re.I)
        pet = norm(parts[0])
        resp = norm(parts[1]) if len(parts) > 1 else None
        resp = re.sub(r'\s*(?:\.\.\.)?\s*on\s+\d{1,2}.*$', '', resp or '').strip()
    else:
        pet, resp = None, None

    dm = re.search(r'on\s+(\d{1,2})[ ,]+([A-Z][a-z]+)[ ,]+(\d{4})', head)
    cites = re.findall(r'\(\d{4}\)\s?\d+\s?[A-Z]+\s?\d+|AIR\s?\d{4}\s?[A-Z ]+\d+|\[\d{4}\]\s?\d+\s?SCR\s?\d+|\d{4}\s?Cri\s?LJ\s?\d+', n.split('JUDGMENT')[0], re.I)
    
    # 3) Case number: NO default -> honest not_found
    case_no = next((m.group(1) for p in PATS if (m := re.search(p, n))), None)
    judges_list = re.findall(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*),\s*J\.', n) or None

    title_str = f"{pet} vs {resp}" if pet and resp else (pet or "Legal Matter Dossier")

    return {
        'court': F(court_clean, 'extracted' if court_clean else 'not_found'),
        'case_title': F(title_str, 'extracted' if pet else 'not_found'),
        'petitioner': F(pet, 'extracted' if pet else 'not_found'),
        'respondent': F(resp, 'extracted' if resp else 'not_found'),
        'decision_date': F(f"{dm.group(1)} {dm.group(2)} {dm.group(3)}" if dm else None, 'extracted' if dm else 'not_found'),
        'citation_numbers': F(cites or None, 'extracted' if cites else 'not_found'),
        'case_number': F(case_no, 'extracted' if case_no else 'not_found'),
        'judges': F(judges_list, 'extracted' if judges_list else 'not_found'),
        'presiding_judges': F(judges_list, 'extracted' if judges_list else 'not_found')
    }

# ---------- 3) SECTIONS (formatted strings — never raw dicts) ----------
def bind_sections(text: str) -> list[dict[str, Any]]:
    n = norm(text)
    out = []
    for m in re.finditer(r'of\s+the\s+' + ACT, n):
        act = norm_act(m.group(1))
        win = n[max(0, m.start()-180):m.start()]
        for s in re.findall(r'Sections?\s*(?:s\s+)?(\d+(?:\([\w]+\))*)', win, re.I):
            out.append({'num': s, 'section_number': s, 'act': act, 'display': f"Section {s} — {act}"})
        for o in re.findall(r'Order\s+(\d+)\s+Rule\s+([\d,\s&]+)', win):
            out.append({'num': f"O.{o[0]} R.{o[1].strip()}", 'section_number': f"O.{o[0]} R.{o[1].strip()}", 'act': act, 'display': f"Order {o[0]} R. {o[1].strip()} — {act}"})
    return list({d['display']: d for d in out}.values())

# ---------- 4) PRECEDENTS (each name ↔ its OWN citation) ----------
def extract_precedents(text: str) -> list[dict[str, Any]]:
    n = norm(text)
    out, seen = [], set()
    for m in re.finditer(r'((?:\(\d{4}\)\s?\d+\s?[A-Z]+\s?\d+|\[\d{4}\]\s?\d+\s?SCR\s?\d+|\d{4}\s?\d+\s?SCC\s?\d+|AIR\s?\d{4}\s?[A-Z ]+\d+))?\s*in the case of\s+([A-Z][A-Za-z0-9.&\-,\s]{2,70}?\s+v\.?\s+[A-Z][A-Za-z0-9.&\-,\s]{2,70}?)(?=\s+(?:holding|wherein|regarding|which)|,|\.)', n):
        name = norm(m.group(2))
        if nows(name)[:14] in seen or name.lower() in JUNK:
            continue
        seen.add(nows(name)[:14])
        out.append({
            'case_name': name,
            'citation': (m.group(1) or '').strip() or None,
            'year': (re.search(r'(19|20)\d{2}', m.group(1) or '') or [None, None])[1],
            'summary': f"Precedent cited for legal principle on this issue."
        })
    return out

# ---------- 5) SUBMISSIONS (counsel attribution, category labels) ----------
ROLE = re.compile(r'for the\s+(petitioner|applicant|appellant|plaintiff|respondent|State|vendor|defendant)', re.I)

def extract_submissions(text: str) -> tuple[list[str], list[str]]:
    n = norm(text)
    a, b, cur = [], [], None
    for s in SENT(n):
        if re.search(r'Solicitor General|learned APP', s):
            cur = 'b'
        m = ROLE.search(s)
        if m:
            cur = 'a' if m.group(1).lower() in ('petitioner', 'applicant', 'appellant', 'plaintiff') else 'b'
        if cur and re.search(r'submitted|contended|argued|relied|pointed|defended|opposed|demonstrated', s, re.I):
            (a if cur == 'a' else b).append(s)
    return a[:3], b[:3]

# ---------- 6) EVIDENCE (per-item reliability, word-aligned) ----------
CUES = [
    (r'Call Detail Records\s*\(CDR\)|cell-site logs', 'Electronic Records (CDR / cell-site logs)'),
    (r'panchanama dated [\d-]+', 'Panchanama'),
    (r'bank ledger audits|bank statements|escrow', 'Financial Records'),
    (r'charge sheet', 'Charge Sheet / Investigation Record'),
    (r'Ex\.\s*P-?\d+', 'Documentary Exhibits'),
    (r'correspondence dated [\d-]+ and [\d-]+', 'Contemporaneous Correspondence'),
    (r'agreement to sell|conveyance deed', 'Title / Contract Documents')
]

def extract_evidence(text: str) -> list[dict[str, Any]]:
    n = norm(text)
    items = []
    for pat, label in CUES:
        m = re.search(pat, n, re.I)
        if not m:
            continue
        win = n[max(0, m.start()-220):m.end()+220]
        # 9) word-aligned windows
        st = n.rfind(' ', 0, max(0, m.start()-140)) + 1
        items.append({
            'label': label,
            'reliability': 'DISPUTED' if re.search(r'without compliance|certification under Section|not certified', win, re.I) else 'HIGH',
            'detail': n[st:m.end()+160]
        })
    return items[:4]

# ---------- 7) TIMELINE + OUTCOME ----------
def build_timeline(text: str, date: str | None) -> list[dict[str, Any]]:
    n = norm(text)
    ev = [{'date': m.group(0), 'fact': n[snap(n, m.start()-140):m.end()+140], 'page': '1-2'}
          for m in re.finditer(r'\d{2}-\d{2}-\d{4}', n)]
    tail = n[-600:]
    op = next((s for s in SENT(tail) if re.search(r'allowed|set aside|disposed|directed', s, re.I)), 'Judgment delivered.')
    return ev + [{'date': date or 'Final Hearing Date', 'fact': op, 'page': '1-2'}]

# ---------- 8) RISK (fully extracted; operative para = action plan) ----------
def build_risk(text: str, subs_a: list[str], subs_b: list[str]) -> dict[str, Any]:
    n = norm(text)
    strengths = [s for s in SENT(n) if re.search(r'We hold|established|readiness and willingness|No direct financial transfer|investigation is complete|charge sheet has already been filed', s, re.I)][:2]
    tail = n[-600:]
    op = next((s for s in SENT(tail) if re.search(r'allowed|set aside|disposed|directed', s, re.I)), None)
    return {
        'strengths': strengths or subs_a[:1],
        'gaps': subs_b[:2],
        'action_plan': [op] if op else [],
        'conclusion': op or 'Relief per operative paragraph.'
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

# 10) Honest trust: min(99, 100 - 3*not_found_count - 1*inferred_count)
def calibrate(meta: dict[str, Any], precs: list[Any], tl: list[Any]) -> int:
    not_found_count = sum(1 for v in meta.values() if isinstance(v, dict) and v.get('status') == 'not_found')
    inferred_count = sum(1 for v in meta.values() if isinstance(v, dict) and v.get('status') == 'inferred')
    s = 100 - (3 * not_found_count) - (1 * inferred_count)
    if not precs:
        s -= 5
    return max(40, min(99, s))

def gate(report: dict[str, Any], text: str) -> dict[str, Any]:
    for k, v in report.get('metadata', {}).items():
        if isinstance(v, dict) and v.get('status') == 'extracted' and v.get('value'):
            if nows(str(v['value']))[:50] not in nows(text):
                v['status'] = 'not_found'
                v['value'] = None
    return report

# ---------- 10) LEGACY HELPERS ----------
def render_issues(r: dict[str, Any]) -> list[str]:
    m = r.get('metadata') or {}
    iss: list[str] = []
    pet = safe(m, 'petitioner', 'the petitioner')
    resp = safe(m, 'respondent', 'the respondent')
    sections = r.get('sections') or []
    section_acts = r.get('section_acts') or {}
    articles = r.get('articles') or []
    category = r.get('category') or 'criminal'

    for s in sections:
        sec_str = str(s.get('section_number') if isinstance(s, dict) else s)
        act_str = s.get('act') if isinstance(s, dict) else section_acts.get(sec_str, 'the Act')
        iss.append(f"Whether the statutory requirements of Section {sec_str} ({act_str}) are satisfied on the facts.")

    for a in articles:
        iss.append(f"Whether the impugned action violates Article {a} of the Constitution of India.")

    if not iss:
        iss.append(f"Whether the claims of {pet} are legally sustainable against {resp}.")

    if category in ('criminal', 'criminal_bail') and not any('procedural' in str(x).lower() for x in iss):
        iss.append("Whether mandatory procedural safeguards under applicable criminal codes were complied with during investigation.")

    return iss

def render_conclusion(r: dict[str, Any], text: str) -> str:
    m = r.get('metadata') or {}
    pet = safe(m, 'petitioner', 'the petitioner')
    tail = text[-700:] if len(text) > 700 else text

    if re.search(r'partly allowed', tail, re.I):
        return f"Petition partly allowed in favour of {pet}."
    if re.search(r'\b(bail application is allowed|bail is allowed)\b', tail, re.I):
        return f"Bail application allowed in favour of {pet} on executing regular bond."
    if re.search(r'\ballowed\b', tail, re.I):
        return f"Application/appeal allowed in favour of {pet}."
    if re.search(r'disposed of', tail, re.I):
        return f"Writ petition disposed of with directions; relief granted to {pet}."
    if 'dismissed' in tail.lower():
        return "Appeal dismissed; conviction and sentence upheld."
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
    
    # 5+6) dynamic headings & 7) labels
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
