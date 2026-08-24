"""Cross-encoder reranker for legal retrieval.

Applies a fine-tuned cross-encoder model to re-rank
the top-K candidates from the merged retrieval results,
significantly improving precision.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from loguru import logger

# Module-level shared CrossEncoder so every RAGPipeline()/reranker instance
# reuses the same loaded model instead of re-loading weights from disk.
_shared_models: dict[str, Any] = {}
_load_lock = threading.Lock()
_load_failed: set[str] = set()


def _get_shared_cross_encoder(model_name: str):
    """Load (once) and return the shared CrossEncoder for the given model name."""
    with _load_lock:
        if model_name in _shared_models:
            return _shared_models[model_name]
        if model_name in _load_failed:
            return None
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading CrossEncoder model: {model_name}")
            model = CrossEncoder(model_name)
            _shared_models[model_name] = model
            return model
        except Exception as exc:
            logger.warning(
                f"Failed to load CrossEncoder model, falling back to score-based reranking: {exc}"
            )
            _load_failed.add(model_name)
            return None


def warmup_reranker(model_name: str | None = None) -> bool:
    """Pre-load the shared CrossEncoder (call at app startup).

    Returns:
        True if the model is available for reranking.
    """
    resolved = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
    return _get_shared_cross_encoder(resolved) is not None


class CrossEncoderReranker:
    """Re-rank search results using a cross-encoder model.

    Uses:
    - Primary: cross-encoder/ms-marco-MiniLM-L-6-v2 (fast, general)
    - Legal alternative: fine-tuned legal-BERT cross-encoder (if available)
    - Fallback: Score-based re-ranking without model
    """

    def __init__(self, model_name: str | None = None) -> None:
        """Initialize the reranker.

        Args:
            model_name: Cross-encoder model name. Defaults to
                       ms-marco-MiniLM-L-6-v2 for general purpose.
        """
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._model = None
        self._loaded = False

    @property
    def model(self):
        """Lazy-load the cross-encoder model."""
        if not self._loaded:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """Load the shared cross-encoder model."""
        self._loaded = True
        self._model = _get_shared_cross_encoder(self.model_name)

    def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Re-rank results using cross-encoder relevance scores.

        Args:
            query: The original search query.
            results: List of result dicts from merged retrieval.
            top_k: Number of top results to return after re-ranking.

        Returns:
            Re-ranked result list.
        """
        if not results:
            return []

        start_time = time.monotonic()

        if self.model is not None:
            reranked = self._cross_encoder_rerank(query, results, top_k)
        else:
            reranked = self._score_based_rerank(query, results, top_k)

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"Reranking complete in {duration_ms:.0f}ms")
        return reranked

    def _cross_encoder_rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Use cross-encoder model for relevance scoring."""
        # Prepare query-document pairs
        pairs = [
            (query, result.get("text", "")[:500])
            for result in results
        ]

        # Get relevance scores
        scores = self.model.predict(pairs)

        # Attach scores
        for result, score in zip(results, scores):
            result["cross_encoder_score"] = float(score)
            result["original_score"] = result.get("score", 0.0)
            result["score"] = float(score)  # Replace with cross-encoder score

        # Sort and return top_k
        results.sort(key=lambda r: r.get("cross_encoder_score", 0.0), reverse=True)
        return results[:top_k]

    def _score_based_rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Fallback reranking using existing scores and query overlap."""
        query_terms = set(query.lower().split())

        for result in results:
            text = result.get("text", "").lower()
            text_terms = set(text.split())

            # Compute simple term overlap score
            overlap = len(query_terms & text_terms) / max(len(query_terms), 1)

            # Combine with existing scores
            base_score = result.get("score", 0.5)
            rrf_score = result.get("rrf_score", 0.0)

            # Weighted combination
            result["cross_encoder_score"] = 0.5 * base_score + 0.3 * rrf_score + 0.2 * overlap
            result["original_score"] = base_score
            result["score"] = result["cross_encoder_score"]

        # Sort and return top_k
        results.sort(key=lambda r: r.get("cross_encoder_score", 0.0), reverse=True)
        return results[:top_k]
