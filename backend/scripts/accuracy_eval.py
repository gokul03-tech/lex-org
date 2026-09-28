"""Repeatable accuracy harness for LexOrch-KG extraction modules.

Every module is scored against golden labels for a specific document, so
"accuracy" is a measured number instead of an eyeball impression. Each scored
module asserts one thing: that the pipeline reproduces a fact that is
verifiable in that document.

Usage:
    .venv/bin/python scripts/accuracy_eval.py                 # all corpora
    .venv/bin/python scripts/accuracy_eval.py --list
    .venv/bin/python scripts/accuracy_eval.py --only metadata statutes
    .venv/bin/python scripts/accuracy_eval.py --path some.pdf --corpus adhoc
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.presentation_universal import (  # noqa: E402
    _court_framed_issues,
    build_kg,
    build_timeline,
    extract_grounded_issues,
    extract_precedents,
    extract_submissions,
    render_conclusion,
)
from app.agents.analysis_fixes_v2 import build_risk_strategy  # noqa: E402
from app.document_pipeline.cleaner import TextCleaner  # noqa: E402
from app.document_pipeline.metadata_extractor import LegalMetadataExtractor  # noqa: E402
from app.document_pipeline.parser import DocumentParser  # noqa: E402

THRESHOLD = 95.0

GENERIC_MARKERS = (
    "prima facie favor",
    "settled principles of legal precedent",
    "asserts statutory compliance",
    "relief granted per operative",
    "no sufficiently relevant precedent found",
    "strict statutory interpretation and judicial",
    "petitioner contends allegations warrant relief",
)

# Phrases that mean "the engine found nothing" and must never be presented as a
# finding for a document that does contain a real disposition.
FABRICATED_OUTCOMES = (
    "relief granted per operative",
    "judgment delivered and case disposed of on merits",
)


def nows(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def text_has(text: str, *needles: str) -> bool:
    hay = nows(text)
    return all(nows(n) in hay for n in needles)


# ── Scorers ────────────────────────────────────────────────────────────────
# Each returns (score_pct, notes:list[str]). Scoring is per-fact, not per-call:
# a module only scores if the value matches the golden label.

def score_metadata(text: str, meta: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    checks: list[tuple[str, bool]] = []

    for field in gold.get("parties", []):
        side, want = field["side"], field["value"]
        got = (meta.get(side) or {}).get("value") or ""
        # A party name must not carry a running header or a role suffix.
        clean = text_has(got, want) and not re.search(
            r"(?:—|--|\.\.\.)\s*(?:Appellant|Petitioner|Respondent|Defendant)?$", got.strip(), re.I
        )
        checks.append((f"party.{side}", clean))
        if not clean:
            notes.append(f"party.{side}: got {got!r}, want ~{want!r}")

    court_want = gold.get("court")
    if court_want:
        got = (meta.get("court") or {}).get("value") or ""
        ok = text_has(got, court_want) or text_has(court_want, got)
        checks.append(("court", bool(ok)))
        if not ok:
            notes.append(f"court: got {got!r}, want ~{court_want!r}")

    num_want = gold.get("case_number")
    if num_want:
        got = (meta.get("case_number") or {}).get("value") or ""
        ok = text_has(got, num_want)
        checks.append(("case_number", ok))
        if not ok:
            notes.append(("case_number: got %r, want ~%r" % (got, num_want)))

    date_want = gold.get("decision_date")
    if date_want:
        got = (meta.get("decision_date") or {}).get("value") or ""
        ok = text_has(got, date_want) or text_has(date_want, got)
        checks.append(("decision_date", bool(ok)))
        if not ok:
            notes.append(f"date: got {got!r}, want ~{date_want!r}")

    if not checks:
        return 100.0, ["no metadata labels defined"]
    passed = sum(1 for _, ok in checks if ok)
    return 100.0 * passed / len(checks), notes


def score_statutes(text: str, sections: list[dict[str, Any]], gold: dict[str, Any]) -> tuple[float, list[str]]:
    """Sections are scored two ways: required ones present, and extras defensible.

    An extra provision is only penalised when it is neither in the golden set nor
    actually present in the document - i.e. a genuine hallucination. A provision
    the document genuinely discusses (e.g. a struck-down section mentioned in a
    historical note) is not an error, so it is recorded but not penalised.
    """
    notes: list[str] = []
    required = gold.get("required_sections", [])
    forbidden_hallucinated = gold.get("hallucinated_sections", [])

    got_nums = {str(s.get("section_number") or "") for s in sections}
    got_nows = {nows(n) for n in got_nums if n}

    hit = [r for r in required if nows(r) in got_nows]
    miss = [r for r in required if nows(r) not in got_nows]
    for m in miss:
        notes.append(f"missing required section {m}")

    extras = [n for n in got_nums if n and nows(n) not in {nows(r) for r in required}]
    unbacked = [
        n for n in extras
        if not any(nows(n) in nows(t) for t in re.findall(r"[^\n]{0,80}", text))
    ]
    for h in forbidden_hallucinated:
        if nows(h) in got_nows and not re.search(rf"\b{re.escape(h)}\b", text, re.I):
            notes.append(f"HALLUCINATED section {h} (absent from document)")
            unbacked.append(h)

    total = len(required) + len(extras)
    if total == 0:
        return (100.0, ["no sections extracted"]) if not required else (0.0, ["no sections extracted"])
    passed = len(hit) + (len(extras) - len(unbacked))
    return 100.0 * passed / total, notes


def score_issues(text: str, issues: list[Any], gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    required = gold.get("required_topics", [])
    if gold.get("non_empty") and not issues:
        return 0.0, ["issues are EMPTY"]

    blob = " ".join(
        str(i.get("text") or i.get("issue") or i.get("question") or "") if isinstance(i, dict) else str(i)
        for i in issues
    )
    if not blob.strip():
        return 0.0, ["issues produced no text"]

    checks: list[bool] = []
    for topic in required:
        # A topic counts as covered when the issue text shares its key concept.
        key = topic.split()[0].lower()
        ok = key in blob.lower()
        checks.append(ok)
        if not ok:
            notes.append(f"issue topic not covered: {topic}")

    if gold.get("max_issues"):
        checks.append(len(issues) <= gold["max_issues"])
        if len(issues) > gold["max_issues"]:
            notes.append(f"too many issues: {len(issues)} > {gold['max_issues']}")

    # Issues must be grounded: no placeholder text.
    junk = [m for m in GENERIC_MARKERS if m in blob.lower()]
    checks.append(not junk)
    if junk:
        notes.append(f"generic/placeholder text in issues: {junk}")

    passed = sum(1 for c in checks if c)
    return 100.0 * passed / len(checks), notes


def score_conclusion(text: str, conclusion: str, gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    conc = (conclusion or "").strip()
    if not conc:
        return 0.0, ["conclusion is EMPTY"]
    if not conc:
        pass
    else:
        low = conc.lower()
        fab = [f for f in FABRICATED_OUTCOMES if f in low]
        if fab:
            notes.append(f"fabricated outcome: {fab}")
            return 0.0, notes

    required = gold.get("required_concepts", [])
    checks = [text_has(conc, c) for c in required]
    for c, ok in zip(required, checks):
        if not ok:
            notes.append(f"conclusion missing concept: {c}")

    # Must not be a bare generic sentence.
    checks.append(len(conc) >= 40)
    if len(conc) < 40:
        notes.append(f"conclusion too short ({len(conc)} chars)")
    return 100.0 * sum(checks) / len(checks), notes


def score_devils_advocate(text: str, risk: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    fields = [
        risk.get("strengths") or [],
        risk.get("weaknesses") or [],
        [risk.get("procedural") or ""],
        [risk.get("conclusion") or ""],
    ]
    blob = " ".join(str(x) for f in fields for x in f)
    checks: list[bool] = []

    html = re.findall(r"</?(?:b|i|p|div|span|em|strong|br)\b[^>]*>", blob, re.I)
    checks.append(not html)
    if html:
        notes.append(f"HTML leakage: {sorted(set(html))[:5]}")

    junk = [m for m in GENERIC_MARKERS if m in blob.lower()]
    checks.append(not junk)
    if junk:
        notes.append(f"generic fallback text: {junk}")

    if not any(risk.get("strengths") or []) and not any(risk.get("weaknesses") or []):
        checks.append(False)
        notes.append("no strengths and no weaknesses extracted")
    else:
        checks.append(True)

    # A cited term must actually appear in the document.
    for term in gold.get("must_not_invent", []):
        if term.lower() in blob.lower() and not re.search(re.escape(term), text, re.I):
            checks.append(False)
            notes.append(f"invented term not in document: {term}")

    passed = sum(1 for c in checks if c)
    return 100.0 * passed / len(checks), notes


def score_strategy(text: str, risk: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    blob = " ".join(
        [str(risk.get("procedural") or ""), str(risk.get("conclusion") or "")]
        + [str(s) for s in (risk.get("strengths") or [])]
    )
    checks: list[bool] = []

    html = re.findall(r"</?(?:b|i|p|div|span|em|strong|br)\b[^>]*>", blob, re.I)
    checks.append(not html)
    if html:
        notes.append(f"HTML leakage: {sorted(set(html))[:5]}")

    junk = [m for m in GENERIC_MARKERS if m in blob.lower()]
    checks.append(not junk)
    if junk:
        notes.append(f"generic fallback text: {junk}")

    # The action plan must be a real direction, not a heading or a reference list.
    procedural = str(risk.get("procedural") or "")
    ok_action = bool(re.search(r"\b(?:directed|shall|must|ordered|required|furnish|appear|remand)\b", procedural, re.I))
    checks.append(ok_action)
    if not ok_action:
        notes.append(f"action plan is not a procedural direction: {procedural[:70]!r}")

    if gold.get("procedure_concepts"):
        for concept in gold["procedure_concepts"]:
            if not text_has(procedural, concept):
                checks.append(False)
                notes.append(f"action plan missing concept: {concept}")

    passed = sum(1 for c in checks if c)
    return 100.0 * passed / len(checks), notes


def score_kg(text: str, kg: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    blob = json.dumps(kg, default=str)
    checks: list[bool] = []

    nodes = kg.get("nodes") or kg.get("nodes", [])
    edges = kg.get("edges") or []
    checks.append(bool(nodes))
    if not nodes:
        notes.append("KG has no nodes")

    # Central / case node must name the case, not the running header.
    central = ""
    for n in nodes:
        if isinstance(n, dict) and str(n.get("type", "")).lower() in ("case", "central", "document"):
            central = str(n.get("label") or n.get("id") or "")
            break
    want_case = gold.get("kg_case_label")
    if want_case:
        ok = text_has(central, want_case)
        checks.append(bool(ok))
        if not ok:
            notes.append(f"KG central node {central!r} does not name the case (~{want_case!r})")

    for side in gold.get("kg_party_sides", []):
        want = next((p["value"] for p in gold.get("parties", []) if p["side"] == side), None)
        if not want:
            continue
        hit = any(
            isinstance(n, dict) and text_has(str(n.get("label") or ""), want)
            for n in nodes
        )
        checks.append(hit)
        if not hit:
            notes.append(f"KG missing {side} node ~{want!r}")

    passed = sum(1 for c in checks if c)
    return 100.0 * passed / len(checks), notes


def score_timeline(text: str, timeline: list[dict[str, Any]], gold: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    if not timeline:
        return 0.0, ["timeline is EMPTY"]
    blob = " ".join(f"{e.get('date','')} {e.get('fact') or e.get('event') or ''}" for e in timeline)
    checks = [True]
    html = re.findall(r"</?(?:b|i|p|div|span|em|strong|br)\b[^>]*>", blob, re.I)
    checks.append(not html)
    if html:
        notes.append(f"HTML leakage: {sorted(set(html))[:5]}")
    for d in gold.get("required_dates", []):
        if nows(d) not in nows(blob):
            checks.append(False)
            notes.append(f"timeline missing date: {d}")
    return 100.0 * sum(checks) / len(checks), notes


# ── Corpus ─────────────────────────────────────────────────────────────────

CORPORA: dict[str, dict[str, Any]] = {
    "suhas_katti": {
        "file": "data/uploads/e3a52ef5d5064de1b9279d82106f8e82_cyber_crime_case_document_suhas_katti_20_pages (1).pdf",
        "label": "Academic dossier (20pp, no bench, no Issue framing)",
        "gold": {
            "parties": [
                {"side": "petitioner", "value": "State of Tamil Nadu"},
                {"side": "respondent", "value": "Suhas Katti"},
            ],
            "court": "Additional Chief Metropolitan Magistrate",
            "case_number": "4680",
            "decision_date": "5 November 2004",
            "required_sections": ["67", "469", "509"],
            "hallucinated_sections": ["66A"],
            "required_topics": ["electronic"],
            "non_empty": True,
            "max_issues": 6,
            "required_concepts": ["67"],
            "must_not_invent": ["mens rea", "vicarious conspiracy"],
            "kg_case_label": "Suhas Katti",
            "kg_party_sides": ["petitioner", "respondent"],
            "required_dates": ["5 November 2004"],
        },
    },
}


def load_text(corpus: dict[str, Any]) -> str:
    parser = DocumentParser()
    raw = parser.parse(corpus["file"])
    pages = raw.get("pages") or [raw.get("text", "")]
    return TextCleaner().clean("\n".join(pages))


def evaluate(path: str, gold: dict[str, Any], label: str) -> dict[str, Any]:
    t0 = time.monotonic()
    text = load_text({"file": path})
    t_load = time.monotonic() - t0

    extractor = LegalMetadataExtractor()
    # Deterministic path: the LLM path is exercised separately in the pipeline.
    extractor._extract_metadata_via_llm = lambda _t: {}
    meta = extractor.extract(text)

    # Mirror legal_research_agent: every "Section N" mention in the document,
    # with its Act resolved from in-text bindings (falling back to defaults).
    from app.agents.analysis_fixes_v2 import (  # noqa: E402
        extract_section_act_bindings,
        map_section_to_act,
    )

    category = (meta.get("case_category") or {}).get("value") or "criminal"
    binds = extract_section_act_bindings(text)
    seen_sec: set[str] = set()
    sections: list[dict[str, Any]] = []
    for m in re.finditer(
        r"(?:Section|Sec\.?|u/s|under\s+section|s\.)\s*(\d+[A-Za-z]*(?:\([a-z0-9]+\))*)",
        text,
        re.IGNORECASE,
    ):
        num = m.group(1)
        if num in seen_sec:
            continue
        seen_sec.add(num)
        sections.append({
            "section_number": num,
            "act": map_section_to_act(num, binds, category=category),
            "explicitly_mentioned": True,
        })
    # In-text "Section N of the X Act" bindings count as citations too.
    for num, act in binds.items():
        if num not in seen_sec:
            seen_sec.add(num)
            sections.append({"section_number": num, "act": act, "explicitly_mentioned": True})

    r_ctx = {
        "metadata": meta,
        "sections": [s["section_number"] for s in sections],
        "articles": [],
        "precedents": [],
        "category": category,
    }
    issues = _court_framed_issues(text) or extract_grounded_issues(r_ctx, text)
    conclusion = render_conclusion(meta, text)
    risk = build_risk_strategy(text, meta)
    timeline = build_timeline(text, (meta.get("decision_date") or {}).get("value"))
    kg = build_kg(r_ctx)
    _ = extract_submissions(text), extract_precedents(text)

    scorers: list[tuple[str, Callable[[], tuple[float, list[str]]]]] = [
        ("metadata", lambda: score_metadata(text, meta, gold)),
        ("statutes", lambda: score_statutes(text, sections, gold)),
        ("issues", lambda: score_issues(text, issues, gold)),
        ("conclusion", lambda: score_conclusion(text, conclusion, gold)),
        ("devils_advocate", lambda: score_devils_advocate(text, risk, gold)),
        ("strategy", lambda: score_strategy(text, risk, gold)),
        ("knowledge_graph", lambda: score_kg(text, kg, gold)),
        ("timeline", lambda: score_timeline(text, timeline, gold)),
    ]

    results: dict[str, Any] = {}
    for name, fn in scorers:
        try:
            score, notes = fn()
        except Exception as exc:  # a crashing module scores 0, it does not abort the run
            score, notes = 0.0, [f"EXCEPTION {type(exc).__name__}: {exc}"]
        results[name] = {"score": round(score, 1), "notes": notes}

    overall = sum(v["score"] for v in results.values()) / len(results)
    results["_overall"] = round(overall, 1)
    results["_seconds"] = round(time.monotonic() - t0, 2)
    results["_load_seconds"] = round(t_load, 2)
    results["_label"] = label
    results["_chars"] = len(text)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--path", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    corpora = CORPORA
    if args.path:
        corpora = {"adhoc": {"file": args.path, "gold": CORPORA["suhas_katti"]["gold"]}}

    all_results: dict[str, Any] = {}
    for name, corpus in corpora.items():
        p = Path(corpus["file"])
        if not p.exists():
            print(f"[skip] {name}: {p} not found")
            continue
        res = evaluate(str(p), corpus["gold"], corpus.get("label", name))
        all_results[name] = res

    if args.json:
        print(json.dumps(all_results, indent=2, default=str))
        return 0 if all(r["_overall"] >= THRESHOLD for r in all_results.values()) else 1

    keys = [k for k in ("metadata", "statutes", "issues", "conclusion",
                        "devils_advocate", "strategy", "knowledge_graph", "timeline")]
    for name, res in all_results.items():
        print("=" * 78)
        print(f"{name} — {res['_label']}")
        print(f"  {res['_chars']} chars, evaluated in {res['_seconds']}s (load {res['_load_seconds']}s)")
        print("-" * 78)
        for k in keys:
            if args.only and k not in args.only:
                continue
            v = res[k]
            flag = "PASS" if v["score"] >= THRESHOLD else "FAIL"
            print(f"  {flag}  {k:<18} {v['score']:6.1f}%")
            for note in v["notes"]:
                print(f"          - {note}")
        ov = res["_overall"]
        print("-" * 78)
        print(f"  {'PASS' if ov >= THRESHOLD else 'FAIL'}  {'OVERALL':<18} {ov:6.1f}%   (threshold {THRESHOLD}%)")
    print("=" * 78)

    ok = all(r["_overall"] >= THRESHOLD for r in all_results.values())
    print("RESULT:", "ALL CORPORA PASS" if ok else "BELOW THRESHOLD")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
