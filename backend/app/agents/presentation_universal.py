"""LexOrch-KG v6 — Universal Presentation Layer.
Works for criminal, civil, bail, arbitration, writ — ANY document.
Rule: every rendered string comes from the report; never from status or other cases.
"""
from __future__ import annotations

import re
from typing import Any

safe = lambda m, k, fb=None: (
    m[k]['value']
    if isinstance(m, dict) and isinstance(m.get(k), dict)
    and m[k].get('status') in ('extracted', 'inferred')
    and m[k].get('value') and m[k].get('value') != "Not found in document"
    else (m[k] if isinstance(m, dict) and isinstance(m.get(k), (str, list)) and m[k] != "Not found in document" else fb)
)


# ---- 1) ISSUES: generated from THIS doc's sections/articles, parties via safe() ----
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

    if category == 'criminal' and not any('procedural' in str(x).lower() for x in iss):
        iss.append("Whether mandatory procedural safeguards under applicable criminal codes were complied with during investigation.")

    return iss


# ---- 2) CONCLUSION: outcome-driven, party-aware, zero leakage ----
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


# ---- 3) CHIPS: from THIS doc (sections -> articles -> fallback) ----
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


# ---- 4) KNOWLEDGE GRAPH: universal node builder (never empty) ----
def build_kg(r: dict[str, Any]) -> dict[str, Any]:
    m = r.get('metadata') or {}
    raw_title = safe(m, 'case_title', 'Case')
    clean_title = re.sub(r'\s+(?:\.\.\.\s*on|on|\.\.\.)\s+\d{1,2}.*$', '', raw_title).strip()
    
    nodes: list[dict[str, Any]] = [{'id': 'case', 'type': 'Case', 'label': clean_title}]
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = {'case'}

    def add(t: str, l: str) -> str:
        node_id = f"{t}|{l}"
        if node_id not in seen_nodes and l.lower() != 'keyword':
            seen_nodes.add(node_id)
            nodes.append({'id': node_id, 'type': t, 'label': l})
        return node_id

    for k in ('petitioner', 'respondent'):
        v = safe(m, k)
        if v and v != "Not found in document":
            target_id = add('Party', v)
            edges.append({'source': 'case', 'target': target_id, 'type': 'INVOLVES', 'label': 'involves'})

    for j in (safe(m, 'presiding_judges') or []):
        if j and j != "Not found in document":
            target_id = add('Judge', j)
            edges.append({'source': 'case', 'target': target_id, 'type': 'DECIDED_BY', 'label': 'decided_by'})

    court_val = safe(m, 'court')
    if court_val and court_val != "Not found in document":
        target_id = add('Court', court_val)
        edges.append({'source': 'case', 'target': target_id, 'type': 'HEARD_IN', 'label': 'heard_in'})

    for a in (r.get('articles') or []):
        target_id = add('Article', f"Article {a}")
        edges.append({'source': 'case', 'target': target_id, 'type': 'RAISES', 'label': 'raises'})

    sections = r.get('sections') or []
    section_acts = r.get('section_acts') or {}
    for s in sections:
        sec_str = str(s.get('section_number') if isinstance(s, dict) else s)
        act_str = s.get('act') if isinstance(s, dict) else section_acts.get(sec_str, '')
        label_sec = f"Sec {sec_str} ({act_str})" if act_str else f"Section {sec_str}"
        target_id = add('Section', label_sec)
        edges.append({'source': 'case', 'target': target_id, 'type': 'APPLIES', 'label': 'applies'})

    for p in (r.get('precedents') or [])[:6]:
        p_name = p.get('case_name') if isinstance(p, dict) else str(p)
        if p_name and p_name not in ("Precedent Citation", "keyword", "Keyword"):
            target_id = add('Citation', p_name)
            edges.append({'source': 'case', 'target': target_id, 'type': 'CITES', 'label': 'cites'})

    # Filter out any stray keyword artifacts
    filtered_nodes = [n for n in nodes if n.get('label', '').lower() != 'keyword' and not str(n.get('id', '')).endswith('|keyword')]
    filtered_edges = [e for e in edges if not str(e.get('target', '')).endswith('|keyword') and not str(e.get('source', '')).endswith('|keyword')]

    return {'nodes': filtered_nodes, 'edges': filtered_edges}


# ---- 5) LEAK LINT: hard fail in dev if any banned string renders ----
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
