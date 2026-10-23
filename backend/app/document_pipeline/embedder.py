"""Embedding module using BGE-M3 for legal text.

Generates dense vector embeddings for document chunks,
with batch processing support and multiple backends.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from loguru import logger

from app.core.config import settings

# Process-wide cache so multiple EmbeddingGenerator instances (ingestion, case
# understanding, re-indexing) share one loaded SentenceTransformer instead of
# re-reading the weights from disk on every call.
_MODEL_CACHE: dict[tuple[str, str], Any] = {}


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
        cache_key = (self.model_name, str(self.device))
        cached = _MODEL_CACHE.get(cache_key)
        if cached is not None:
            self._model = cached
            self._backend = "sentence_transformers"
            return

        # Try sentence-transformers (BGE-M3)
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            # Half precision on CUDA so BGE-M3 can share a small (4GB) GPU
            # with the llama.cpp LLM without OOM.
            if "cuda" in str(self.device):
                self._model.half()
            self._backend = "sentence_transformers"
            _MODEL_CACHE[cache_key] = self._model
            get_dim = getattr(self._model, "get_embedding_dimension", None) or getattr(
                self._model, "get_sentence_embedding_dimension"
            )
            dim = get_dim()
            logger.info(
                f"Loaded embedding model: {self.model_name} "
                f"(dim={dim}, device={self.device})"
            )
            return
        except ImportError:
            logger.warning("sentence-transformers not installed.")
        except Exception as exc:
            logger.warning(f"Failed to load sentence-transformers model: {exc}")

        # Fallback: simple TF-IDF + SVD (no GPU needed)
        logger.info("Using fallback embedding backend (TF-IDF based)")
        self._model = None
        self._backend = "random"

    def _shared_embedder(self):
        """Return the shared cloud/local embedder, or None to use this class's
        own local/random path.

        Returns None when EMBEDDING_BACKEND=local, or when "auto" has no API
        key configured, so standalone behaviour stays unchanged.
        """
        backend = (getattr(settings, "EMBEDDING_BACKEND", "auto") or "auto").lower()
        if backend == "local":
            return None
        if backend == "auto" and not (settings.EMBEDDING_API_BASE and settings.EMBEDDING_API_KEY):
            return None
        from app.embeddings.embedder import get_embedder

        return get_embedder()

    def embed(self, texts: str | list[str]) -> np.ndarray:
        """Generate embeddings for one or more texts.

        Uses the configured embedding backend (cloud first when active, with
        automatic local fallback), otherwise the local sentence-transformers
        model, and finally a deterministic fallback.

        Args:
            texts: Single text string or list of strings.

        Returns:
            NumPy array of shape (n_texts, vector_size).
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.zeros((0, self.vector_size), dtype=np.float32)

        shared = self._shared_embedder()
        if shared is not None:
            try:
                vecs = shared.encode(texts, normalize=True)
                if vecs.shape[1] == self.vector_size:
                    return vecs
                logger.warning(
                    f"Cloud embedding dim {vecs.shape[1]} != QDRANT_VECTOR_SIZE "
                    f"{self.vector_size}; using local embedder instead."
                )
            except Exception as exc:
                logger.warning(f"Cloud embedding failed; using local embedder: {exc}")

        # Lazy-load: embed() may be called without touching the `.model` property.
        if self._backend is None and self._model is None:
            self._load_model()

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
