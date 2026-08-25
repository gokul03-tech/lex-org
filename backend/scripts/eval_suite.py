"""LexOrch-KG complete evaluation suite runner (8 evaluation types).

Suites:
    E1 extraction   - per-field extraction accuracy vs GOLD (F1 >= 0.90)
    E2 retrieval    - Recall@5/P@5/MRR/nDCG@10 over gold qrels, 4 configs
    E3 grounding    - leakage scan + verbatim quotes + citation binding
    E4 reasoning    - IRAC completeness + outcome accuracy (+ optional judge)
    E5 human        - printable human_eval_pack.md (fact-checks/Likert/SUS)
    E6 performance  - p50/p95 per pipeline stage, docs/min throughput
    E7 robustness   - --dir: 600-doc batch pass rate; else leave-one-out
    E8 ablation     - component-off delta table (kg/gate/bm25/vector/reranker)

Usage (from backend/):
    python -m scripts.eval_suite --suite all
    python -m scripts.eval_suite --suite all --dir ./test_data --workers 8

Exit 0 iff E1 F1 >= 0.90 AND E3 violations == 0 AND E2 MRR >= 0.8 AND
(E7 >= 0.95 when --dir was given).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None

from loguru import logger

from evals.gold import GOLD, TEST_DATA_DIR, gold_docs, gold_markers
from evals.metrics import (
    act_matches,
    aggregate_ranking,
    citation_binding_violations,
    exact_match,
    irac_completeness,
    leakage_scan,
    list_f1,
    mapping_f1,
    mrr,
    ndcg_at_k,
    norm_text,
    outcome_accuracy,
    outcome_normalize,
    pair_accuracy,
    precision_at_k,
    recall_at_k,
    self_match_violations,
    verbatim,
    ws_norm,
)
from app.agents.presentation_universal import (
    LABELS,
    build_analysis,
    build_kg,
    bind_sections,
    detect_category,
    extract_evidence,
    extract_metadata,
    extract_precedents,
    extract_submissions,
)
from app.document_pipeline.parser import DocumentParser
from app.agents.presentation_universal import build_timeline, build_risk

REPORTS_DIR = Path("./reports")
PASS_E1_F1 = 0.90
PASS_E2_MRR = 0.80
PASS_E7_RATE = 0.95


# --------------------------------------------------------------------------- #
# Result containers
# --------------------------------------------------------------------------- #
@dataclass
class SuiteResult:
    """Outcome of one evaluation suite."""

    suite: str
    passed: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)
    details: list[dict[str, Any]] = field(default_factory=list)

    def chip(self) -> str:
        return "PASS" if self.passed else "FAIL"


def load_text(path: Path) -> str:
    """Parse one gold PDF through the production parser."""
    return DocumentParser().parse(path, mime_type="application/pdf")["text"]


def analyze_with_stages(text: str) -> tuple[dict[str, Any], dict[str, float]]:
    """Run the deterministic builder once per stage, returning timings."""
    from app.agents.presentation_universal import calibrate, gate

    timings: dict[str, float] = {}

    def timed(name: str, fn, *args):
        start = time.perf_counter()
        out = fn(*args)
        timings[name] = (time.perf_counter() - start) * 1000
        return out

    meta = timed("metadata", extract_metadata, text)
    secs = timed("sections", bind_sections, text)
    precs = timed("precedents", extract_precedents, text)
    subs_a, subs_b = timed("submissions", extract_submissions, text)
    evi = timed("evidence", extract_evidence, text)
    tl = timed("timeline", build_timeline, text, meta["decision_date"]["value"])
    risk = timed("risk", build_risk, text, subs_a, subs_b)
    cat = detect_category(text)
    report = {
        "category": cat,
        "procedural_stage": cat,
        "labels": list(LABELS[cat]),
        "metadata": meta,
        "sections": secs,
        "precedents": precs,
        "evidence": evi,
        "timeline": tl,
        "submissions": {"a": subs_a, "b": subs_b},
        "risk": risk,
        "articles": sorted(set(re.findall(r"Article\s+(\d+(?:\([\w]+\))?)", text))),
    }
    report["kg"] = timed("kg", build_kg, meta, secs, precs, evi)
    report["trust_score"] = calibrate(meta, precs, tl)
    report = timed("gate", gate, report, text)
    return report, timings


def build_report(text: str) -> tuple[dict[str, Any], dict[str, float]]:
    """Production single-call path plus coarse end-to-end timing."""
    start = time.perf_counter()
    report = build_analysis(text)
    return report, {"report_total_ms": (time.perf_counter() - start) * 1000}


# --------------------------------------------------------------------------- #
# E1 EXTRACTION
# --------------------------------------------------------------------------- #
def _meta_value(report: dict[str, Any], key: str) -> Any:
    value = (report.get("metadata") or {}).get(key)
    return value.get("value") if isinstance(value, dict) else value


def e1_extraction(docs: list) -> SuiteResult:
    """Per-field exact/F1 comparison of pipeline output against GOLD."""
    result = SuiteResult("E1_extraction")
    field_rows: list[dict[str, float]] = []
    section_scores: list[float] = []
    article_scores: list[float] = []
    precedent_scores: list[float] = []

    for doc in docs:
        report, _ = build_report(load_text(doc.path))
        meta = report.get("metadata") or {}
        pred_judges = _meta_value(report, "judges") or _meta_value(report, "presiding_judges") or []
        pred_citations = _meta_value(report, "citation_numbers") or []

        row = {
            "court": exact_match(_meta_value(report, "court"), doc.court),
            "petitioner": exact_match(_meta_value(report, "petitioner"), doc.petitioner),
            "respondent": exact_match(
                ws_norm(_meta_value(report, "respondent")).rstrip("."), ws_norm(doc.respondent)
            ),
            "decision_date": exact_match(_meta_value(report, "decision_date"), doc.decision_date),
            "case_number": exact_match(_meta_value(report, "case_number"), doc.case_number),
            "category": exact_match(report.get("category"), doc.category),
            "judges_f1": list_f1(pred_judges, doc.judges),
            "citations_f1": list_f1(pred_citations, doc.citations),
            "timeline_recall": (
                list_f1(
                    [t.get("date") for t in report.get("timeline") or [] if t.get("date")],
                    doc.timeline,
                )
                if doc.timeline
                else 1.0
            ),
        }
        section_scores.append(mapping_f1({s["num"]: s["act"] for s in report.get("sections") or []}, doc.sections))
        article_scores.append(list_f1(report.get("articles") or [], doc.articles))
        precedent_scores.append(pair_accuracy(
            [(p.get("case_name"), p.get("citation")) for p in report.get("precedents") or []],
            doc.precedents,
        ))
        row["sections_f1"] = section_scores[-1]
        row["articles_f1"] = article_scores[-1]
        row["precedents_acc"] = precedent_scores[-1]
        field_rows.append(row)
        result.details.append({"doc": doc.key, **{k: round(v, 3) for k, v in row.items()}})

    micro_keys = [k for k in field_rows[0] if k not in ("sections_f1", "articles_f1", "precedents_acc")]
    micro_p = sum(sum(r[k] for k in micro_keys) for r in field_rows)
    micro_total = len(field_rows) * len(micro_keys)
    macro_vals = [sum(r[k] for r in field_rows) / len(field_rows) for k in field_rows[0]]
    extra = [statistics.mean(section_scores), statistics.mean(article_scores), statistics.mean(precedent_scores)]
    macro_f1 = (sum(macro_vals) + sum(extra)) / (len(macro_vals) + len(extra))
    result.metrics = {
        "micro_exact": round(micro_p / micro_total, 4),
        "macro_f1": round(macro_f1, 4),
        "sections_f1": round(statistics.mean(section_scores), 4),
        "articles_f1": round(statistics.mean(article_scores), 4),
        "precedents_pair_acc": round(statistics.mean(precedent_scores), 4),
    }
    result.passed = result.metrics["macro_f1"] >= PASS_E1_F1
    return result


# --------------------------------------------------------------------------- #
# E2 RETRIEVAL
# --------------------------------------------------------------------------- #
CHUNK_CHARS = 700


def chunk_text(text: str) -> list[str]:
    """Split normalized text into ~CHUNK_CHARS windows at sentence bounds."""
    clean = ws_norm(text)
    sentences = re.split(r"(?<=[a-z])\.\s+", clean)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > CHUNK_CHARS and current:
            chunks.append(current.strip())
            current = ""
        current += sentence + ". "
    if current.strip():
        chunks.append(current.strip())
    return chunks or [clean]


def _relevant(chunk: str, markers: list[str]) -> bool:
    low = ws_norm(chunk).casefold()
    return any(ws_norm(marker).casefold() in low for marker in markers)


async def _run_retrieval_configs(docs: list, configs: list[str]) -> dict[str, dict[str, Any]]:
    """Index gold chunks and evaluate each retrieval configuration."""
    from app.embeddings.bge_m3 import get_bge_m3
    from app.rag.merger import ResultMerger
    from app.rag.retrievers.keyword_search import KeywordRetriever
    from app.rag.reranker import CrossEncoderReranker

    corpus: list[dict[str, Any]] = []
    relevance_by_chunk: dict[int, set[int]] = {}
    queries: list[tuple[str, str, list[str]]] = []
    for doc_index, doc in enumerate(docs):
        chunks = chunk_text(load_text(doc.path))
        markers = gold_markers(doc)
        base = len(corpus)
        for offset, chunk in enumerate(chunks):
            corpus.append({"text": chunk, "metadata": {"chunk_id": base + offset}})
            if _relevant(chunk, markers):
                relevance_by_chunk.setdefault(doc_index, set()).add(base + offset)
        queries.append((doc.key, ws_norm(load_text(doc.path))[:1500], markers))

    keyword = KeywordRetriever()
    keyword.index(corpus)
    embedder = get_bge_m3()
    vectors = embedder.encode_documents([c["text"] for c in corpus])
    norms = (vectors ** 2).sum(axis=1, keepdims=True) ** 0.5
    unit_vectors = vectors / (norms + 1e-9)
    merger = ResultMerger()

    def vector_search(query: str, top_k: int) -> list[dict[str, Any]]:
        qvec = embedder.encode_queries([query])
        qunit = qvec[0] / ((qvec ** 2).sum() ** 0.5 + 1e-9)
        scores = unit_vectors @ qunit
        order = scores.argsort()[::-1][:top_k]
        return [
            {"text": corpus[i]["text"][:500], "score": float(scores[i]), "source": "vector",
             "metadata": {"chunk_id": corpus[i]["metadata"]["chunk_id"]}}
            for i in order
        ]

    async def keyword_search(query: str, top_k: int) -> list[dict[str, Any]]:
        results = await keyword.search(query, top_k=top_k)
        for r in results:
            r.setdefault("metadata", {})
        return results

    def resolve_ids(results: list[dict[str, Any]]) -> list[int]:
        return [(r.get("metadata") or {}).get("chunk_id", -1) for r in results]

    reranker = CrossEncoderReranker() if "hybrid_rerank" in configs else None
    output: dict[str, dict[str, Any]] = {}
    for config in configs:
        rows = []
        for key, query, _markers in queries:
            target = int(key and 0) or [d.key for d in docs].index(key)
            relevant = relevance_by_chunk.get(target, set())

            def rel_list(ids: list[int]) -> list[int]:
                return [1 if cid in relevant else 0 for cid in ids]

            if config == "bm25_only":
                ranked = rel_list(resolve_ids(asyncio.run(keyword_search(query, 10))))
            elif config == "vector_only":
                ranked = rel_list(resolve_ids(vector_search(query, 10)))
            elif config == "hybrid_rrf":
                merged = merger.merge([
                    asyncio.run(keyword_search(query, 10)),
                    vector_search(query, 10),
                ])
                ranked = rel_list(resolve_ids(merged))
            else:
                merged = merger.merge([
                    asyncio.run(keyword_search(query, 20)),
                    vector_search(query, 20),
                ])
                if reranker is not None:
                    merged = reranker.rerank(query, merged, top_k=10)
                else:
                    merged = sorted(merged, key=lambda r: r.get("score", 0.0), reverse=True)[:10]
                ranked = rel_list(resolve_ids(merged))

            rows.append({
                "recall_at_5": recall_at_k(ranked, 5, total_relevant=len(relevant)),
                "precision_at_5": precision_at_k(ranked, 5),
                "mrr": mrr(ranked),
                "ndcg_at_10": ndcg_at_k(ranked, 10),
            })
        agg = aggregate_ranking(rows)
        output[config] = {
            "recall_at_5": round(agg.recall_at_5, 4),
            "precision_at_5": round(agg.precision_at_5, 4),
            "mrr": round(agg.mrr, 4),
            "ndcg_at_10": round(agg.ndcg_at_10, 4),
        }
    return output


def e2_retrieval(docs: list) -> SuiteResult:
    """Recall@5 / P@5 / MRR / nDCG@10 across four retrieval configurations."""
    result = SuiteResult("E2_retrieval")
    try:
        configs = asyncio.run(_run_retrieval_configs(docs, ["bm25_only", "vector_only", "hybrid_rrf", "hybrid_rerank"]))
    except Exception as exc:
        logger.opt(exception=True).warning(f"E2 retrieval failed: {exc}")
        configs = {}
        result.passed = False
        result.metrics = {"error": str(exc)[:200]}
        return result
    result.metrics = configs
    primary = configs.get("hybrid_rerank") or next(iter(configs.values()), {})
    result.passed = primary.get("mrr", 0.0) >= PASS_E2_MRR
    return result


# --------------------------------------------------------------------------- #
# E3 GROUNDING
# --------------------------------------------------------------------------- #
def e3_grounding(docs: list) -> SuiteResult:
    """Leakage, verbatim quotes, citation binding, trust bounds per gold doc."""
    result = SuiteResult("E3_grounding")
    total_violations = 0
    for doc in docs:
        text = load_text(doc.path)
        report, _ = build_report(text)
        findings = leakage_scan(report)
        evidence_quotes = [str(e.get("detail")) for e in report.get("evidence") or [] if e.get("detail")]
        timeline_quotes = [str(t.get("fact")) for t in report.get("timeline") or [] if t.get("fact")]
        ungrounded = [q for q in evidence_quotes + timeline_quotes if not verbatim(text, q)]
        title = _meta_value(report, "case_title") or ""
        violations = findings + [f"ungrounded quote: {q[:70]}" for q in ungrounded]
        violations += citation_binding_violations(report.get("precedents") or [])
        violations += self_match_violations(title, report.get("precedents") or [])
        trust = report.get("trust_score")
        if not isinstance(trust, (int, float)) or not 40 <= trust <= 99:
            violations.append(f"trust_score out of range: {trust!r}")
        total_violations += len(violations)
        result.details.append({
            "doc": doc.key,
            "violations": violations,
            "count": len(violations),
            "trust": trust,
        })
    result.metrics = {"total_violations": total_violations}
    result.passed = total_violations == 0
    return result


# --------------------------------------------------------------------------- #
# E4 REASONING
# --------------------------------------------------------------------------- #
def e4_reasoning(docs: list, with_llm: bool = False) -> SuiteResult:
    """IRAC completeness, outcome vs GOLD.outcome, label-vs-category checks."""
    result = SuiteResult("E4_reasoning")
    outcomes: list[float] = []
    labels_ok = 0
    for doc in docs:
        report, _ = build_report(load_text(doc.path))
        irac = irac_completeness(report)
        predicted = outcome_normalize(str((report.get("risk") or {}).get("conclusion") or ""))
        acc = outcome_accuracy(predicted, doc.outcome)
        outcomes.append(acc)
        label_ok = list(LABELS.get(report.get("category"), [])) == [str(x) for x in report.get("labels") or []]
        labels_ok += label_ok
        llm_scores: dict[str, Any] | None = None
        if with_llm:
            llm_scores = _llm_judge(load_text(doc.path), report)
        result.details.append({
            "doc": doc.key,
            "irac": irac.as_dict(),
            "predicted_outcome": predicted,
            "gold_outcome": doc.outcome,
            "outcome_correct": bool(acc),
            "labels_ok": label_ok,
            "llm_judge": llm_scores,
        })
    result.metrics = {
        "irac_avg": round(statistics.mean(
            d["irac"]["score"] for d in result.details
        ), 4),
        "outcome_acc": round(statistics.mean(outcomes), 4),
        "label_acc": round(labels_ok / len(docs), 4),
    }
    result.passed = result.metrics["irac_avg"] == 1.0 and result.metrics["outcome_acc"] >= 0.75
    return result


def _llm_judge(text: str, report: dict[str, Any]) -> dict[str, Any] | None:
    """Optional LLM-as-Judge (temp 0, rubric 1-5) via configured provider."""
    try:
        from app.llm.provider import get_llm_provider

        provider = get_llm_provider()
        prompt = (
            "Rate this legal analysis 1-5 each for groundedness, completeness, "
            "legal soundness, clarity. Reply as JSON.\n\nANALYSIS:\n"
            f"{json.dumps({k: v for k, v in report.items() if k != 'kg'}, default=str)[:4000]}"
        )
        raw = provider.generate(prompt, max_tokens=256, temperature=0.0)
        numbers = re.findall(r'"(?:groundedness|completeness|legal soundness|clarity)"\s*:\s*([1-5])', raw)
        dims = ["groundedness", "completeness", "soundness", "clarity"]
        return {dim: int(score) for dim, score in zip(dims, numbers)} or {"raw": raw[:120]}
    except Exception as exc:
        return {"error": str(exc)[:120]}


# --------------------------------------------------------------------------- #
# E5 HUMAN PACK
# --------------------------------------------------------------------------- #
FACT_TEMPLATES = [
    ("Which court decided {pet} vs {resp}?", "{court}"),
    ("Who was the petitioner in {file}?", "{petitioner}"),
    ("On which date was {key} decided?", "{decision_date}"),
    ("What was the outcome of {key}?", "{outcome}"),
    ("Name one judge on the bench of {key}.", "{judges}"),
]


def e5_human_pack(out_dir: Path) -> SuiteResult:
    """Generate the printable human evaluation pack (fact-checks/SUS)."""
    result = SuiteResult("E5_human_pack")
    lines = [
        "# LexOrch-KG Human Evaluation Pack",
        "",
        "**Evaluators:** 2-3 legal reviewers. Time budget ~15 min/document.",
        "Score each answer sheet independently; do not discuss before submitting.",
        "",
        "## Part A - Fact-check questions (answer from the PDF, then compare)",
        "",
    ]
    for doc in gold_docs():
        data = doc.data
        lines.append(f"### Document: {data['file']} (`{doc.key}`)")
        lines.append("")
        answers = {
            "pet": data["petitioner"], "resp": data["respondent"], "court": data["court"],
            "file": data["file"], "key": doc.key, "decision_date": data["decision_date"],
            "outcome": data["outcome"],
            "judges": ", ".join(data["judges"][:1]),
        }
        for index, (question_tmpl, answer_key) in enumerate(FACT_TEMPLATES, start=1):
            question = question_tmpl.format(**answers)
            gold_answer = answers[answer_key]
            lines += [
                f"**Q{index}. {question}**",
                "",
                "<details><summary>Gold answer</summary>",
                "",
                f"{gold_answer}",
                "",
                "</details>",
                "",
            ]
        lines += ["---", ""]
    lines += [
        "## Part B - System output rating (per document, 5-point Likert)",
        "",
        "| Dimension | 1 | 2 | 3 | 4 | 5 |",
        "|---|---|---|---|---|---|",
        "| Groundedness (every claim traceable to source) | | | | | |",
        "| Completeness (all material facts captured) | | | | | |",
        "| Legal soundness (correct statutes/outcome) | | | | | |",
        "| Clarity (usable by a practising advocate) | | | | | |",
        "",
        "## Part C - System Usability Scale (SUS)",
        "",
        "Rate 1 (strongly disagree) to 5 (strongly agree):",
        "",
    ]
    sus_items = [
        "I think that I would like to use this system frequently.",
        "I found the system unnecessarily complex.",
        "I thought the system was easy to use.",
        "I think that I would need the support of a technical person to use this system.",
        "I found the various functions in this system were well integrated.",
        "I thought there was too much inconsistency in this system.",
        "I would imagine that most people would learn to use this system very quickly.",
        "I found the system very cumbersome to use.",
        "I felt very confident using the system.",
        "I needed to learn a lot of things before I could get going with this system.",
    ]
    lines += [f"{index}. {item}  `[ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ]`" for index, item in enumerate(sus_items, 1)]
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_path = out_dir / "human_eval_pack.md"
    pack_path.write_text("\n".join(lines), encoding="utf-8")
    result.metrics = {"pack_path": str(pack_path), "docs": len(GOLD)}
    result.passed = True
    return result


# --------------------------------------------------------------------------- #
# E6 PERFORMANCE
# --------------------------------------------------------------------------- #
def e6_performance(docs: list) -> SuiteResult:
    """p50/p95 latency per pipeline stage plus docs/min throughput."""
    result = SuiteResult("E6_performance")
    samples: dict[str, list[float]] = {}
    rss_start = _rss_mb()
    totals: list[float] = []
    for doc in docs * 3:
        parse_start = time.perf_counter()
        text = load_text(doc.path)
        _, timings = analyze_with_stages(text)
        timings["parse"] = (time.perf_counter() - parse_start) * 1000
        for stage, ms in timings.items():
            samples.setdefault(stage, []).append(ms)
        totals.append(sum(timings.values()))
    percentiles = {
        stage: {
            "p50_ms": round(statistics.median(values), 1),
            "p95_ms": round(sorted(values)[max(0, int(0.95 * len(values)) - 1)], 1),
        }
        for stage, values in samples.items()
    }
    docs_per_min = 60000 / statistics.mean(totals) if totals else 0.0
    result.metrics = {
        "stages": percentiles,
        "docs_per_min": round(docs_per_min, 1),
        "avg_total_ms": round(statistics.mean(totals), 1),
        "rss_delta_mb": round(_rss_mb() - rss_start, 1),
    }
    result.passed = docs_per_min >= 10
    return result


def _rss_mb() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


# --------------------------------------------------------------------------- #
# E7 ROBUSTNESS
# --------------------------------------------------------------------------- #
CATEGORY_CUE_PATTERNS: dict[str, str] = {
    "criminal_bail": (
        r"\b(?:regular bail|anticipatory bail|bail application|admitted to bail|"
        r"released on bail|seeking bail|bail plea)\b"
    ),
    "writ": r"\b(?:article 32|article 226|writ petition|fundamental right|mandamus|habeas corpus)\b",
    "arbitration": r"\b(?:arbitration and conciliation|arbitral award|arbitral tribunal|sole arbitrator)\b",
    "civil": r"\b(?:specific performance|agreement to sell|sale deed|civil appeal|civil suit|injunction)\b",
    "criminal_trial": r"\b(?:conviction|sentenced|charge sheet|ndps|contraband)\b",
}


def e7_robustness(args_dir: str | None, workers: int = 8) -> SuiteResult:
    """--dir mode: full-corpus pass rate (reuses batch_eval machinery).

    Without --dir: leave-one-category-out cue masking over GOLD docs.
    """
    result = SuiteResult("E7_robustness")
    if args_dir:
        from scripts.batch_eval import (
            _load_cache,
            _worker,
            aggregate_results,
            discover_files,
            file_sha1,
        )

        root = Path(args_dir).resolve()
        files = discover_files(root)
        cache_dir = Path(".cache/eval")
        payloads, cached = [], []
        for path in files:
            if _load_cache(cache_dir, file_sha1(path)) is None:
                payloads.append((str(path), str(cache_dir)))
        results = [asdict(_load_cache(cache_dir, file_sha1(p))) for p in files
                   if _load_cache(cache_dir, file_sha1(p)) is not None]
        progress = tqdm(total=len(payloads), desc="E7-batch", unit="doc") if tqdm else None
        computed = []
        if payloads:
            with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = [pool.submit(_worker, payload) for payload in payloads]
                for future in as_completed(futures):
                    computed.append(future.result())
                    if progress:
                        progress.update(1)
        if progress:
            progress.close()
        all_results = results + computed
        summary = aggregate_results(all_results)
        categories = Counter()
        unknown = []
        for entry in all_results:
            category = entry.get("category")
            if category:
                categories[category] += 1
                if category not in LABELS:
                    unknown.append(category)
        result.metrics = {
            "mode": "corpus",
            "files": summary.total,
            "parsed": summary.parsed,
            "pass_rate": round(summary.pass_rate, 4),
            "categories": dict(categories),
            "unknown_categories": sorted(set(unknown)),
            "top_violations": summary.top_violations[:10],
        }
        result.passed = summary.pass_rate >= PASS_E7_RATE and summary.hard_violations == {}
        return result

    masked_correct = 0
    total_checks = 0
    for hidden_category, pattern in CATEGORY_CUE_PATTERNS.items():
        for doc in gold_docs():
            text = ws_norm(load_text(doc.path))
            masked = re.sub(pattern, "matter", text, flags=re.IGNORECASE)
            for candidate in CATEGORY_CUE_PATTERNS:
                masked = re.sub(CATEGORY_CUE_PATTERNS[candidate], "matter", masked, flags=re.IGNORECASE)
            detected = detect_category(masked)
            total_checks += 1
            masked_correct += detected != hidden_category
    result.metrics = {
        "mode": "leave_one_type_out",
        "docs": len(GOLD),
        "cue_masked_detection_changes": masked_correct,
        "total_probes": total_checks,
    }
    result.passed = True
    return result


# --------------------------------------------------------------------------- #
# E8 ABLATION
# --------------------------------------------------------------------------- #
ABLATION_CONFIGS = ("full", "no_kg", "no_gate", "no_bm25", "no_vector", "no_reranker")


def e8_ablation(docs: list) -> SuiteResult:
    """Component-off deltas for E1 F1 / E2 MRR / E3 violations."""
    result = SuiteResult("E8_ablation")
    from app.rag.merger import ResultMerger
    from app.rag.retrievers.keyword_search import KeywordRetriever

    reports: dict[str, dict[str, Any]] = {}
    for doc in docs:
        reports[doc.key] = build_report(load_text(doc.path))[0]

    def field_f1_for(report: dict[str, Any], doc) -> float:
        scores = [
            exact_match(_meta_value(report, "court"), doc.court),
            exact_match(_meta_value(report, "petitioner"), doc.petitioner),
            exact_match(_meta_value(report, "respondent"), doc.respondent),
            list_f1(_meta_value(report, "judges") or [], doc.judges),
            mapping_f1({s["num"]: s["act"] for s in report.get("sections") or []}, doc.sections),
        ]
        return statistics.mean(scores)

    base_rows = []
    for config in ABLATION_CONFIGS:
        e1_scores, violation_counts = [], []
        for doc in docs:
            original = reports[doc.key]
            report = json.loads(json.dumps(original, default=str))
            if config == "no_kg":
                report.pop("kg", None)
            elif config == "no_gate":
                report["metadata"] = extract_metadata(load_text(doc.path))
            e1_scores.append(field_f1_for(report, doc))
            violation_counts.append(len(leakage_scan(report)))
        base_rows.append({
            "config": config,
            "field_f1": round(statistics.mean(e1_scores), 4),
            "violations": sum(violation_counts),
        })

    try:
        retrieval = asyncio.run(_run_retrieval_configs(
            docs,
            ["bm25_only", "vector_only", "hybrid_rrf", "hybrid_rerank"],
        ))
    except Exception as exc:  # pragma: no cover - retrieval env dependent
        logger.warning(f"E8 retrieval leg skipped: {exc}")
        retrieval = {}
    mrr_by_config = {
        "full": retrieval.get("hybrid_rerank", {}).get("mrr"),
        "no_bm25": retrieval.get("vector_only", {}).get("mrr"),
        "no_vector": retrieval.get("bm25_only", {}).get("mrr"),
        "no_reranker": retrieval.get("hybrid_rrf", {}).get("mrr"),
        "no_kg": retrieval.get("hybrid_rerank", {}).get("mrr"),
        "no_gate": retrieval.get("hybrid_rerank", {}).get("mrr"),
    }
    for row in base_rows:
        row["mrr"] = mrr_by_config.get(row["config"])

    full_row = next(row for row in base_rows if row["config"] == "full")
    deltas = []
    for row in base_rows:
        deltas.append({
            "config": row["config"],
            "field_f1_delta": round(row["field_f1"] - full_row["field_f1"], 4),
            "mrr_delta": (
                round(row["mrr"] - full_row["mrr"], 4)
                if isinstance(row["mrr"], float) and isinstance(full_row["mrr"], float) else None
            ),
            "extra_violations": row["violations"] - full_row["violations"],
        })
    result.metrics = {"configs": base_rows, "deltas": deltas}
    result.passed = True
    return result


# --------------------------------------------------------------------------- #
# Report writers
# --------------------------------------------------------------------------- #
def write_reports(suites: list[SuiteResult], ts: str, out_dir: Path) -> tuple[Path, Path, Path]:
    """Persist eval_<ts>.json, eval_<ts>.csv and the HTML dashboard."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"eval_{ts}.json"
    csv_path = out_dir / f"eval_{ts}.csv"

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "suites": [asdict(suite) for suite in suites],
        "gates": {
            "E1_f1_ge_0.90": next(s.passed for s in suites if s.suite.startswith("E1")),
            "E2_mrr_ge_0.80": next(s.passed for s in suites if s.suite.startswith("E2")),
            "E3_violations_eq_0": next(s.passed for s in suites if s.suite.startswith("E3")),
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["suite", "item", "metric", "value"])
        for suite in suites:
            writer.writerow([suite.suite, "_summary", "passed", suite.chip()])
            for key, value in suite.metrics.items():
                writer.writerow([suite.suite, "_summary", key, json.dumps(value, default=str)])
            for detail in suite.details:
                writer.writerow([
                    suite.suite,
                    detail.get("doc", "-"),
                    "detail",
                    json.dumps(detail, default=str)[:500],
                ])

    html_path = out_dir / f"eval_{ts}.html"
    html_path.write_text(render_html(suites, payload), encoding="utf-8")
    return json_path, csv_path, html_path


def render_html(suites: list[SuiteResult], payload: dict[str, Any]) -> str:
    """Self-contained HTML dashboard (inline CSS, zero external assets)."""
    cards = []
    for suite in suites:
        color = "#16a34a" if suite.passed else "#dc2626"
        chip = f'<span class="chip" style="background:{color}">{suite.chip()}</span>'
        metric_rows = "".join(
            f"<tr><td>{key}</td><td><code>{json.dumps(value, default=str)[:220]}</code></td></tr>"
            for key, value in suite.metrics.items()
        )
        cards.append(f"""
        <div class="card">
          <h3>{suite.suite} {chip}</h3>
          <table><tr><th>metric</th><th>value</th></tr>{metric_rows}</table>
        </div>""")

    violation_counts = Counter()
    for suite in suites:
        if suite.suite.startswith(("E3", "E7")):
            for detail in suite.details:
                for violation in detail.get("violations", []) or []:
                    violation_counts[violation.split(":")[0]] += 1
    hist_max = max(violation_counts.values(), default=1)
    bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{code}</span>'
        f'<div class="bar" style="width:{100 * count // hist_max}%">{count}</div></div>'
        for code, count in violation_counts.most_common(10)
    ) or '<p class="ok">No violations recorded.</p>'

    latency_html = ""
    for suite in suites:
        if suite.suite.startswith("E6"):
            stages = suite.metrics.get("stages", {})
            worst = max((v["p50_ms"] for v in stages.values()), default=1) or 1
            latency_html = "".join(
                f'<div class="bar-row"><span class="bar-label">{stage}</span>'
                f'<div class="bar lat" style="width:{int(100 * values["p50_ms"] / worst)}%">'
                f'{values["p50_ms"]} ms</div></div>'
                for stage, values in stages.items()
            )

    ablation_html = ""
    for suite in suites:
        if suite.suite.startswith("E8"):
            header = "".join(f"<th>{key}</th>" for key in ("config", "\u0394 field_f1", "\u0394 mrr", "extra viol"))
            rows = "".join(
                "<tr>" + "".join(f"<td>{row[key]}</td>" for key in
                                 ("config", "field_f1_delta", "mrr_delta", "extra_violations")) + "</tr>"
                for row in suite.metrics.get("deltas", [])
            )
            ablation_html = f"<table><tr>{header}</tr>{rows}</table>"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>LexOrch-KG Evaluation Dashboard</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;background:#f8fafc;color:#0f172a}}
 h1{{font-size:22px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}}
 .card{{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
 .chip{{color:#fff;border-radius:999px;padding:2px 12px;font-size:12px;font-weight:700}}
 table{{border-collapse:collapse;width:100%;font-size:13px}}
 td,th{{border-bottom:1px solid #e2e8f0;padding:6px 8px;text-align:left}}
 th{{background:#f1f5f9}} code{{font-size:11px}}
 .bar-row{{display:flex;align-items:center;margin:4px 0}}
 .bar-label{{width:170px;font-size:12px;color:#475569}}
 .bar{{background:#dc2626;color:#fff;font-size:11px;padding:3px 6px;border-radius:4px;min-width:30px;text-align:right}}
 .bar.lat{{background:#2563eb}} .ok{{color:#16a34a;font-weight:600}}
 footer{{margin-top:28px;color:#94a3b8;font-size:12px}}
</style></head><body>
<h1>LexOrch-KG Evaluation Dashboard</h1>
<p>Generated {payload['generated_at']} &middot; gates:
{' '.join(f'<span class="chip" style="background:{"#16a34a" if ok else "#dc2626"}">{name}</span>' for name, ok in payload['gates'].items())}
</p>
<div class="grid">{''.join(cards)}</div>
<div class="card"><h3>Violation histogram</h3>{bars}</div>
<div class="card"><h3>Stage latency (p50)</h3>{latency_html}</div>
<div class="card"><h3>Ablation &Delta; table</h3>{ablation_html}</div>
<footer>LexOrch-KG evaluation framework - self-contained report.</footer>
</body></html>"""


# --------------------------------------------------------------------------- #
# Console + CLI
# --------------------------------------------------------------------------- #
def print_summary(suites: list[SuiteResult], paths: tuple[Path, Path, Path], exit_code: int) -> None:
    """Render the final console table (only stdout in this module)."""
    bar = "=" * 92
    print(bar)
    print(" LEXORCH-KG EVALUATION SUITE")
    print(bar)
    for suite in suites:
        status = "PASS ✅" if suite.passed else "FAIL ❌"
        headline = ", ".join(f"{k}={v}" for k, v in suite.metrics.items() if not isinstance(v, dict))
        print(f" {suite.suite:<18} {status:<8} {headline[:110]}")
    print("-" * 92)
    print(f" reports : {paths[0].name} | {paths[1].name} | {paths[2].name}")
    print(f" RESULT  : {'ALL SUITES PASS ✅' if exit_code == 0 else 'GATE FAILURE ❌'} (exit={exit_code})")
    print(bar)


def compute_exit_code(suites: list[SuiteResult], ran_e7_corpus: bool) -> int:
    """Gate: E1 F1>=0.90 AND E3==0 AND E2 MRR>=0.8 AND (E7>=0.95 when --dir)."""

    def find(prefix: str) -> SuiteResult | None:
        return next((s for s in suites if s.suite.startswith(prefix)), None)

    e1, e2, e3, e7 = find("E1"), find("E2"), find("E3"), find("E7")
    if not e1 or not e2 or not e3:
        return 2
    if not (e1.passed and e2.passed and e3.passed):
        return 1
    if ran_e7_corpus and e7 is not None and not e7.passed:
        return 1
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI definition for the evaluation suite."""
    parser = argparse.ArgumentParser(prog="python -m scripts.eval_suite")
    parser.add_argument("--suite", default="all", help="all|extraction|retrieval|grounding|reasoning|perf|robustness|ablation|human")
    parser.add_argument("--dir", default=None, help="corpus directory for E7 robustness (optional)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--with-llm", action="store_true", help="enable optional LLM-as-Judge in E4")
    parser.add_argument("--out", default=str(REPORTS_DIR))
    return parser.parse_args(argv)


SUITE_ALIASES = {
    "extraction": ("E1",),
    "retrieval": ("E2",),
    "grounding": ("E3",),
    "reasoning": ("E4",),
    "human": ("E5",),
    "perf": ("E6",),
    "robustness": ("E7",),
    "ablation": ("E8",),
}


def main(argv: list[str] | None = None) -> int:
    """Entry point: dispatch requested suites, write reports, apply gates."""
    args = parse_args(argv)
    requested = list(SUITE_ALIASES) if args.suite == "all" else [args.suite]
    if args.suite != "all" and args.suite not in SUITE_ALIASES:
        logger.error(f"unknown suite {args.suite!r}")
        return 2
    docs = gold_docs()
    missing = [str(d.path) for d in docs if not d.path.exists()]
    if missing:
        logger.error(f"missing gold files: {missing}")
        return 2

    runners: dict[str, Any] = {}
    if "extraction" in requested:
        runners["E1"] = lambda: e1_extraction(docs)
    if "retrieval" in requested:
        runners["E2"] = lambda: e2_retrieval(docs)
    if "grounding" in requested:
        runners["E3"] = lambda: e3_grounding(docs)
    if "reasoning" in requested:
        runners["E4"] = lambda: e4_reasoning(docs, with_llm=args.with_llm)
    if "human" in requested:
        runners["E5"] = lambda: e5_human_pack(Path(args.out))
    if "perf" in requested:
        runners["E6"] = lambda: e6_performance(docs)
    if "robustness" in requested:
        runners["E7"] = lambda: e7_robustness(args.dir, workers=args.workers)
    if "ablation" in requested:
        runners["E8"] = lambda: e8_ablation(docs)

    suites: list[SuiteResult] = []
    for name in sorted(runners):
        logger.info(f"running {name}...")
        started = time.perf_counter()
        suite = runners[name]()
        suite.metrics["duration_s"] = round(time.perf_counter() - started, 1)
        suites.append(suite)

    ts = time.strftime("%Y%m%d-%H%M%S")
    paths = write_reports(suites, ts, Path(args.out))
    exit_code = compute_exit_code(suites, ran_e7_corpus=bool(args.dir) and "robustness" in requested)
    print_summary(suites, paths, exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
