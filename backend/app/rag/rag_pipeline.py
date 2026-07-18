"""Adaptive Multi-Stage RAG Pipeline for legal retrieval.

Orchestrates the full retrieval pipeline:
1. Intent Detection → classifies query into legal intent category
2. Query Rewriting → generates multiple query variants
3. 4-Way Parallel Retrieval → vector, KG, citation, keyword
4. Reciprocal Rank Fusion → merges results with intent-adaptive weights
5. Cross-Encoder Reranking → re-ranks top candidates for precision
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from loguru import logger

from app.rag.intent_detector import IntentDetector, LegalIntent
from app.rag.query_rewriter import QueryRewriter
from app.rag.retrievers.vector_search import VectorRetriever
from app.rag.retrievers.kg_search import KnowledgeGraphRetriever
from app.rag.retrievers.citation_search import CitationRetriever
from app.rag.retrievers.keyword_search import KeywordRetriever
from app.rag.merger import ResultMerger
from app.rag.reranker import CrossEncoderReranker


class RAGPipeline:
    """Complete adaptive multi-stage RAG pipeline.

    Usage:
        rag = RAGPipeline()
        results = await rag.search("What is the punishment for theft under BNS?")
    """

    def __init__(self) -> None:
        """Initialize all RAG components."""
        self.intent_detector = IntentDetector()
        self.query_rewriter = QueryRewriter()
        self.vector_retriever = VectorRetriever()
        self.kg_retriever = KnowledgeGraphRetriever()
        self.citation_retriever = CitationRetriever()
        self.keyword_retriever = KeywordRetriever()
        self.merger = ResultMerger(k=60)
        self.reranker = CrossEncoderReranker()

    async def search(
        self,
        query: str,
        top_k: int = 10,
        intent: str | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute the full multi-stage RAG pipeline.

        Args:
            query: The search query string.
            top_k: Number of final results after reranking.
            intent: Optional pre-detected intent (skips detection if provided).
            filter_conditions: Optional metadata filters for vector search.

        Returns:
            Ranked list of result dicts with text, score, source, and metadata.
        """
        start_time = time.monotonic()
        logger.info(f"RAG pipeline starting for query: {query[:100]}")

        # ── Stage 1: Intent Detection ──
        stage_start = time.monotonic()
        if intent:
            detected_intent = LegalIntent(intent)
        else:
            detected_intent = self.intent_detector.detect(query)
        intent_weights = self.intent_detector.get_retriever_weights(detected_intent)
        logger.info(f"  Stage 1 (Intent): {detected_intent.value} ({time.monotonic() - stage_start:.3f}s)")

        # ── Stage 2: Query Rewriting ──
        stage_start = time.monotonic()
        query_variants = self.query_rewriter.rewrite(query, detected_intent.value)
        logger.info(f"  Stage 2 (Rewrite): {len(query_variants)} variants ({time.monotonic() - stage_start:.3f}s)")

        # ── Stage 3: 4-Way Parallel Retrieval ──
        stage_start = time.monotonic()

        # Run all retrievers in parallel
        results = await asyncio.gather(
            # Vector search (main variant)
            self.vector_retriever.search(
                query=query_variants[0],
                top_k=top_k * 3,
                filter_conditions=filter_conditions,
            ),
            # KG search
            self.kg_retriever.search(
                query=query,
                top_k=top_k * 2,
            ),
            # Citation search
            self.citation_retriever.search(
                query=query,
                top_k=top_k,
            ),
            # Keyword search (try main variant)
            self.keyword_retriever.search(
                query=query_variants[0],
                top_k=top_k * 2,
            ),
            return_exceptions=True,
        )

        # Unpack results, filtering out exceptions
        vector_results = results[0] if not isinstance(results[0], Exception) else []
        kg_results = results[1] if not isinstance(results[1], Exception) else []
        citation_results = results[2] if not isinstance(results[2], Exception) else []
        keyword_results = results[3] if not isinstance(results[3], Exception) else []

        logger.info(
            f"  Stage 3 (Retrieval): vector={len(vector_results)}, "
            f"kg={len(kg_results)}, citation={len(citation_results)}, "
            f"keyword={len(keyword_results)} ({time.monotonic() - stage_start:.3f}s)"
        )

        # ── Stage 4: Reciprocal Rank Fusion ──
        stage_start = time.monotonic()

        # Build source weight dict from intent weights
        source_weights = {
            "vector": intent_weights.get("vector", 1.0),
            "kg": intent_weights.get("kg", 1.0),
            "citation": intent_weights.get("citation", 1.0),
            "keyword": intent_weights.get("keyword", 1.0),
        }

        merged = self.merger.merge(
            [vector_results, kg_results, citation_results, keyword_results],
            source_weights=source_weights,
        )
        logger.info(f"  Stage 4 (Merge): {len(merged)} candidates ({time.monotonic() - stage_start:.3f}s)")

        # ── Stage 5: Cross-Encoder Reranking ──
        stage_start = time.monotonic()
        final_results = self.reranker.rerank(query, merged, top_k=top_k)
        logger.info(f"  Stage 5 (Rerank): {len(final_results)} final results ({time.monotonic() - stage_start:.3f}s)")

        total_time = time.monotonic() - start_time
        logger.info(f"RAG pipeline complete: {len(final_results)} results in {total_time:.3f}s")

        return final_results

    async def search_with_metadata(
        self,
        query: str,
        top_k: int = 10,
        intent: str | None = None,
    ) -> dict[str, Any]:
        """Search with full metadata about the pipeline execution.

        Args:
            query: The search query.
            top_k: Final result count.
            intent: Optional pre-detected intent.

        Returns:
            Dict with 'results', 'intent', 'pipeline_stats'.
        """
        start_time = time.monotonic()

        intent_detected = self.intent_detector.detect(query)
        results = await self.search(query, top_k=top_k, intent=intent or intent_detected.value)

        elapsed = time.monotonic() - start_time

        return {
            "results": results,
            "detected_intent": intent_detected.value if not intent else intent,
            "pipeline_stats": {
                "total_time_ms": elapsed * 1000,
                "result_count": len(results),
                "sources": list(set(r.get("source", "") for r in results)),
                "avg_score": sum(r.get("score", 0) for r in results) / max(len(results), 1),
            },
        }
