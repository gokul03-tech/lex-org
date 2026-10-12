#!/usr/bin/env python3
"""Recursively and idempotently import JSON/JSONL corpus records into Qdrant."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.core.config import settings
from app.document_pipeline.embedder import EmbeddingGenerator
from app.embeddings.qdrant_client import get_qdrant_manager

BATCH_SIZE = 64
EMBEDDING_BATCH_SIZE = 16
MAX_EMBEDDING_TOKENS = 256
CORPUS_NAMESPACE = uuid.UUID("82c4028b-44d2-42df-a9ef-5d34a8bf1c32")


class JSONToQdrantImporter:
    """Import every JSON or JSONL record below ``json_output``."""

    def __init__(self, json_output_root: Path | None = None):
        self.json_output_root = (json_output_root or settings.PROJECT_ROOT / "json_output").resolve()

    @staticmethod
    def _records(file_path: Path) -> Iterator[dict[str, Any]]:
        """Read JSON objects, arrays, or JSONL, skipping malformed lines explicitly."""
        try:
            with file_path.open("r", encoding="utf-8-sig") as stream:
                first = ""
                while not first:
                    char = stream.read(1)
                    if not char:
                        return
                    if not char.isspace():
                        first = char
                stream.seek(0)
                if first == "[":
                    parsed = json.load(stream)
                    if not isinstance(parsed, list):
                        raise ValueError("top-level JSON array expected")
                    for item in parsed:
                        if isinstance(item, dict):
                            yield item
                        else:
                            logger.warning("Ignoring non-object record in {}", file_path)
                    return
                if first != "{":
                    raise ValueError("JSON/JSONL file must contain object records")
                for line_num, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        # A pretty-printed single JSON object is supported too.
                        stream.seek(0)
                        parsed = json.load(stream)
                        if isinstance(parsed, dict):
                            yield parsed
                            return
                        raise
                    if isinstance(item, dict):
                        yield item
                    else:
                        logger.warning("Ignoring non-object record {}:{}", file_path, line_num)
        except (UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as exc:
            logger.error("Could not read JSON records from {}: {}", file_path, exc)
            raise

    @staticmethod
    def _legacy_source(file_path: Path, corpus_root: Path) -> tuple[str, str] | None:
        """Map files covered by the previous importer to its source label/collection."""
        parts = file_path.relative_to(corpus_root).parts
        if len(parts) >= 3 and parts[0] in {"acts", "constitution"}:
            return parts[1], settings.QDRANT_COLLECTION_DOCS
        if len(parts) >= 4 and parts[0] == "legal_corpus" and parts[1] in {"Supreme_Court", "highcourt"}:
            return parts[2], settings.QDRANT_COLLECTION_DOCS
        if len(parts) >= 3 and parts[0] == "legal_corpus" and parts[1] == "BNS_BNSS_BSA":
            return f"qa_{parts[2]}", settings.QDRANT_COLLECTION_SECTIONS
        return None

    @staticmethod
    def _record_text(record: dict[str, Any]) -> str:
        text = record.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        question, answer = record.get("question"), record.get("answer")
        if question is not None or answer is not None:
            return f"Question: {question or ''}\n\nAnswer: {answer or ''}".strip()
        # Preserve/search structured records that have no pre-rendered text.
        return json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)

    async def import_all(self) -> dict[str, int]:
        if not self.json_output_root.is_dir():
            raise FileNotFoundError(f"JSON corpus directory not found: {self.json_output_root}")

        files = sorted(
            path for path in self.json_output_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
        )
        if not files:
            raise FileNotFoundError(f"No JSON/JSONL files found under {self.json_output_root}")

        model_path = settings.MODELS_DIR / Path(settings.EMBEDDING_MODEL_NAME).name
        model_name = str(model_path) if (model_path / "config.json").exists() else settings.EMBEDDING_MODEL_NAME
        embedder = EmbeddingGenerator(model_name=model_name, batch_size=EMBEDDING_BATCH_SIZE)
        qdrant = get_qdrant_manager()
        if not qdrant.is_available():
            raise ConnectionError("Qdrant is unavailable; refusing to report a successful import")
        if not qdrant.create_collections():
            raise ConnectionError("Could not ensure the required Qdrant collections exist")

        # Reuse records already indexed by the earlier importer. Its payload stored
        # only source labels, so the source-to-file mapping below covers those labels;
        # new imports also store corpus_path for precise resumability.
        existing_sources: dict[str, set[str]] = {}
        for collection in (settings.QDRANT_COLLECTION_DOCS, settings.QDRANT_COLLECTION_SECTIONS):
            sources: set[str] = set()
            offset = None
            while True:
                # Keep pages small: hosted Qdrant may reset connections on large
                # scroll responses. Retry transient resets without losing progress.
                for attempt in range(5):
                    try:
                        points, offset = qdrant.client.scroll(
                            collection_name=collection,
                            limit=100,
                            offset=offset,
                            with_payload=["source", "corpus_path"],
                            with_vectors=False,
                        )
                        break
                    except Exception:
                        if attempt == 4:
                            raise
                        time.sleep(2 ** attempt)
                for point in points:
                    payload = point.payload or {}
                    if isinstance(payload.get("source"), str):
                        sources.add(payload["source"])
                if offset is None:
                    break
            existing_sources[collection] = sources

        stats = {"files_found": len(files), "files_processed": 0, "files_already_present": 0,
                 "records_read": 0, "points_upserted": 0, "errors": 0}
        batch: list[dict[str, Any]] = []
        for file_path in files:
            relative_path = file_path.relative_to(self.json_output_root).as_posix()
            legacy = self._legacy_source(file_path, self.json_output_root)
            covered_by_legacy = bool(legacy and legacy[0] in existing_sources[legacy[1]])
            if covered_by_legacy:
                try:
                    stats["records_read"] += sum(1 for _ in self._records(file_path))
                    stats["files_already_present"] += 1
                    continue
                except Exception:
                    stats["errors"] += 1
                    continue
            file_records = 0
            try:
                for index, record in enumerate(self._records(file_path)):
                    file_records += 1
                    text = self._record_text(record)
                    if not text:
                        continue

                    source_id = str(record.get("id") or index)
                    stable_key = f"{relative_path}\0{source_id}\0{index}"
                    point_id = str(uuid.uuid5(CORPUS_NAMESPACE, stable_key))
                    metadata = record.get("metadata")
                    metadata = metadata if isinstance(metadata, dict) else {}
                    doc_type = str(record.get("document_type") or metadata.get("document_type") or "legal_record")
                    collection = (
                        settings.QDRANT_COLLECTION_SECTIONS
                        if doc_type.casefold() in {"qa_pair", "section", "legal_section"}
                        else settings.QDRANT_COLLECTION_DOCS
                    )

                    # Preserve the original fields in Qdrant payload (text is stored once).
                    payload_fields = {k: v for k, v in record.items() if k != "text"}
                    payload_fields["metadata"] = metadata
                    batch.append({
                        "text": text,
                        "chunk_index": index,
                        "point_id": point_id,
                        "collection_name": collection,
                        "metadata": {
                            **payload_fields,
                            "source": legacy[0] if legacy else relative_path,
                            "corpus_path": relative_path,
                            "source_id": source_id,
                            "doc_type": doc_type,
                            "act": metadata.get("act_name") or metadata.get("act") or "",
                            "record_fingerprint": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        },
                    })
                    if len(batch) >= BATCH_SIZE:
                        stats["points_upserted"] += self._embed_and_upsert(batch, embedder, qdrant)
                        batch = []
                stats["records_read"] += file_records
                stats["files_processed"] += 1
                if stats["files_processed"] % 100 == 0:
                    logger.info("Progress: {}/{} files; {} records, {} points upserted",
                                stats["files_processed"], stats["files_found"],
                                stats["records_read"], stats["points_upserted"])
            except Exception as exc:
                stats["records_read"] += file_records
                stats["errors"] += 1
                logger.error("Failed to import {}: {}", relative_path, exc)

        if batch:
            stats["points_upserted"] += self._embed_and_upsert(batch, embedder, qdrant)
        logger.info("JSON corpus import finished: {}", stats)
        if stats["errors"]:
            raise RuntimeError(f"Import incomplete: {stats}")
        return stats

    @staticmethod
    def _embed_and_upsert(batch: list[dict[str, Any]], embedder: EmbeddingGenerator, qdrant) -> int:
        if getattr(embedder, "_backend", None) is None:
            embedder.model  # Initialize the configured model before processing the batch.
        if getattr(embedder, "_backend", None) != "sentence_transformers":
            raise RuntimeError(
                "A real sentence-transformers model is unavailable; refusing to index fallback/random vectors"
            )
        # The source corpus contains very long judgments. Keep inference aligned
        # with the project's existing 512-token embedding pipeline and avoid
        # the model's 8,192-token default on CPU.
        embedder.model.max_seq_length = min(embedder.model.max_seq_length, MAX_EMBEDDING_TOKENS)
        embedded = embedder.embed_chunks(batch)
        total = 0
        by_collection: dict[str, list[dict[str, Any]]] = {}
        for chunk in embedded:
            # embed_chunks mutates its input dictionaries; keep collection_name
            # intact so a failed write can safely be retried from the same batch.
            by_collection.setdefault(chunk["collection_name"], []).append(chunk)
        for collection, chunks in by_collection.items():
            upserted = 0
            for attempt in range(5):
                upserted = qdrant.upsert_chunks(chunks, collection_name=collection)
                if upserted == len(chunks):
                    break
                if attempt < 4:
                    logger.warning(
                        "Qdrant accepted {}/{} points for {}; retrying ({}/5)",
                        upserted, len(chunks), collection, attempt + 2,
                    )
                    time.sleep(2 ** attempt)
            if upserted != len(chunks):
                raise RuntimeError(
                    f"Qdrant accepted {upserted}/{len(chunks)} points for {collection}"
                )
            total += upserted
        return total


if __name__ == "__main__":
    asyncio.run(JSONToQdrantImporter().import_all())
