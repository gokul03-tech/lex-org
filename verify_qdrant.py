"""Verify the Qdrant legal corpus.

Three modes:
  1. default            -> collection info + an embedding search demo
  2. --corpus-check     -> also verify every ``json_output`` file/chunk is indexed
  3. --corpus-only      -> run only the corpus completeness check (no model load)

The completeness check is the source of truth for "is the whole corpus in
Qdrant?".  It compares the ``json_output`` tree (all sub-directories) against
the ``legal_documents`` collection using the exact same loader/splitter
settings as ``embed_and_upsert.py``:

  * Qdrant's ``source`` payload for corpus chunks is the record's
    ``metadata.filename`` (the original ``.html`` page name).
  * chunk counts use ``chunk_size=800`` / ``chunk_overlap=100`` and drop
    records whose text is shorter than 10 characters.
  * ``graph``/``edges`` files are skipped, matching the ingester.

Exits non-zero if any corpus filename is missing or the point total is short.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from loguru import logger
from qdrant_client import QdrantClient

COLLECTION_NAME = "legal_documents"
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT_DIR = os.environ.get(
    "LEXORCH_JSON_INPUT_DIR", os.path.join(_REPO_ROOT, "json_output")
)
DEFAULT_MODEL_DIR = os.environ.get(
    "LEXORCH_EMBEDDING_MODEL_DIR", os.path.join(_REPO_ROOT, "models", "bge-m3")
)

# Keep in lock-step with embed_and_upsert.py
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
SEPARATORS = ["\n\n", "\n", "Article ", "Section ", " ", ""]


def _load_records(file_path: str) -> list[dict]:
    """Load a corpus file (single JSON object/array or JSONL)."""
    with open(file_path, encoding="utf-8", errors="ignore") as handle:
        raw = handle.read()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        records: list[dict] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records


def _get_text(record: dict) -> str:
    if record.get("text"):
        return record["text"]
    if "question" in record and "answer" in record:
        return f"Q: {record['question']}\nA: {record['answer']}"
    if record.get("section_text"):
        return record["section_text"]
    return ""


def _iter_corpus_files(input_dir: str) -> list[str]:
    files = [
        os.path.join(root, name)
        for root, _dirs, names in os.walk(input_dir)
        for name in names
        if name.endswith((".json", ".jsonl"))
    ]
    files.sort()
    return files


def _scan_corpus(input_dir: str, count_chunks: bool) -> dict:
    """Walk the corpus and compute expected filenames (and chunk count)."""
    splitter = None
    if count_chunks:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=SEPARATORS,
        )

    files = _iter_corpus_files(input_dir)
    used = 0
    skipped = 0
    expected_filenames: set[str] = set()
    expected_chunks = 0

    for file_path in files:
        if "graph" in file_path.lower() or "edges" in file_path.lower():
            skipped += 1
            continue
        used += 1
        for record in _load_records(file_path):
            text = _get_text(record)
            if not text or len(text.strip()) < 10:
                continue
            filename = (record.get("metadata") or {}).get("filename")
            if filename:
                expected_filenames.add(filename)
            if splitter is not None:
                expected_chunks += len(splitter.split_text(text))

    return {
        "files_total": len(files),
        "files_used": used,
        "files_skipped": skipped,
        "expected_filenames": expected_filenames,
        "expected_chunks": expected_chunks,
    }


def _scan_qdrant(client: QdrantClient, collection_name: str) -> set[str]:
    """Return the set of distinct ``source`` payloads stored in Qdrant."""
    sources: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection_name,
            limit=10000,
            offset=offset,
            with_payload=["source"],
            with_vectors=False,
        )
        for point in points:
            source = (point.payload or {}).get("source")
            if source:
                sources.add(source)
        if offset is None:
            break
    return sources


def run_corpus_check(
    client: QdrantClient,
    collection_name: str = COLLECTION_NAME,
    input_dir: str | None = None,
    count_chunks: bool = True,
) -> bool:
    """Verify every ``json_output`` file/chunk is present in the collection."""
    input_dir = input_dir or DEFAULT_INPUT_DIR
    if not os.path.isdir(input_dir):
        logger.error(f"Corpus input directory not found: {input_dir}")
        return False

    scan = _scan_corpus(input_dir, count_chunks)
    logger.info(
        f"Corpus: {scan['files_total']} files "
        f"({scan['files_used']} used, {scan['files_skipped']} graph/edge skipped); "
        f"{len(scan['expected_filenames'])} distinct filenames"
        + (f"; {scan['expected_chunks']} expected chunks" if count_chunks else "")
    )

    sources = _scan_qdrant(client, collection_name)
    missing = scan["expected_filenames"] - sources
    logger.info(
        f"Qdrant '{collection_name}': {len(sources)} distinct sources indexed; "
        f"{len(missing)} corpus filenames missing"
    )
    if missing:
        logger.error(f"Missing filenames (first 10): {sorted(missing)[:10]}")

    complete = not missing

    if count_chunks:
        points = client.count(collection_name=collection_name, exact=True).count
        baseline = points - scan["expected_chunks"]
        logger.info(
            f"Points: {points} = {scan['expected_chunks']} corpus chunks "
            f"+ {baseline} baseline/other points"
        )
        if baseline < 0:
            complete = False

    logger.info("CORPUS COMPLETE" if complete else "CORPUS INCOMPLETE")
    return complete


def print_collection_info(client: QdrantClient, collection_name: str) -> None:
    try:
        info = client.get_collection(collection_name)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to retrieve collection '{collection_name}': {exc}")
        raise SystemExit(1)
    logger.info(f"Collection '{collection_name}' status: {info.status}")
    logger.info(f"Points: {info.points_count} | indexed vectors: {info.indexed_vectors_count}")


def search_demo(client: QdrantClient, model_dir: str) -> None:
    from FlagEmbedding import BGEM3FlagModel

    logger.info(f"Loading BGE-M3 model from {model_dir} on CUDA...")
    model = BGEM3FlagModel(model_dir, use_fp16=True, device="cuda")

    query_text = "What are the fundamental rights under the Constitution of India?"
    logger.info(f"Generating embedding for query: '{query_text}'...")
    query_vector = model.encode(
        query_text, return_dense=True, return_sparse=False, return_colbert_vecs=False
    )["dense_vecs"].tolist()

    logger.info("Searching in Qdrant...")
    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3,
        with_payload=True,
    ).points

    logger.info("--- Search Results ---")
    for idx, hit in enumerate(hits):
        print(f"\n[{idx + 1}] Score: {hit.score:.4f}")
        print(f"    File: {hit.payload.get('source')}")
        print(f"    Type: {hit.payload.get('doc_type')}")
        snippet = hit.payload.get("text", "")
        if len(text_snippet := snippet) > 300:
            text_snippet = text_snippet[:300] + "..."
        print(f"    Text snippet: {text_snippet}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the LexOrch Qdrant legal corpus.")
    parser.add_argument("--corpus-check", action="store_true", help="also run corpus completeness")
    parser.add_argument("--corpus-only", action="store_true", help="run only the corpus check")
    parser.add_argument(
        "--no-chunks", action="store_true", help="skip chunk counting (file-level check only)"
    )
    args = parser.parse_args()

    client = QdrantClient("http://localhost:6333", check_compatibility=False)

    if not args.corpus_only:
        print_collection_info(client, COLLECTION_NAME)

    exit_code = 0
    if args.corpus_check or args.corpus_only:
        complete = run_corpus_check(client, COLLECTION_NAME, count_chunks=not args.no_chunks)
        exit_code = 0 if complete else 1

    if args.corpus_only:
        sys.exit(exit_code)

    search_demo(client, DEFAULT_MODEL_DIR)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
