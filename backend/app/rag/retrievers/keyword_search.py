"""Keyword-based BM25/TF-IDF retriever.

Provides lexical search over chunked legal corpus
as a complement to dense vector search.
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Any

from loguru import logger


class KeywordRetriever:
    """BM25-inspired keyword search for legal retrieval.

    Uses a simple scoring function based on term frequency
    and inverse document frequency for rapid keyword matching.
    Works without external dependencies and serves as
    a strong baseline alongside vector search.
    """

    def __init__(self) -> None:
        self._corpus: list[dict[str, Any]] = []
        self._df: dict[str, int] = {}  # Document frequency
        self._avgdl: float = 0.0
        self._k1: float = 1.5
        self._b: float = 0.75

    def index(self, documents: list[dict[str, Any]]) -> None:
        """Index a list of document chunks for keyword search.

        Args:
            documents: List of dicts with 'text' key.
        """
        self._corpus = documents
        self._df = {}
        total_length = 0

        for doc in documents:
            text = doc.get("text", "")
            total_length += len(text.split())
            terms = set(self._tokenize(text))
            for term in terms:
                self._df[term] = self._df.get(term, 0) + 1

        self._avgdl = total_length / max(len(documents), 1)
        logger.info(f"Keyword index built: {len(documents)} docs, {len(self._df)} unique terms")

    async def search(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Search indexed documents using BM25 scoring.

        Args:
            query: Search query.
            top_k: Max results.

        Returns:
            Ranked result dicts with scores.
        """
        start_time = time.monotonic()

        if not self._corpus:
            logger.warning("Keyword index empty, returning no results")
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        N = len(self._corpus)
        scores: list[tuple[int, float]] = []

        for idx, doc in enumerate(self._corpus):
            text = doc.get("text", "")
            doc_terms = self._tokenize(text)
            doc_len = len(doc_terms)

            term_freqs = Counter(doc_terms)
            score = 0.0

            for term in query_terms:
                if term not in self._df:
                    continue
                tf = term_freqs.get(term, 0)
                df = self._df.get(term, 0)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

                # BM25 term score
                numerator = tf * (self._k1 + 1)
                denominator = tf + self._k1 * (1 - self._b + self._b * doc_len / self._avgdl)
                score += idf * numerator / denominator

            if score > 0:
                scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results: list[dict[str, Any]] = []
        for idx, score in scores[:top_k]:
            doc = self._corpus[idx]
            results.append({
                "text": doc.get("text", "")[:500],
                "score": float(score),
                "source": "keyword",
                "metadata": {
                    **doc.get("metadata", {}),
                    "bm25_score": float(score),
                },
            })

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"Keyword search returned {len(results)} results in {duration_ms:.0f}ms")
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into normalized terms.

        Args:
            text: Input text.

        Returns:
            List of lowercase tokens.
        """
        # Lowercase
        text = text.lower()
        # Remove punctuation except legal symbols
        text = re.sub(r"[^a-z0-9\s\-/]", " ", text)
        # Split on whitespace
        tokens = text.split()
        # Remove very short tokens and pure numbers
        tokens = [t for t in tokens if len(t) > 1 and not t.isdigit()]
        return tokens

    def search_raw_texts(
        self,
        query: str,
        texts: list[str],
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Search a list of raw texts without building an index first.

        Args:
            query: Search query.
            texts: List of text strings.
            top_k: Max results.

        Returns:
            Ranked result dicts.
        """
        docs = [{"text": t, "metadata": {}} for t in texts]
        self.index(docs)
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.search(query, top_k)
        )
