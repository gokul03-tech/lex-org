#!/usr/bin/env python3
"""Re-derive correct Qdrant payloads for the ingested ``json_output`` corpus.

``embed_and_upsert.py`` originally read ``document_type`` from ``metadata``
(where it does not exist) so every corpus point landed with
``doc_type="act"`` and ``act="Unknown"``.  The corpus actually stores the
values at the record top level (``document_type``/``source_type``) and inside
``metadata`` (``act_name``/``court``).

This script recomputes the payload per source file and updates the existing
points in place with ``set_payload`` -- no re-embedding, no re-upsert.

Usage:
    python fix_corpus_metadata.py --dry-run
    python fix_corpus_metadata.py
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

from loguru import logger
from qdrant_client import QdrantClient

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.environ.get("LEXORCH_JSON_INPUT_DIR", os.path.join(REPO_ROOT, "json_output"))
COLLECTION = "legal_documents"


def _load(file_path: str) -> list[dict]:
    with open(file_path, encoding="utf-8", errors="ignore") as handle:
        raw = handle.read()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        records = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records


def build_source_payloads(input_dir: str) -> dict[str, dict]:
    """Map each corpus source filename to its corrected payload fields."""
    doc_types: dict[str, Counter] = defaultdict(Counter)
    source_types: dict[str, Counter] = defaultdict(Counter)
    acts: dict[str, Counter] = defaultdict(Counter)
    courts: dict[str, Counter] = defaultdict(Counter)

    files = [
        os.path.join(root, name)
        for root, _dirs, names in os.walk(input_dir)
        for name in names
        if name.endswith((".json", ".jsonl"))
    ]
    files.sort()

    for file_path in files:
        if "graph" in file_path.lower() or "edges" in file_path.lower():
            continue
        for record in _load(file_path):
            text = record.get("text")
            if not text or len(str(text).strip()) < 10:
                continue
            metadata = record.get("metadata") or {}
            source = metadata.get("filename") or os.path.basename(file_path)
            doc_types[source][record.get("document_type")] += 1
            source_types[source][record.get("source_type")] += 1
            acts[source][metadata.get("act_name")] += 1
            courts[source][metadata.get("court")] += 1

    payloads: dict[str, dict] = {}
    for source in doc_types:
        doc_type = doc_types[source].most_common(1)[0][0]
        source_type = source_types[source].most_common(1)[0][0]
        act_names = sorted({a for a in acts[source] if a})
        court = next((c for c, _ in courts[source].most_common() if c), None)
        payloads[source] = {
            "doc_type": doc_type or "act",
            "act": "/".join(act_names) if act_names else "Unknown",
            "source_type": source_type,
            "court": court,
        }
    return payloads


def _collect_point_ids_by_source(client: QdrantClient) -> dict[str, list]:
    by_source: dict[str, list] = defaultdict(list)
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=10000,
            offset=offset,
            with_payload=["source"],
            with_vectors=False,
        )
        for point in points:
            source = (point.payload or {}).get("source")
            if source:
                by_source[source].append(point.id)
        if offset is None:
            break
    return by_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix corpus payload metadata in Qdrant.")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = parser.parse_args()

    logger.info(f"Scanning corpus at {INPUT_DIR} ...")
    source_payloads = build_source_payloads(INPUT_DIR)
    logger.info(f"Derived corrected payloads for {len(source_payloads)} sources")

    client = QdrantClient("http://localhost:6333", check_compatibility=False)
    by_source = _collect_point_ids_by_source(client)
    logger.info(f"Qdrant has {len(by_source)} distinct sources")

    to_update = [s for s in source_payloads if s in by_source]
    total_points = sum(len(by_source[s]) for s in to_update)
    missing = [s for s in source_payloads if s not in by_source]
    logger.info(
        f"Will update {len(to_update)} sources ({total_points} points); "
        f"{len(missing)} corpus sources absent from Qdrant"
    )
    if missing[:5]:
        logger.info(f"  e.g. absent: {missing[:5]}")

    if args.dry_run:
        for source in to_update[:3]:
            logger.info(f"  sample {source!r} -> {source_payloads[source]}")
        logger.info("Dry run complete; no changes written.")
        return 0

    updated = 0
    for i, source in enumerate(to_update, 1):
        try:
            client.set_payload(
                collection_name=COLLECTION,
                payload=source_payloads[source],
                points=by_source[source],
            )
            updated += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to update source {source!r}: {exc}")
        if i % 500 == 0:
            logger.info(f"  updated {i}/{len(to_update)} sources ...")

    logger.info(f"Updated payloads for {updated}/{len(to_update)} sources")
    info = client.get_collection(COLLECTION)
    logger.info(f"Collection now has {info.points_count} points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
