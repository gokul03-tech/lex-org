"""Pluggable embedding factory with cloud + local fallback.

Provides a unified interface used across the app:
- get_embedder() returns an object with encode(), encode_queries(),
  encode_documents(), get_dimension()
- EMBEDDING_BACKEND: "cloud" | "local" | "auto" (default)
- Cloud uses OpenAI-compatible BGE-M3 (SiliconFlow by default)
- Local falls back to BGEM3Embedder (sentence-transformers)
"""
from __future__ import annotations

from typing import Any, Protocol

import numpy as np
from loguru import logger

from app.core.config import settings


class EmbedderProto(Protocol):
    def load(self) -> bool: ...
    def encode(self, texts: str | list[str], normalize: bool = True) -> np.ndarray: ...
    def encode_queries(self, queries: list[str]) -> np.ndarray: ...
    def encode_documents(self, documents: list[str]) -> np.ndarray: ...
    def get_dimension(self) -> int: ...


class _LocalBGEM3:
    def __init__(self) -> None:
        from app.embeddings.bge_m3 import BGEM3Embedder

        self._impl = BGEM3Embedder()
        self._impl.load()

    def load(self) -> bool:
        return self._impl.load()

    def encode(self, texts: str | list[str], normalize: bool = True) -> np.ndarray:
        return self._impl.encode(texts, normalize=normalize)

    def encode_queries(self, queries: list[str]) -> np.ndarray:
        return self._impl.encode_queries(queries)

    def encode_documents(self, documents: list[str]) -> np.ndarray:
        return self._impl.encode_documents(documents)

    def get_dimension(self) -> int:
        return self._impl.get_dimension()


class _CloudEmb:
    def __init__(self) -> None:
        from app.embeddings.openai_compatible_embeddings import OpenAICompatibleEmbeddings

        self._impl = OpenAICompatibleEmbeddings(
            api_base=settings.EMBEDDING_API_BASE,
            api_key=settings.EMBEDDING_API_KEY,
            model_id=settings.EMBEDDING_CLOUD_MODEL or settings.EMBEDDING_MODEL_NAME,
            vector_size=settings.QDRANT_VECTOR_SIZE,
        )
        self._local: _LocalBGEM3 | None = None
        self._warned = False

    def _fallback(self) -> _LocalBGEM3:
        if self._local is None:
            self._local = _LocalBGEM3()
        if not self._warned:
            self._warned = True
            logger.warning(
                "Cloud embeddings failed; falling back to local BGE-M3 for this session."
            )
        return self._local

    def _call(self, fn_name: str, *args, **kwargs: Any) -> np.ndarray:
        if not getattr(settings, "EMBEDDING_ALLOW_LOCAL_FALLBACK", True):
            return getattr(self._impl, fn_name)(*args, **kwargs)
        try:
            return getattr(self._impl, fn_name)(*args, **kwargs)
        except Exception as exc:
            logger.warning(f"Cloud embedding '{fn_name}' failed: {exc}")
            return getattr(self._fallback(), fn_name)(*args, **kwargs)

    def load(self) -> bool:
        return True

    def encode(self, texts: str | list[str], normalize: bool = True) -> np.ndarray:
        return self._call("encode", texts, normalize=normalize)

    def encode_queries(self, queries: list[str]) -> np.ndarray:
        return self._call("encode_queries", queries)

    def encode_documents(self, documents: list[str]) -> np.ndarray:
        return self._call("encode_documents", documents)

    def get_dimension(self) -> int:
        return self._impl.get_dimension()


_emb: EmbedderProto | None = None


def get_embedder() -> EmbedderProto:
    global _emb
    if _emb is not None:
        return _emb

    backend = (getattr(settings, "EMBEDDING_BACKEND", "auto") or "auto").lower()
    if backend == "local":
        _emb = _LocalBGEM3()
        logger.info("Using local embedding backend (BGE-M3/sentence-transformers)")
        return _emb

    if backend == "cloud":
        try:
            _emb = _CloudEmb()
            logger.info("Using cloud embedding backend (OpenAI-compatible)")
            return _emb
        except Exception as exc:
            logger.error(f"Failed to init cloud embeddings: {exc}")
            raise

    # auto: try cloud if API key/base configured; else local
    has_cloud = bool(
        getattr(settings, "EMBEDDING_API_BASE", "") and getattr(settings, "EMBEDDING_API_KEY", "")
    )
    if has_cloud:
        try:
            _emb = _CloudEmb()
            logger.info("Using cloud embedding backend (OpenAI-compatible, auto)")
            return _emb
        except Exception as exc:
            logger.warning(f"Cloud embeddings init failed, falling back to local: {exc}")
            _emb = _LocalBGEM3()
            logger.info("Using local embedding backend (BGE-M3/sentence-transformers, fallback)")
            return _emb
    else:
        _emb = _LocalBGEM3()
        logger.info("Using local embedding backend (BGE-M3/sentence-transformers, default)")
        return _emb
