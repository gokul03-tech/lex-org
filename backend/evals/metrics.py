"""Typed metric functions for the LexOrch-KG evaluation framework.

All string comparisons are punctuation/whitespace/case-insensitive unless
stated. Ranking metrics operate on ordered lists of per-item relevance
gains (0/1 or graded) so they stay reusable across E2 and E7.
"""
from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

DEFAULT_BANNED: tuple[str, ...] = (
    "Not found in document",
    "Mock summary",
    "keyword",
    "vector",
    "Applicable Statutes",
    "{'num'",
    "Bail App.",
    "\u2014 \u2014",
)


def norm_text(value: Any) -> str:
    """Lowercase and strip every non-alphanumeric character."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def ws_norm(value: Any) -> str:
    """Collapse whitespace runs to single spaces (keeps punctuation)."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


# --------------------------------------------------------------------------- #
# Pair metrics
# --------------------------------------------------------------------------- #
def exact_match(pred: Any, gold: Any) -> float:
    """1.0 iff normalized strings are equal; None/empty matches None/empty."""
    p, g = norm_text(pred), norm_text(gold)
    if not p and not g:
        return 1.0
    return 1.0 if p == g else 0.0


def list_f1(pred: Iterable[Any], gold: Iterable[Any]) -> float:
    """Set-based F1 over normalized elements (judges, citations, articles)."""
    preds = {norm_text(x) for x in pred if norm_text(x)}
    golds = {norm_text(x) for x in gold if norm_text(x)}
    if not golds and not preds:
        return 1.0
    if not golds or not preds:
        return 0.0
    tp = len(preds & golds)
    precision = tp / len(preds)
    recall = tp / len(golds)
    return 0.0 if tp == 0 else 2 * precision * recall / (precision + recall)


def act_matches(pred_act: Any, gold_act: Any) -> bool:
    """Act-name matcher tolerant of citation suffixes ('BNSS' vs long form)."""
    p, g = norm_text(pred_act), norm_text(gold_act)
    if not p or not g:
        return False
    return p in g or g in p


def mapping_f1(pred: dict[str, Any], gold: dict[str, Any], key_norm=None) -> float:
    """F1 over dict items where values match via ``value_match`` (sections)."""
    key_fn = key_norm or norm_text
    preds = {(key_fn(k), v) for k, v in (pred or {}).items()}
    matched_gold = 0
    matched_pred_keys: set[str] = set()
    for gk, gv in (gold or {}).items():
        hit = next(((pk, pv) for pk, pv in preds if pk == key_fn(gk) and act_matches(pv, gv)), None)
        if hit:
            matched_gold += 1
            matched_pred_keys.add(hit[0])
    n_pred = len({k for k, _ in preds})
    n_gold = len(gold or {})
    if n_pred == 0 and n_gold == 0:
        return 1.0
    if n_pred == 0 or n_gold == 0:
        return 0.0
    precision = len(matched_pred_keys) / n_pred
    recall = matched_gold / n_gold
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def pair_accuracy(pred_pairs: list[tuple[str, str]], gold_pairs: dict[str, str]) -> float:
    """Precedent name+citation joint accuracy (both must match)."""
    if not gold_pairs:
        return 1.0
    hits = 0
    for name, cite in ((n, c) for n, c in pred_pairs):
        gold_cite = gold_pairs.get(name) or next(
            (gc for gn, gc in gold_pairs.items() if norm_text(gn) == norm_text(name)), None
        )
        if gold_cite and norm_text(cite) == norm_text(gold_cite):
            hits += 1
    denom = max(len(gold_pairs), len(pred_pairs)) or 1
    return min(hits / denom, 1.0)


# --------------------------------------------------------------------------- #
# Ranking metrics (E2 retrieval)
# --------------------------------------------------------------------------- #
@dataclass
class RankingReport:
    """Aggregated ranking metrics over a query set."""

    recall_at_5: float = 0.0
    precision_at_5: float = 0.0
    mrr: float = 0.0
    ndcg_at_10: float = 0.0
    per_query: list[dict[str, float]] = field(default_factory=list)


def _gains_at(ranked_relevance: list[int], k: int) -> list[int]:
    return ranked_relevance[:k]


def recall_at_k(ranked_relevance: list[int], k: int, total_relevant: int | None = None) -> float:
    """Recall@k over a binary relevance-ordered result list."""
    total = total_relevant if total_relevant is not None else sum(ranked_relevance)
    if total <= 0:
        return 0.0
    return sum(_gains_at(ranked_relevance, k)) / total


def precision_at_k(ranked_relevance: list[int], k: int) -> float:
    """Precision@k over a binary relevance-ordered result list."""
    window = _gains_at(ranked_relevance, k)
    return sum(window) / k if k > 0 else 0.0


def mrr(ranked_relevance: list[int]) -> float:
    """Mean reciprocal rank of the first relevant item (single query)."""
    for index, rel in enumerate(ranked_relevance, start=1):
        if rel > 0:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_relevance: list[int], k: int) -> float:
    """Normalized discounted cumulative gain with log2 discount."""
    gains = _gains_at(ranked_relevance, k)
    dcg = sum(rel / math.log2(i + 1) for i, rel in enumerate(gains, start=1))
    ideal = sorted(ranked_relevance, reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 1) for i, rel in enumerate(ideal, start=1))
    return dcg / idcg if idcg > 0 else 0.0


def aggregate_ranking(per_query_rows: list[dict[str, float]]) -> RankingReport:
    """Average per-query metric rows into one report."""
    if not per_query_rows:
        return RankingReport()
    keys = ("recall_at_5", "precision_at_5", "mrr", "ndcg_at_10")
    avg = {
        key: sum(row.get(key, 0.0) for row in per_query_rows) / len(per_query_rows)
        for key in keys
    }
    return RankingReport(**avg, per_query=per_query_rows)


# --------------------------------------------------------------------------- #
# Grounding metrics (E3)
# --------------------------------------------------------------------------- #
def iter_strings(node: Any) -> Iterable[str]:
    """Yield every string leaf inside arbitrarily nested JSON-ish data."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from iter_strings(value)
    elif isinstance(node, (list, tuple, set)):
        for item in node:
            yield from iter_strings(item)


def verbatim(text: str, quote: str) -> bool:
    """Whitespace-insensitive containment of ``quote`` inside ``text``."""
    q, t = ws_norm(quote).casefold(), ws_norm(text).casefold()
    return bool(q) and q in t


def leakage_scan(report: Any, banned: tuple[str, ...] = DEFAULT_BANNED) -> list[str]:
    """All banned-string occurrences found among the report's strings."""
    findings: list[str] = []
    for text in iter_strings(report):
        low = text.lower()
        for item in banned:
            if item.lower() in low:
                findings.append(f"{item!r} in {text[:80]!r}")
                break
    return findings


def citation_binding_violations(precedents: list[dict[str, Any]]) -> list[str]:
    """Two distinct precedents must never share one citation."""
    owner: dict[str, str] = {}
    violations = []
    for precedent in precedents or []:
        name = norm_text(precedent.get("case_name"))
        cite = norm_text(precedent.get("citation"))
        if not cite or not name:
            continue
        prev = owner.setdefault(cite, name)
        if prev != name:
            violations.append(f"citation shared by {prev!r} and {name!r}")
    return violations


def self_match_violations(case_title: str, precedents: list[dict[str, Any]]) -> list[str]:
    """A precedent must not be the case itself."""
    title = norm_text(case_title)
    if not title:
        return []
    return [
        f"self-match: {p.get('case_name')!r}"
        for p in precedents or []
        if norm_text(p.get("case_name")) == title
    ]


# --------------------------------------------------------------------------- #
# Reasoning metrics (E4)
# --------------------------------------------------------------------------- #
IRAC_KEYS = ("issue", "rule", "application", "conclusion")


@dataclass
class IRACResult:
    """Completeness verdict for the four IRAC components."""

    issue: bool = False
    rule: bool = False
    application: bool = False
    conclusion: bool = False

    @property
    def score(self) -> float:
        return sum(bool(getattr(self, key)) for key in IRAC_KEYS) / len(IRAC_KEYS)

    def as_dict(self) -> dict[str, Any]:
        return {"issue": self.issue, "rule": self.rule, "application": self.application,
                "conclusion": self.conclusion, "score": round(self.score, 3)}


def irac_completeness(report: dict[str, Any]) -> IRACResult:
    """Map analysis-report sections onto Issue/Rule/Application/Conclusion.

    Issue <- legal issues derivable from statutes/articles; Rule <- bound
    statute/article displays; Application <- counsel submissions or evidence;
    Conclusion <- operative risk conclusion.
    """
    sections = report.get("sections") or []
    articles = report.get("articles") or []
    submissions = report.get("submissions") or {}
    evidence = report.get("evidence") or []

    has_rule = bool(sections) or bool(articles)
    has_issue = has_rule or bool(evidence)
    has_application = any(submissions.get(side) for side in ("a", "b")) or bool(evidence)
    conclusion = str((report.get("risk") or {}).get("conclusion") or "")
    outcome_word = re.search(r"\b(?:allowed|dismissed|disposed|set aside)\b", conclusion, re.I)
    return IRACResult(issue=has_issue, rule=has_rule, application=bool(has_application),
                      conclusion=bool(conclusion.strip() and outcome_word))


OUTCOME_ALIASES: dict[str, str] = {
    "allowed": "allowed",
    "granted": "allowed",
    "partly allowed": "partly allowed",
    "partially allowed": "partly allowed",
    "disposed of": "disposed of",
    "disposed": "disposed of",
    "dismissed": "dismissed",
    "rejected": "dismissed",
}


def outcome_normalize(text: str) -> str | None:
    """Extract the canonical GOLD-style outcome phrase from free text."""
    low = ws_norm(text).lower()
    if "partly allowed" in low or "partially allowed" in low:
        return "partly allowed"
    for phrase, canonical in OUTCOME_ALIASES.items():
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return canonical
    return None


def outcome_accuracy(predicted: str | None, gold: str) -> float:
    """1.0 iff predicted canonical outcome equals gold outcome."""
    return 1.0 if predicted is not None and predicted == outcome_normalize(gold) else 0.0
