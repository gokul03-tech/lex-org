#!/usr/bin/env python3
"""Verify the configured embedding backend (cloud SiliconFlow + local fallback).

Reads .env / backend/.env, then reports which backend resolves and, when an API
key is present, performs a single real request against the OpenAI-compatible
/embeddings endpoint.

Usage:
    backend/.venv/bin/python check_embeddings.py
"""

from __future__ import annotations

import os

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def _load_env() -> None:
    for path in (os.path.join(_REPO_ROOT, ".env"), os.path.join(_REPO_ROOT, "backend", ".env")):
        if not os.path.exists(path):
            continue
        for raw in open(path, encoding="utf-8", errors="ignore"):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    _load_env()

    backend = os.environ.get("LEXORCH_EMBEDDING_BACKEND") or os.environ.get(
        "EMBEDDING_BACKEND", "auto"
    )
    api_base = os.environ.get("EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1").rstrip("/")
    model = os.environ.get("EMBEDDING_CLOUD_MODEL", "BAAI/bge-m3")
    key = os.environ.get("EMBEDDING_API_KEY", "")

    print(f"EMBEDDING_BACKEND     = {backend}")
    print(f"EMBEDDING_API_BASE    = {api_base}")
    print(f"EMBEDDING_CLOUD_MODEL = {model}")
    print(f"EMBEDDING_API_KEY     = {'set (' + str(len(key)) + ' chars)' if key else 'NOT SET'}")

    use_cloud = backend == "cloud" or (backend == "auto" and bool(key))
    if not use_cloud:
        print("\n-> resolves to LOCAL BGE-M3 (no cloud key, or EMBEDDING_BACKEND=local).")
        return 0

    try:
        import httpx
    except ImportError:
        print("\nhttpx not installed; run with backend/.venv/bin/python")
        return 1

    query = "What are the fundamental rights under the Constitution of India?"
    print(f"\nPOST {api_base}/embeddings  (model={model}) ...")
    try:
        resp = httpx.post(
            f"{api_base}/embeddings",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "input": [query]},
            timeout=30.0,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"REQUEST FAILED: {exc}")
        return 1

    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text[:400])
        return 1

    vec = resp.json()["data"][0]["embedding"]
    dim = len(vec)
    print(f"OK: cloud embedding returned dim={dim}")
    if dim != 1024:
        print(f"WARNING: expected dim 1024 (BGE-M3 / QDRANT_VECTOR_SIZE), got {dim}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
