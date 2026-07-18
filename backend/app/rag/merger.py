"""Reciprocal Rank Fusion (RRF) merger for multi-source retrieval.

Merges results from 4 parallel retrievers into a single
ranked list using weighted reciprocal rank fusion.
"""

from __future__ import annotations

from typing import Any


class ResultMerger:
    """Merge results from multiple retrievers using RRF.

    Reciprocal Rank Fusion combines rankings from different
    sources by scoring each document as:
        RRF(d) = sum(weight_i / (k + rank_i(d)))
    where k is a constant smoothing parameter (default 60).
    """

    def __init__(self, k: int = 60) -> None:
        """Initialize the merger.

        Args:
            k: RRF smoothing constant. Higher k means rank
               differences matter less. Default 60 per Cormack et al.
        """
        self.k = k

    def merge(
        self,
        result_sets: list[list[dict[str, Any]]],
        source_weights: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Merge multiple result lists using weighted RRF.

        Args:
            result_sets: List of result lists, one per retriever.
            source_weights: Dict mapping source name to weight multiplier.
                           Default equal weights.

        Returns:
            Single merged and sorted result list.
        """
        if not result_sets:
            return []

        if source_weights is None:
            # Default: equal weights
            sources = set()
            for results in result_sets:
                for r in results:
                    sources.add(r.get("source", "unknown"))
            source_weights = {s: 1.0 for s in sources}

        # Build RRF scores
        doc_scores: dict[str, float] = {}  # key = text hash or first 100 chars
        doc_data: dict[str, dict[str, Any]] = {}

        for result_list in result_sets:
            for rank, result in enumerate(result_list, start=1):
                # Create a stable key from the result text
                text = result.get("text", "")
                key = self._make_key(text)

                source = result.get("source", "unknown")
                weight = source_weights.get(source, 1.0)

                # RRF score contribution
                rrf_score = weight / (self.k + rank)
                doc_scores[key] = doc_scores.get(key, 0.0) + rrf_score

                # Store the result data (keep the one with higher individual score)
                if key not in doc_data or result.get("score", 0) > doc_data[key].get("score", 0):
                    doc_data[key] = result
                    # Record which sources matched
                    doc_data[key]["matched_sources"] = doc_data[key].get("matched_sources", [])
                    if source not in doc_data[key]["matched_sources"]:
                        doc_data[key]["matched_sources"].append(source)

        # Sort by RRF score descending
        sorted_keys = sorted(doc_scores, key=doc_scores.get, reverse=True)  # type: ignore[arg-type]

        merged: list[dict[str, Any]] = []
        for key in sorted_keys:
            result = doc_data[key]
            result["rrf_score"] = doc_scores[key]
            merged.append(result)

        return merged

    @staticmethod
    def _make_key(text: str) -> str:
        """Create a stable key from text for deduplication.

        Uses first 120 chars normalized for near-dedup.
        """
        # Remove whitespace differences
        normalized = " ".join(text[:120].split()).lower()
        return normalized
