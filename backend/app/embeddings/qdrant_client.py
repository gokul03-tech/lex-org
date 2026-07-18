"""Qdrant vector database client for legal document embeddings.

Provides collection management, vector search, and batch
upsert operations for document chunks.
"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from app.core.config import settings


class QdrantManager:
    """Async Qdrant client wrapper for legal document embeddings.

    Manages collections for documents and sections with
    HNSW indexing for fast approximate nearest neighbor search.
    """

    def __init__(self, url: str | None = None, api_key: str | None = None) -> None:
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL.
            api_key: Optional API key for Qdrant Cloud.
        """
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY or None
        self._client = None
        self._initialized = False

    @property
    def client(self):
        """Lazy-load Qdrant client."""
        if self._client is None:
            self._init_client()
        return self._client

    def _init_client(self) -> None:
        """Initialize Qdrant client connection."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as rest

            if self.api_key:
                self._client = QdrantClient(url=self.url, api_key=self.api_key)
            else:
                self._client = QdrantClient(url=self.url)
            self._initialized = True
            logger.info(f"Qdrant client initialized: {self.url}")
        except ImportError:
            logger.warning("qdrant-client not installed. Vector search will be unavailable.")
            self._client = None
            self._initialized = False
        except Exception as exc:
            logger.error(f"Failed to connect to Qdrant: {exc}")
            self._client = None
            self._initialized = False

    @property
    def models(self):
        """Access Qdrant models."""
        from qdrant_client.http import models as rest
        return rest

    def is_available(self) -> bool:
        """Check if Qdrant is connected."""
        if not self._initialized:
            self._init_client()
        if self._client is None:
            return False
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def create_collections(self) -> bool:
        """Create all required Qdrant collections with HNSW config.

        Returns:
            True if collections created or already exist.
        """
        if not self.is_available():
            logger.warning("Qdrant unavailable, skipping collection creation.")
            return False

        collections = [
            (settings.QDRANT_COLLECTION_DOCS, "Legal document chunks"),
            (settings.QDRANT_COLLECTION_SECTIONS, "Legal section chunks"),
        ]

        for name, description in collections:
            try:
                existing = self._client.get_collections()
                collection_names = [c.name for c in existing.collections]
                if name in collection_names:
                    logger.info(f"Qdrant collection '{name}' already exists.")
                    continue

                self._client.create_collection(
                    collection_name=name,
                    vectors_config=self.models.VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=self.models.Distance.COSINE,
                    ),
                    hnsw_config=self.models.HnswConfigDiff(
                        m=16,  # Number of edges per node
                        ef_construct=200,  # Build-time search depth
                    ),
                    optimizers_config=self.models.OptimizersConfigDiff(
                        indexing_threshold=10000,
                    ),
                )
                logger.info(f"Created Qdrant collection: {name}")

                # Create payload indexes for filtering
                self._client.create_payload_index(
                    collection_name=name,
                    field_name="source",
                    field_schema=self.models.PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=name,
                    field_name="doc_type",
                    field_schema=self.models.PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=name,
                    field_name="act",
                    field_schema=self.models.PayloadSchemaType.KEYWORD,
                )
            except Exception as exc:
                logger.error(f"Failed to create collection '{name}': {exc}")

        return True

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        collection_name: str | None = None,
        batch_size: int = 100,
    ) -> int:
        """Batch upsert embedded chunks into Qdrant.

        Args:
            chunks: List of chunk dicts with 'embedding' and 'text' keys.
            collection_name: Target collection name.
            batch_size: Number of points per upsert batch.

        Returns:
            Number of points upserted.
        """
        if not self.is_available():
            logger.warning("Qdrant unavailable, skipping upsert.")
            return 0

        collection = collection_name or settings.QDRANT_COLLECTION_DOCS

        points = []
        for chunk in chunks:
            if "embedding" not in chunk:
                continue

            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk.get("text", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "source": chunk.get("metadata", {}).get("source", ""),
                "doc_type": chunk.get("metadata", {}).get("doc_type", ""),
                "act": chunk.get("metadata", {}).get("act", ""),
            }

            points.append(
                self.models.PointStruct(
                    id=point_id,
                    vector=chunk["embedding"],
                    payload=payload,
                )
            )

        total = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                self._client.upsert(
                    collection_name=collection,
                    points=batch,
                )
                total += len(batch)
            except Exception as exc:
                logger.error(f"Qdrant upsert batch failed: {exc}")

        logger.info(f"Upserted {total} points to Qdrant collection '{collection}'")
        return total

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        collection_name: str | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks in Qdrant.

        Args:
            query_vector: The query embedding vector.
            top_k: Number of results to return.
            collection_name: Collection to search.
            filter_conditions: Optional payload filters.

        Returns:
            List of result dicts with text, score, and metadata.
        """
        if not self.is_available():
            logger.warning("Qdrant unavailable, returning empty results.")
            return []

        collection = collection_name or settings.QDRANT_COLLECTION_DOCS

        try:
            # Build filter if conditions provided
            query_filter = None
            if filter_conditions:
                from qdrant_client.http import models as rest

                conditions = []
                for field, value in filter_conditions.items():
                    conditions.append(
                        rest.FieldCondition(
                            key=field,
                            match=rest.MatchValue(value=value),
                        )
                    )
                if conditions:
                    query_filter = rest.Filter(must=conditions)

            results = self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )

            return [
                {
                    "id": str(r.id),
                    "text": r.payload.get("text", ""),
                    "score": float(r.score),
                    "source": r.payload.get("source", ""),
                    "doc_type": r.payload.get("doc_type", ""),
                    "act": r.payload.get("act", ""),
                    "chunk_index": r.payload.get("chunk_index", 0),
                }
                for r in results
            ]
        except Exception as exc:
            logger.error(f"Qdrant search failed: {exc}")
            return []

    def search_batch(
        self,
        query_vectors: list[list[float]],
        top_k: int = 10,
        collection_name: str | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Batch search with multiple query vectors.

        Args:
            query_vectors: List of query embedding vectors.
            top_k: Number of results per query.
            collection_name: Collection to search.

        Returns:
            List of result lists, one per query vector.
        """
        if not self.is_available():
            return [[] for _ in query_vectors]

        collection = collection_name or settings.QDRANT_COLLECTION_DOCS

        try:
            results = self._client.search_batch(
                collection_name=collection,
                requests=[
                    self.models.SearchRequest(
                        vector=qv,
                        limit=top_k,
                        with_payload=True,
                    )
                    for qv in query_vectors
                ],
            )

            formatted: list[list[dict[str, Any]]] = []
            for batch_results in results:
                formatted.append([
                    {
                        "id": str(r.id),
                        "text": r.payload.get("text", ""),
                        "score": float(r.score),
                        "source": r.payload.get("source", ""),
                    }
                    for r in batch_results
                ])
            return formatted
        except Exception as exc:
            logger.error(f"Qdrant batch search failed: {exc}")
            return [[] for _ in query_vectors]

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a Qdrant collection."""
        if not self.is_available():
            return False
        try:
            self._client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to delete collection '{collection_name}': {exc}")
            return False

    def get_collection_info(self, collection_name: str | None = None) -> dict[str, Any]:
        """Get collection statistics."""
        if not self.is_available():
            return {"status": "unavailable"}

        collection = collection_name or settings.QDRANT_COLLECTION_DOCS
        try:
            info = self._client.get_collection(collection_name=collection)
            return {
                "name": collection,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": "active",
            }
        except Exception:
            return {"name": collection, "status": "not_found"}


# Singleton
_qdrant_manager: QdrantManager | None = None


def get_qdrant_manager() -> QdrantManager:
    """Get or create the singleton QdrantManager."""
    global _qdrant_manager
    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()
    return _qdrant_manager
