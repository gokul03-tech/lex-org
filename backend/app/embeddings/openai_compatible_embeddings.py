"""OpenAI-compatible embedding client for cloud embedding models (e.g. SiliconFlow BGE-M3).

This client implements a minimal subset compatible with how the codebase uses embeddings:
- encode(texts) -> np.ndarray (n_texts, dim)
- encode_queries/encode_documents similar to BGEM3Embedder
- get_dimension() -> int

It targets OpenAI-compatible /v1/embeddings endpoints. For BGE-M3 on SiliconFlow
the model id is typically "BAAI/bge-m3".
"""
from __future__ import annotations

from typing import Any

import httpx
import numpy as np


class OpenAICompatibleEmbeddings:
    def __init__(
        self,
        api_base: str,
        api_key: str = "",
        model_id: str = "BAAI/bge-m3",
        vector_size: int = 1024,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.vector_size = vector_size
        self.timeout = timeout

    def _request(self, texts: list[str]) -> np.ndarray:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        payload: dict[str, Any] = {
            "model": self.model_id,
            "input": texts,
        }
        # Some endpoints ignore dimensions; BGE-M3 dim is fixed 1024.
        url = f"{self.api_base}/embeddings"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"Embeddings API error {resp.status_code}: {resp.text}")
            data = resp.json()
        # OpenAI format: data[*].embedding
        embs = []
        for item in data.get("data", []):
            embs.append(np.array(item.get("embedding", []), dtype=np.float32))
        arr = np.stack(embs, axis=0) if embs else np.zeros(
            (len(texts), self.vector_size), dtype=np.float32
        )
        return arr

    def encode(self, texts: str | list[str], normalize: bool = True) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return np.zeros((0, self.vector_size), dtype=np.float32)
        # Batch if large? simple loop not needed; API accepts list
        arr = self._request(texts)
        if normalize and arr.shape[0] > 0:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms < 1e-8] = 1.0
            arr = arr / norms
        return arr.astype(np.float32)

    def encode_queries(self, queries: list[str]) -> np.ndarray:
        # BGE-M3 benefits from query instruction in local ST; for API many providers accept raw.
        # Use same as local: "Represent this sentence for searching relevant passages: {q}"
        instructed = [
            f"Represent this sentence for searching relevant passages: {q}" for q in queries
        ]
        return self.encode(instructed)

    def encode_documents(self, documents: list[str]) -> np.ndarray:
        return self.encode(documents)

    def get_dimension(self) -> int:
        return self.vector_size
