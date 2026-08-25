"""CI-friendly regression suite over the LexOrch-KG batch grounding validators.

The heavy lifting lives in ``scripts/batch_eval.py``; these tests wrap the
exact same validators used by ``python -m scripts.batch_eval``. Pure-logic
tests run hermetically (no corpus needed). Corpus-backed integration tests
auto-skip when ``backend/test_data`` is absent, keeping CI green anywhere.
"""
# ruff: noqa: E501  (embedded judgment-text fixtures must not be re-wrapped)
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.presentation_universal import build_analysis  # noqa: E402
from scripts.batch_eval import (  # noqa: E402
    aggregate_results,
    evaluate_file,
    exit_code_for,
    llm_extra_violations,
    validate_report,
)

TEST_DATA_DIR = BACKEND_DIR / "test_data"

CANONICAL_TEXT = """IN THE HIGH COURT OF JUDICATURE AT BOMBAY
Vikram Dev vs The State Of Maharashtra ... on 14 March, 2024
(2024) 2 Bom CR 412, 2024 Cri LJ 1580
Bench: Revati Mohite Dere, J. and Gauri Godse, J.
JUDGMENT
Revati Mohite Dere, J.
1. The applicant, Vikram Dev, has approached this Court under Section 482 of the Bharatiya Nagarik Suraksha
Sanhita (BNSS), 2023, seeking regular bail in connection with C.R. No. 102 of 2024 registered with Cyber Crime
Police Station, Bandra, Mumbai. The offences alleged against the applicant are punishable under Section 111 of the
Bharatiya Nyaya Sanhita (BNS), 2023 and Section 66D of the Information Technology Act, 2000.
2. The case of the prosecution is that on 15-01-2024, an organized syndicate executed a sophisticated OTP phishing
and corporate SIM-swap scheme resulting in wrongful loss of Rs. 3.8 Crores to a commercial entity. The applicant
was arrested on 22-01-2024 on the allegation that he facilitated logistics and server infrastructure for the prime
conspirators.
3. Mr. Merchant, learned Senior Counsel for the applicant, submitted that the investigation is complete and the charge
sheet has already been filed on 05-03-2024. He contends that the applicant had no mens rea or knowledge of the
phishing fraud. Furthermore, the electronic evidence sought to be relied upon by the prosecution, namely Call Detail
Records (CDR) and cell-site logs, has been obtained without compliance with mandatory statutory certification under
Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023.
4. Counsel for the applicant placed strong reliance on the judgment reported in (2011) 1 SCC 694 in the case of
Sanjay Chandra v. Central Bureau of Investigation, where the Supreme Court settled the principle that bail is the rule
and jail is the exception. He also cited the landmark decision reported in (2014) 10 SCC 473 in the case of Anvar P.V.
v. P.K. Basheer regarding the mandatory nature of electronic evidentiary certificates.
5. On the other hand, the learned APP Ms. Shinde for the State vehemently opposed the bail plea. She argued that
the applicant operated a key logistics conduit under Section 111 of the Bharatiya Nyaya Sanhita (BNS), 2023. She
further pointed out that bank ledger audits and panchanama dated 25-01-2024 establish physical proximity of the
applicant's leased vehicles near cyber operating nodes.
6. We have considered the rival submissions and perused the charge sheet materials. The custodial interrogation of
the applicant has concluded. The main conspirators who received the siphoned funds in offshore accounts remain
absconding. No direct financial transfer has been traced to the applicant's accounts. Continued incarceration would
amount to pre-trial punishment.
7. In view of the above circumstances, the applicant is directed to be released on bail on executing a P.R. Bond of Rs.
50,000/- with one or two local sureties. Bail application is allowed.
Gauri Godse, J. - I agree."""


@pytest.fixture(scope="module")
def canonical_report() -> dict:
    """A realistic analysis report that must satisfy every validator."""
    return build_analysis(CANONICAL_TEXT)


def _codes(report: dict, stem: str = "01_Cybercrime_Bail_Vikram_Dev") -> list[str]:
    return [v.code for v in validate_report(report, stem, f"{stem}.pdf")]


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #
def test_canonical_document_passes_all_rules(canonical_report: dict) -> None:
    assert _codes(canonical_report) == []


def test_llm_checks_pass_on_canonical_document(canonical_report: dict) -> None:
    violations, stats = llm_extra_violations(CANONICAL_TEXT, canonical_report)
    codes = [v.code for v in violations]
    assert "L01" not in codes
    assert stats["issues"] > 0
    assert stats["quotes"] > 0
    assert stats["ungrounded_quotes"] == 0


# --------------------------------------------------------------------------- #
# Per-rule mutations
# --------------------------------------------------------------------------- #
def test_v02_banned_string_detected_in_nested_values(canonical_report: dict) -> None:
    mutated = dict(canonical_report)
    mutated["metadata"] = {**canonical_report["metadata"]}
    mutated["metadata"]["court"] = {"value": "Not found in document", "status": "extracted"}
    mutated["kg"] = {"nodes": [{"id": "x", "type": "Case", "label": "Mock summary"}], "edges": []}
    codes = _codes(mutated)
    assert codes.count("V02") >= 2


def test_v03_case_title_must_not_render_filename(canonical_report: dict) -> None:
    stem = "600_Criminal_NDPS_Bail_Sai_Desai"
    leaky = {
        **canonical_report,
        "metadata": {
            **canonical_report["metadata"],
            "case_title": {"value": stem, "status": "extracted"},
        },
    }
    assert "V03" in [v.code for v in validate_report(leaky, stem, f"{stem}.pdf")]

    empty = {
        **canonical_report,
        "metadata": {**canonical_report["metadata"], "case_title": {"value": None, "status": "not_found"}},
    }
    assert "V03" in _codes(empty)


def test_v04_metadata_status_whitelist(canonical_report: dict) -> None:
    mutated = {
        **canonical_report,
        "metadata": {
            **canonical_report["metadata"],
            "court": {"value": "High Court", "status": "guessed"},
        },
    }
    assert "V04" in _codes(mutated)


@pytest.mark.parametrize("bad_trust", [100, 39, "92", None])
def test_v05_trust_score_bounds(canonical_report: dict, bad_trust) -> None:
    assert "V05" in _codes({**canonical_report, "trust_score": bad_trust})


def test_v06_timeline_rules(canonical_report: dict) -> None:
    assert "V06" in _codes({**canonical_report, "timeline": []})
    stale_tail = [dict(canonical_report["timeline"][-1], date="01 January 1999")]
    mutated = {**canonical_report, "timeline": [*canonical_report["timeline"][:-1], *stale_tail]}
    assert "V06" in _codes(mutated)


def test_v07_statutes_need_formatted_display(canonical_report: dict) -> None:
    raw_dict = [{**canonical_report["sections"][0]}]
    raw_dict[0]["display"] = "Section 482 BNSS"
    assert "V07" in _codes({**canonical_report, "sections": raw_dict})
    assert "V07" in _codes({**canonical_report, "sections": ["Section 482"]})


def test_v08_precedent_guards(canonical_report: dict) -> None:
    title_value = canonical_report["metadata"]["case_title"]["value"]
    self_match = [
        {"case_name": title_value, "citation": "(2011) 1 SCC 694", "year": "2011", "summary": "s"}
    ]
    assert "V08" in _codes({**canonical_report, "precedents": self_match})

    shared_citation = [
        {"case_name": "Alpha A v. Beta B", "citation": "(2011) 1 SCC 694", "year": "2011", "summary": "s"},
        {"case_name": "Gamma C v. Delta D", "citation": "(2011) 1 SCC 694", "year": "2011", "summary": "s"},
    ]
    assert "V08" in _codes({**canonical_report, "precedents": shared_citation})

    junk_name = [{"case_name": "keyword", "citation": "(2010) 1 SCC 1", "year": "2010", "summary": "s"}]
    assert "V08" in _codes({**canonical_report, "precedents": junk_name})

    over_similar = [
        {"case_name": "Alpha A v. Beta B", "citation": "(2011) 1 SCC 694", "similarity": 137}
    ]
    assert "V08" in _codes({**canonical_report, "precedents": over_similar})


def test_v09_unknown_category_rejected(canonical_report: dict) -> None:
    assert "V09" in _codes({**canonical_report, "category": "tax"})


def test_v10_category_sections_and_labels(canonical_report: dict) -> None:
    wrong_labels = {**canonical_report, "labels": ["Foo Submissions", "Bar Case"]}
    assert "V10" in _codes(wrong_labels)

    empty_submissions = {
        **canonical_report,
        "submissions": {"a": [], "b": []},
    }
    assert "V10" in _codes(empty_submissions)

    empty_conclusion = {
        **canonical_report,
        "risk": {**canonical_report["risk"], "conclusion": ""},
    }
    assert "V10" in _codes(empty_conclusion)


def test_llm_l02_and_l03_flags(canonical_report: dict) -> None:
    no_verb = {**canonical_report, "risk": {**canonical_report["risk"], "conclusion": "Matter adjourned."}}
    violations, _ = llm_extra_violations(CANONICAL_TEXT, no_verb)
    assert any(v.code == "L02" for v in violations)

    with_allowed = {
        **canonical_report,
        "risk": {**canonical_report["risk"], "conclusion": "Bail application is allowed."},
    }
    violations, _ = llm_extra_violations(CANONICAL_TEXT, with_allowed)
    assert not any(v.code == "L02" for v in violations)

    ungrounded_risk = {
        **canonical_report,
        "risk": {**canonical_report["risk"], "strengths": ["The moon was lit during the hearing."]},
    }
    violations, stats = llm_extra_violations(CANONICAL_TEXT, ungrounded_risk)
    assert any(v.code == "L03" for v in violations)
    assert stats["ungrounded_quotes"] >= 1


# --------------------------------------------------------------------------- #
# Aggregation + exit policy
# --------------------------------------------------------------------------- #
def _result(name: str, parsed: bool = True, codes: tuple[str, ...] = ()) -> dict:
    return {
        "file": name,
        "parsed": parsed,
        "engine": "",
        "pages": 1,
        "category": "criminal_bail",
        "trust_score": 90,
        "coverage": 1.0,
        "status_counts": {"extracted": 9},
        "violations": [{"code": c, "message": f"{c} triggered"} for c in codes],
        "error": None if parsed else "boom",
        "duration_ms": 1,
        "llm_checked": False,
    }


def test_exit_code_clean_batch_passes() -> None:
    summary = aggregate_results([_result("a.pdf"), _result("b.pdf"), _result("c.pdf")])
    assert summary.pass_rate == 1.0
    assert exit_code_for(summary) == 0


def test_exit_code_low_pass_rate_fails() -> None:
    results = [_result(f"f{i}.pdf") for i in range(18)] + [_result("bad.pdf", codes=("V10",))]
    results += [_result("worse.pdf", codes=("V06",))]
    summary = aggregate_results(results)
    assert summary.parsed == 20 and summary.parse_fail == 0
    assert summary.pass_rate < 0.95
    assert exit_code_for(summary) == 1


def test_exit_code_threshold_is_inclusive_at_95_percent() -> None:
    results = [_result(f"f{i}.pdf") for i in range(19)] + [_result("bad.pdf", codes=("V10",))]
    summary = aggregate_results(results)
    assert summary.pass_rate == pytest.approx(0.95)
    assert exit_code_for(summary) == 0


def test_exit_code_hard_violation_fails_even_at_full_rate() -> None:
    results = [_result(f"g{i}.pdf") for i in range(50)]
    results.append(_result("leak.pdf", codes=("V02",)))
    summary = aggregate_results(results)
    assert summary.pass_rate > 0.95
    assert exit_code_for(summary) == 1


def test_parse_failures_excluded_from_rate_but_counted() -> None:
    results = [_result(f"h{i}.pdf") for i in range(9)] + [_result("broken.pdf", parsed=False)]
    summary = aggregate_results(results)
    assert summary.total == 10 and summary.parsed == 9 and summary.parse_fail == 1
    assert summary.pass_rate == 1.0


# --------------------------------------------------------------------------- #
# End-to-end pipeline (hermetic txt + optional real corpus)
# --------------------------------------------------------------------------- #
def test_evaluate_file_txt_with_cache_resume(tmp_path: Path) -> None:
    doc = tmp_path / "01_Cybercrime_Bail_Vikram_Dev.txt"
    doc.write_text(CANONICAL_TEXT, encoding="utf-8")
    cache_dir = tmp_path / ".cache" / "eval"

    first = evaluate_file(doc, cache_dir)
    assert first.parsed and first.engine.startswith(("DocumentParser/", "fallback/"))
    assert [v.code for v in first.violations] == []

    second = evaluate_file(doc, cache_dir)
    assert second.violations == first.violations
    assert second.category == first.category == "criminal_bail"
    assert (cache_dir / "*.json") and list(cache_dir.glob("*.json"))


@pytest.mark.skipif(not TEST_DATA_DIR.exists(), reason="corpus test_data/ not present")
def test_real_corpus_sample_is_grounding_clean() -> None:
    pdfs = sorted(TEST_DATA_DIR.glob("*.pdf"))[:4]
    assert pdfs, "expected at least one PDF in test_data/"
    for pdf in pdfs:
        result = evaluate_file(pdf)
        assert result.parsed, f"{pdf.name} failed to parse: {result.error}"
        hard = [v for v in result.violations if v.code in {"V02", "V03", "V08"}]
        assert not hard, f"{pdf.name}: {[asdict_hard(v) for v in hard]}"


def asdict_hard(violation) -> str:
    return f"{violation.code}: {violation.message}"
