"""Evaluation metrics for LexOrch-KG.

Implements standard information retrieval metrics plus
legal-specific evaluation measures for section matching,
IRAC quality scoring, and trust calibration.
"""

from __future__ import annotations

import math
from typing import Any


# ── Information Retrieval Metrics ────────────────────────────
def recall_at_k(retrieved: list[str], relevant: list[str], k: int = 10) -> float:
    """Compute Recall@K.

    Args:
        retrieved: List of retrieved item IDs (ordered by score).
        relevant: List of relevant item IDs (ground truth).
        k: Cutoff rank.

    Returns:
        Recall@K score (0.0 to 1.0).
    """
    if not relevant:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(relevant_set)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int = 10) -> float:
    """Compute Precision@K.

    Args:
        retrieved: List of retrieved item IDs.
        relevant: List of relevant item IDs.
        k: Cutoff rank.

    Returns:
        Precision@K score (0.0 to 1.0).
    """
    if k <= 0 or not retrieved:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / k


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    """Compute Mean Reciprocal Rank.

    MRR = 1 / rank_of_first_relevant_item

    Args:
        retrieved: Ordered list of retrieved item IDs.
        relevant: Set of relevant item IDs.

    Returns:
        MRR score (0.0 to 1.0).
    """
    relevant_set = set(relevant)
    for i, item in enumerate(retrieved, start=1):
        if item in relevant_set:
            return 1.0 / i
    return 0.0


def ndcg_at_k(
    retrieved: list[str],
    relevance_scores: dict[str, float],
    k: int = 10,
) -> float:
    """Compute Normalized Discounted Cumulative Gain at K.

    Args:
        retrieved: Ordered list of retrieved item IDs.
        relevance_scores: Dict mapping item ID to relevance score (0-3 or 0-1).
        k: Cutoff rank.

    Returns:
        NDCG@K score (0.0 to 1.0).
    """
    def dcg(items: list[str]) -> float:
        score = 0.0
        for i, item in enumerate(items[:k], start=1):
            rel = relevance_scores.get(item, 0.0)
            score += rel / math.log2(i + 1)
        return score

    actual_dcg = dcg(retrieved)

    # Ideal DCG: sort by relevance score descending
    ideal_order = sorted(
        relevance_scores.keys(),
        key=lambda x: relevance_scores.get(x, 0.0),
        reverse=True,
    )
    ideal_dcg = dcg(ideal_order)

    return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0


# ── Legal-Specific Metrics ───────────────────────────────────
def section_matching_f1(
    predicted_sections: list[dict[str, Any]],
    ground_truth_sections: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute F1 score for section citation matching.

    Compares predicted section citations against ground truth.

    Args:
        predicted_sections: List of dicts with 'section_number' and 'act'.
        ground_truth_sections: Ground truth section list.

    Returns:
        Dict with precision, recall, f1.
    """
    def section_key(sec: dict[str, Any]) -> str:
        return f"{sec.get('act', '')}::{sec.get('section_number', '')}"

    pred_keys = set(section_key(s) for s in predicted_sections)
    gt_keys = set(section_key(s) for s in ground_truth_sections)

    true_positives = len(pred_keys & gt_keys)
    precision = true_positives / len(pred_keys) if pred_keys else 0.0
    recall = true_positives / len(gt_keys) if gt_keys else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def temporal_routing_accuracy(
    predictions: list[str],
    ground_truth: list[str],
) -> float:
    """Accuracy of IPC vs BNS temporal routing.

    Evaluates whether the system correctly routes queries
    to the appropriate act based on temporal context.

    Args:
        predictions: List of predicted act names (e.g., 'BNS', 'IPC').
        ground_truth: Ground truth act names.

    Returns:
        Accuracy score (0.0 to 1.0).
    """
    if not predictions:
        return 0.0
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(predictions)


def irac_quality_score(
    analysis: dict[str, Any],
    rubric_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """Score the quality of an IRAC legal analysis.

    Evaluates Issue, Rule, Application, and Conclusion separately.

    Args:
        analysis: Dict with 'issue', 'rule', 'application', 'conclusion' keys.
        rubric_weights: Optional weights for each IRAC component.

    Returns:
        Dict with per-component scores and weighted total.
    """
    if rubric_weights is None:
        rubric_weights = {
            "issue": 0.15,
            "rule": 0.30,
            "application": 0.40,
            "conclusion": 0.15,
        }

    scores: dict[str, float] = {}

    for component in ["issue", "rule", "application", "conclusion"]:
        content = analysis.get(component, "")
        if not content or content == "N/A":
            scores[component] = 0.0
            continue

        # Heuristic scoring based on content quality indicators
        score = 0.6  # Base score for non-empty content
        if len(content) > 100:
            score += 0.1
        if len(content) > 300:
            score += 0.1
        if any(kw in content.lower() for kw in ["section", "act", "provision", "code"]):
            score += 0.1
        if any(kw in content.lower() for kw in ["therefore", "conclusion", "held"]):
            score += 0.1

        scores[component] = min(score, 1.0)

    # Weighted total
    total = sum(
        scores.get(comp, 0.0) * weight
        for comp, weight in rubric_weights.items()
    )

    scores["weighted_total"] = total
    return scores


def contradiction_detection_metrics(
    predicted_contradictions: list[dict[str, Any]],
    ground_truth_contradictions: list[dict[str, Any]],
) -> dict[str, float]:
    """Precision/Recall for contradiction detection.

    Args:
        predicted_contradictions: Detected contradictions.
        ground_truth_contradictions: Known contradictions (ground truth).

    Returns:
        Dict with precision, recall, f1.
    """
    def contradiction_key(cont: dict[str, Any]) -> str:
        return f"{cont.get('type', '')}::{cont.get('statement_a', '')[:50]}::{cont.get('statement_b', '')[:50]}"

    pred_keys = set(contradiction_key(c) for c in predicted_contradictions)
    gt_keys = set(contradiction_key(c) for c in ground_truth_contradictions)

    tp = len(pred_keys & gt_keys)
    precision = tp / len(pred_keys) if pred_keys else 0.0
    recall = tp / len(gt_keys) if gt_keys else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def expected_calibration_error(
    confidence_scores: list[float],
    accuracy_scores: list[float],
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE).

    Measures how well calibrated the trust/confidence scores are.
    Lower ECE means better calibration.

    Args:
        confidence_scores: Model's confidence predictions (0-1).
        accuracy_scores: Binary accuracy (0 or 1) for each prediction.
        n_bins: Number of bins for ECE computation.

    Returns:
        ECE score (0.0 to 1.0, lower is better).
    """
    if not confidence_scores or len(confidence_scores) != len(accuracy_scores):
        return 1.0

    pairs = list(zip(confidence_scores, accuracy_scores))
    pairs.sort(key=lambda x: x[0])

    bin_size = len(pairs) / n_bins
    ece = 0.0

    for i in range(n_bins):
        start = int(i * bin_size)
        end = int((i + 1) * bin_size)
        bin_pairs = pairs[start:end]

        if not bin_pairs:
            continue

        avg_confidence = sum(p[0] for p in bin_pairs) / len(bin_pairs)
        avg_accuracy = sum(p[1] for p in bin_pairs) / len(bin_pairs)
        weight = len(bin_pairs) / len(pairs)

        ece += weight * abs(avg_confidence - avg_accuracy)

    return ece


# ── Aggregate Metric Reporter ────────────────────────────────
def compute_all_metrics(
    results: dict[str, Any],
) -> dict[str, Any]:
    """Compute all evaluation metrics from a results dict.

    Args:
        results: Dict containing raw predictions and ground truth.

    Returns:
        Dict of computed metrics.
    """
    metrics: dict[str, Any] = {}

    # RAG metrics
    if "retrieved_ids" in results and "relevant_ids" in results:
        retrieved = results["retrieved_ids"]
        relevant = results["relevant_ids"]
        metrics["recall@5"] = recall_at_k(retrieved, relevant, k=5)
        metrics["recall@10"] = recall_at_k(retrieved, relevant, k=10)
        metrics["precision@10"] = precision_at_k(retrieved, relevant, k=10)
        metrics["mrr"] = mrr(retrieved, relevant)

    # Section matching
    if "predicted_sections" in results and "ground_truth_sections" in results:
        metrics["section_f1"] = section_matching_f1(
            results["predicted_sections"],
            results["ground_truth_sections"],
        )

    # Temporal routing
    if "predicted_acts" in results and "ground_truth_acts" in results:
        metrics["temporal_accuracy"] = temporal_routing_accuracy(
            results["predicted_acts"],
            results["ground_truth_acts"],
        )

    # IRAC quality
    if "irac_analysis" in results:
        metrics["irac_quality"] = irac_quality_score(results["irac_analysis"])

    # Contradiction detection
    if "predicted_contradictions" in results and "ground_truth_contradictions" in results:
        metrics["contradiction_metrics"] = contradiction_detection_metrics(
            results["predicted_contradictions"],
            results["ground_truth_contradictions"],
        )

    # Trust calibration
    if "confidence_scores" in results and "accuracy_scores" in results:
        metrics["ece"] = expected_calibration_error(
            results["confidence_scores"],
            results["accuracy_scores"],
        )

    return metrics
