"""BGE-M3 embedding model wrapper.

BGE-M3 is a multilingual embedding model from BAAI that supports
dense, sparse (lexical), and multi-vector (ColBERT) retrieval.
We use the dense embeddings for Qdrant vector search.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from loguru import logger

from app.core.config import settings


class BGEM3Embedder:
    """Wrapper around BGE-M3 for generating dense embeddings.

    Falls back to deterministic random embeddings when the model
    isn't available (for development/testing).
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.device = device or settings.EMBEDDING_DEVICE
        self.vector_size = settings.QDRANT_VECTOR_SIZE
        self._model = None
        self._loaded = False

    def load(self) -> bool:
        """Attempt to load the BGE-M3 model.

        Returns:
            True if model loaded successfully.
        """
        if self._loaded:
            return True

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            actual_dim = self._model.get_sentence_embedding_dimension()
            self.vector_size = actual_dim
            self._loaded = True
            logger.info(f"BGE-M3 loaded: dim={actual_dim}, device={self.device}")
            return True
        except ImportError:
            logger.warning("sentence-transformers not installed; using fallback embeddings.")
        except Exception as exc:
            logger.error(f"Failed to load BGE-M3: {exc}")

        self._loaded = True  # Mark as loaded so we don't retry
        return False

    def encode(self, texts: str | list[str], normalize: bool = True) -> np.ndarray:
        """Encode texts to dense embeddings.

        Args:
            texts: Single string or list of strings.
            normalize: Whether to L2-normalize embeddings.

        Returns:
            NumPy array of shape (n_texts, vector_size).
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.zeros((0, self.vector_size), dtype=np.float32)

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=normalize,
            )
            return np.array(embeddings, dtype=np.float32)

        # Fallback: deterministic pseudo-embeddings
        return self._fallback_encode(texts, normalize)

    def _fallback_encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        """Generate deterministic fallback embeddings."""
        embeddings = np.zeros((len(texts), self.vector_size), dtype=np.float32)
        for i, text in enumerate(texts):
            seed = abs(hash(text)) % (2**31)
            rng = np.random.RandomState(seed)
            vec = rng.randn(self.vector_size).astype(np.float32)
            if normalize:
                norm = np.linalg.norm(vec)
                if norm > 1e-8:
                    vec = vec / norm
            embeddings[i] = vec
        return embeddings

    def encode_queries(self, queries: list[str]) -> np.ndarray:
        """Encode search queries.

        Uses the query instruction prefix for BGE-M3 when available,
        which improves retrieval quality.
        """
        if self._model is not None:
            # Add query instruction for BGE-M3
            instructed = [
                f"Represent this sentence for searching relevant passages: {q}"
                for q in queries
            ]
            return self.encode(instructed)
        return self.encode(queries)

    def encode_documents(self, documents: list[str]) -> np.ndarray:
        """Encode document passages for indexing."""
        return self.encode(documents)

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self.vector_size


# Singleton
_bge_m3: BGEM3Embedder | None = None


def get_bge_m3() -> BGEM3Embedder:
    """Get or create the singleton BGE-M3 embedder."""
    global _bge_m3
    if _bge_m3 is None:
        _bge_m3 = BGEM3Embedder()
        _bge_m3.load()
    return _bge_m3
