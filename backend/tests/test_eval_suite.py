"""CI gate for the LexOrch-KG evaluation framework.

Fast hermetic metric units + gold-corpus gates (E1/E3/E4) over the four
GOLD documents. The retrieval suite is exercised as a smoke test and
auto-skips when model weights are unavailable, keeping CI green offline.
"""
# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evals.gold import GOLD, gold_docs, gold_markers  # noqa: E402
from evals.metrics import (  # noqa: E402
    act_matches,
    citation_binding_violations,
    exact_match,
    irac_completeness,
    leakage_scan,
    list_f1,
    mapping_f1,
    mrr,
    ndcg_at_k,
    outcome_accuracy,
    outcome_normalize,
    pair_accuracy,
    precision_at_k,
    recall_at_k,
    self_match_violations,
    verbatim,
)
from scripts.eval_suite import (  # noqa: E402
    chunk_text,
    e1_extraction,
    e3_grounding,
    e4_reasoning,
    load_text,
)

PASS_E1 = 0.90


# --------------------------------------------------------------------------- #
# Metric units
# --------------------------------------------------------------------------- #
def test_exact_match_ignores_whitespace_and_punctuation() -> None:
    assert exact_match("High  Court, of Bombay.", "high court of bombay") == 1.0
    assert exact_match("A vs B", "A v B") == 0.0
    assert exact_match(None, "") == 1.0


def test_list_f1_and_act_matching() -> None:
    assert list_f1(["a", "b"], ["b", "a"]) == 1.0
    assert list_f1(["a"], ["a", "b"]) == pytest.approx(2 / 3)
    assert act_matches("Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023", "BNSS")
    assert act_matches("Indian Contract Act, 1872", "Indian Contract Act")
    assert not act_matches("NDPS Act, 1985", "Indian Contract Act")


def test_mapping_f1_sections() -> None:
    pred = {"482": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023", "111": "BNS Act"}
    gold = {"482": "BNSS", "111": "BNS"}
    assert mapping_f1(pred, gold) == 1.0
    assert mapping_f1({}, {}) == 1.0
    assert mapping_f1({"74": "Indian Contract Act"}, {"O.39 R.1-2": "Code of Civil Procedure"}) == 0.0


def test_pair_accuracy_requires_joint_name_and_citation() -> None:
    gold = {"X v. Y": "(2011) 1 SCC 694"}
    assert pair_accuracy([("X v. Y", "(2011) 1 SCC 694")], gold) == 1.0
    assert pair_accuracy([("X v. Y", "(2014) 10 SCC 473")], gold) == 0.0


def test_ranking_metrics() -> None:
    ranked = [0, 0, 1, 0, 1]
    assert recall_at_k(ranked, 5, total_relevant=2) == 1.0
    assert recall_at_k(ranked, 2, total_relevant=2) == 0.0
    assert precision_at_k(ranked, 5) == 0.4
    assert mrr(ranked) == pytest.approx(1 / 3)
    assert ndcg_at_k([1, 0], 2) == 1.0
    assert ndcg_at_k([0, 1], 2) == pytest.approx(0.63093, abs=1e-4)


def test_verbatim_is_whitespace_insensitive() -> None:
    assert verbatim("The  bail\napplication is allowed.", "bail application is allowed")
    assert not verbatim("short text", "this quote does not exist")


def test_leakage_scan_finds_all_banned_families() -> None:
    report = {"a": {"value": "Not found in document"}, "b": ["Applicable Statutes"], "c": {"d": "keyword"}}
    findings = leakage_scan(report)
    assert len(findings) == 3
    assert leakage_scan({"clean": "perfectly fine output"}) == []


def test_citation_binding_and_self_match() -> None:
    precedents = [
        {"case_name": "A v. B", "citation": "(2011) 1 SCC 694"},
        {"case_name": "C v. D", "citation": "(2011) 1 SCC 694"},
    ]
    assert len(citation_binding_violations(precedents)) == 1
    assert self_match_violations("C v. D", precedents)


def test_irac_completeness_and_outcome() -> None:
    full = {
        "sections": [{"num": "482", "act": "BNSS"}],
        "submissions": {"a": ["x submitted"], "b": []},
        "risk": {"conclusion": "Bail application is allowed."},
    }
    assert irac_completeness(full).score == 1.0
    broken = {"sections": [], "submissions": {}, "risk": {}}
    assert irac_completeness(broken).score < 0.5
    assert outcome_normalize("petition partly allowed with costs") == "partly allowed"
    assert outcome_accuracy("disposed of", "disposed of") == 1.0
    assert outcome_accuracy("dismissed", "allowed") == 0.0


# --------------------------------------------------------------------------- #
# Gold integrity
# --------------------------------------------------------------------------- #
def test_gold_files_exist() -> None:
    for doc in gold_docs():
        assert doc.path.exists(), f"missing gold PDF: {doc.path}"
    assert set(GOLD) == {"vikram", "ananya", "apex", "mehta"}
    for doc in gold_docs():
        assert gold_markers(doc), f"no relevance markers derived for {doc.key}"


def test_chunking_produces_nonempty_windows() -> None:
    text = load_text(gold_docs()[0].path)
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 900 for chunk in chunks)


# --------------------------------------------------------------------------- #
# Corpus gates over the 4 GOLD docs
# --------------------------------------------------------------------------- #
def test_e1_extraction_meets_gate() -> None:
    result = e1_extraction(gold_docs())
    assert result.passed, result.metrics
    assert result.metrics["macro_f1"] >= PASS_E1


def test_e3_grounding_zero_violations() -> None:
    result = e3_grounding(gold_docs())
    assert result.passed, [d["violations"] for d in result.details if d["violations"]]


def test_e4_reasoning_irac_and_outcomes() -> None:
    result = e4_reasoning(gold_docs(), with_llm=False)
    assert result.metrics["irac_avg"] == 1.0
    assert result.metrics["outcome_acc"] >= 0.75
    assert all(d["llm_judge"] is None for d in result.details)


@pytest.mark.slow
def test_retrieval_smoke_hybrid_mrr_gate() -> None:
    weights_ready = (BACKEND_DIR.parent / "models" / "bge-m3").exists()
    if not weights_ready:
        pytest.skip("BGE-M3 weights unavailable; retrieval smoke skipped")
    from scripts.eval_suite import e2_retrieval

    result = e2_retrieval(gold_docs())
    assert isinstance(result.metrics.get("primary_mrr"), float)
