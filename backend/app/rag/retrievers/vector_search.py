"""Qdrant vector search retriever.

Performs HNSW-based approximate nearest neighbor search
using BGE-M3 dense embeddings.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger


class VectorRetriever:
    """Vector similarity search using Qdrant.

    Converts query to embedding, searches Qdrant collections,
    and returns ranked results with cosine similarity scores.
    """

    def __init__(self) -> None:
        pass

    async def search(
        self,
        query: str,
        top_k: int = 20,
        collection_name: str | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform vector similarity search.

        Args:
            query: The search query text.
            top_k: Number of results to return.
            collection_name: Target Qdrant collection.
            filter_conditions: Optional payload filters.

        Returns:
            List of result dicts with score, text, and metadata.
        """
        start_time = time.monotonic()

        try:
            from app.embeddings.bge_m3 import get_bge_m3
            from app.embeddings.qdrant_client import get_qdrant_manager

            # Encode query
            embedder = get_bge_m3()
            query_vector = embedder.encode_queries([query])[0]

            # Search Qdrant
            qdrant = get_qdrant_manager()
            results = qdrant.search(
                query_vector=query_vector.tolist(),
                top_k=top_k,
                collection_name=collection_name,
                filter_conditions=filter_conditions,
            )

            # Add source annotation
            for r in results:
                r["source"] = "vector"

            duration_ms = (time.monotonic() - start_time) * 1000
            logger.info(f"Vector search returned {len(results)} results in {duration_ms:.0f}ms")
            return results

        except Exception as exc:
            logger.error(f"Vector search failed: {exc}")
            return []

    async def search_batch(
        self,
        queries: list[str],
        top_k: int = 20,
        collection_name: str | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Batch vector search for multiple queries.

        Args:
            queries: List of query strings.
            top_k: Results per query.
            collection_name: Target collection.

        Returns:
            List of result lists, one per input query.
        """
        try:
            from app.embeddings.bge_m3 import get_bge_m3
            from app.embeddings.qdrant_client import get_qdrant_manager

            embedder = get_bge_m3()
            qdrant = get_qdrant_manager()

            # Encode all queries
            embeddings = embedder.encode_queries(queries)

            # Batch search
            results = qdrant.search_batch(
                query_vectors=[e.tolist() for e in embeddings],
                top_k=top_k,
                collection_name=collection_name,
            )

            # Annotate source
            for result_list in results:
                for r in result_list:
                    r["source"] = "vector"

            return results
        except Exception as exc:
            logger.error(f"Batch vector search failed: {exc}")
            return [[] for _ in queries]
