#!/usr/bin/env python3
"""Restore full payloads for the ingested ``json_output`` corpus.

The earlier ``fix_corpus_metadata.py`` used ``set_payload`` while the installed
qdrant client (1.18) and server (1.10) versions differ; the call *replaced*
payloads instead of merging.  As a result some points lost ``text`` /
``chunk_index`` / ``source``.

This script deterministically replays the corpus (same order and chunking as
``embed_and_upsert.py``, which reproduces the exact point IDs) and rewrites the
complete payload for every corpus point over the REST API.  No re-embedding is
performed.

Usage:
    python restore_corpus_payloads.py --dry-run
    python restore_corpus_payloads.py --limit 500
    python restore_corpus_payloads.py
"""

import argparse
import asyncio
import json
import os
import uuid

import httpx
from loguru import logger

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.environ.get("LEXORCH_JSON_INPUT_DIR", os.path.join(REPO_ROOT, "json_output"))
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = "legal_documents"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
SEPARATORS = ["\n\n", "\n", "Article ", "Section ", " ", ""]

BATCH = 2000
CONCURRENCY = 24


def _load_documents(file_path: str) -> list[dict]:
    content = open(file_path, encoding="utf-8", errors="ignore").read().strip()
    if not content:
        return []
    try:
        data = json.loads(content)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        pass
    records = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _get_text(doc: dict) -> str:
    if doc.get("text"):
        return doc["text"]
    if "question" in doc and "answer" in doc:
        return f"Q: {doc['question']}\nA: {doc['answer']}"
    if doc.get("section_text"):
        return doc["section_text"]
    return ""


def iter_payloads(limit: int | None = None):
    """Yield ``(point_id, full_payload)`` for every corpus chunk."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=SEPARATORS
    )

    all_files = []
    for root, _dirs, filenames in os.walk(INPUT_DIR):
        for filename in filenames:
            if filename.endswith((".json", ".jsonl")):
                all_files.append(os.path.join(root, filename))

    total = 0
    emitted = 0
    for file_path in all_files:
        if "graph" in file_path.lower() or "edges" in file_path.lower():
            continue
        for doc_index, doc in enumerate(_load_documents(file_path)):
            text = _get_text(doc)
            metadata = doc.get("metadata") or {}
            doc_id = doc.get("id") or f"doc_{doc_index}"
            if not text or len(text.strip()) < 10:
                continue
            base = {
                "source": metadata.get("filename")
                or metadata.get("source")
                or os.path.basename(file_path),
                "doc_type": doc.get("document_type") or metadata.get("doc_type") or "act",
                "act": metadata.get("act_name") or metadata.get("act") or "Unknown",
                "source_type": doc.get("source_type"),
                "court": metadata.get("court"),
            }
            for chunk_index, chunk in enumerate(splitter.split_text(text)):
                unique_str = f"{file_path}_{doc_id}_chunk_{chunk_index}_{total}"
                total += 1
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))
                payload = {"text": chunk, "chunk_index": chunk_index, **base}
                yield point_id, payload
                emitted += 1
                if limit is not None and emitted >= limit:
                    return


async def _put(client: httpx.AsyncClient, sem: asyncio.Semaphore, point_id: str, payload: dict):
    async with sem:
        resp = await client.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/payload",
            params={"wait": "false"},
            json={"payload": payload, "points": [point_id]},
        )
        return resp.status_code


async def _run(limit: int | None) -> tuple[int, int]:
    sem = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY * 2, max_keepalive_connections=CONCURRENCY)
    ok = fail = 0
    batch: list[tuple[str, dict]] = []

    async def flush(pending: list[tuple[str, dict]]) -> tuple[int, int]:
        results = await asyncio.gather(
            *[_put(client, sem, pid, pl) for pid, pl in pending], return_exceptions=True
        )
        good = sum(1 for r in results if isinstance(r, int) and r < 400)
        return good, len(results) - good

    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        for point_id, payload in iter_payloads(limit):
            batch.append((point_id, payload))
            if len(batch) >= BATCH:
                g, b = await flush(batch)
                ok += g
                fail += b
                batch = []
                if (ok + fail) % 50000 < BATCH:
                    logger.info(f"  restored {ok + fail} points (failures={fail}) ...")
        if batch:
            g, b = await flush(batch)
            ok += g
            fail += b
    return ok, fail


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore full corpus payloads in Qdrant.")
    parser.add_argument("--dry-run", action="store_true", help="count payloads without writing")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N chunks")
    args = parser.parse_args()

    if args.dry_run:
        n = sum(1 for _ in iter_payloads(limit=10))
        logger.info(f"Dry run: first {n} payloads built successfully")
        for point_id, payload in list(iter_payloads(limit=1)):
            logger.info(
                f"  sample id={point_id} payload_keys={list(payload)} "
                f"text[:60]={payload['text'][:60]!r}"
            )
        return 0

    ok, fail = asyncio.run(_run(args.limit))
    logger.info(f"Restored {ok} payloads; {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
