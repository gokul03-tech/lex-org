"""Maintenance tool: purge orphaned / duplicate uploaded-document vectors from Qdrant.

Modes:
1. Orphan removal (default): removes every point tagged
   doc_type="uploaded_document" whose `source` filename no longer belongs to a
   live document row in SQLite.
2. Excess rebuild (--rebuild-excess): for sources whose point count exceeds
   what the live DB rows justify (stale duplicates from repeated test uploads
   of the same file), purges ALL their points and re-indexes directly from the
   DB page texts using the same pipeline as case_understanding_agent.

Corpus points (acts, constitution, etc.) are never touched.

Usage (from backend/ with venv active):
    python scripts/cleanup_orphan_vectors.py [--dry-run] [--rebuild-excess]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client.models import FieldCondition, Filter, MatchAny  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.embeddings.qdrant_client import get_qdrant_manager  # noqa: E402

DB_PATH = Path("data/lexorch.db")
# A live document may legitimately be indexed once per analysis run per case.
# Anything beyond (rows * 8) chunks is considered stale duplicate pollution.
CHUNK_HEADROOM = 8


def _live_filenames(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT DISTINCT filename FROM documents")}


def _scan_source_counts(manager) -> dict[str, int]:
    scroll_filter = Filter(
        must=[FieldCondition(key="doc_type", match=MatchAny(any=["uploaded_document"]))]
    )
    source_counts: dict[str, int] = {}
    offset = None
    while True:
        points, offset = manager.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_DOCS,
            scroll_filter=scroll_filter,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            break
        for p in points:
            src = p.payload.get("source", "")
            source_counts[src] = source_counts.get(src, 0) + 1
        if offset is None:
            break
    return source_counts


def _purge_sources(manager, sources: list[str]) -> None:
    for i in range(0, len(sources), 50):
        batch = sources[i : i + 50]
        manager.client.delete(
            collection_name=settings.QDRANT_COLLECTION_DOCS,
            points_selector=Filter(
                must=[
                    FieldCondition(key="doc_type", match=MatchAny(any=["uploaded_document"])),
                    FieldCondition(key="source", match=MatchAny(any=batch)),
                ]
            ),
        )


def _rebuild_source_from_db(manager, conn: sqlite3.Connection, filename: str) -> int:
    """Re-index a filename's chunks from DB page texts, mirroring the agent."""
    from app.document_pipeline.chunker import LegalChunker
    from app.document_pipeline.embedder import EmbeddingGenerator

    chunker = LegalChunker()
    embedder = EmbeddingGenerator()
    total = 0

    rows = conn.execute(
        "SELECT case_id, filename, metadata_, parsed_text FROM documents WHERE filename = ?",
        (filename,),
    ).fetchall()

    for case_id, fname, meta_json, parsed_text in rows:
        meta = json.loads(meta_json or "{}")
        pages = meta.get("pages") or ([parsed_text] if parsed_text else [])
        if not pages:
            continue

        chunks = chunker.chunk_pages(pages, {"filename": fname, "case_id": case_id})
        if not chunks:
            continue
        chunks = embedder.embed_chunks(chunks)

        qdrant_chunks = [
            {
                "text": c["text"],
                "embedding": c["embedding"],
                "metadata": {
                    "case_id": case_id,
                    "doc_type": "uploaded_document",
                    "filename": fname,
                    "page_number": c["metadata"]["page_number"],
                    "chunk_id": c["metadata"]["chunk_id"],
                    "source": fname,
                },
            }
            for c in chunks
        ]
        total += manager.upsert_chunks(
            qdrant_chunks,
            collection_name=settings.QDRANT_COLLECTION_DOCS,
            batch_size=25,
        )

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only report, don't delete")
    parser.add_argument(
        "--rebuild-excess",
        action="store_true",
        help="Purge and re-index sources whose vector count exceeds the live DB expectation",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH.resolve()}")
        return

    conn = sqlite3.connect(DB_PATH)
    live_filenames = _live_filenames(conn)
    print(f"Live document filenames in DB: {len(live_filenames)}")

    manager = get_qdrant_manager()
    if not manager.is_available():
        print("Qdrant unavailable — aborting.")
        return

    source_counts = _scan_source_counts(manager)
    scanned = sum(source_counts.values())
    print(f"Scanned {scanned} uploaded_document points across {len(source_counts)} sources")

    # ── Mode 1: orphaned sources (no live DB rows at all) ──────────
    orphans = {s: n for s, n in source_counts.items() if s not in live_filenames}
    print(f"Orphaned sources: {len(orphans)} | orphaned points: {sum(orphans.values())}")
    for src, count in sorted(orphans.items(), key=lambda kv: -kv[1])[:20]:
        print(f"  - {src}: {count} points")

    # ── Mode 2: live filenames carrying stale duplicates ───────────
    excess: dict[str, int] = {}
    if args.rebuild_excess:
        for src, n in source_counts.items():
            if src not in live_filenames:
                continue
            db_rows = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE filename = ?", (src,)
            ).fetchone()[0]
            expected_max = max(db_rows * CHUNK_HEADROOM, CHUNK_HEADROOM)
            if n > expected_max:
                excess[src] = n
                print(f"  [excess] {src}: {n} points for {db_rows} DB row(s) (max expected {expected_max})")

    if args.dry_run:
        print("Dry run — nothing deleted.")
        conn.close()
        return

    # Delete true orphans
    if orphans:
        _purge_sources(manager, list(orphans))
        print(f"Deleted {sum(orphans.values())} orphaned points.")

    # Rebuild polluted live sources from DB truth
    for src in excess:
        print(f"Rebuilding index for '{src}' from DB...")
        _purge_sources(manager, [src])
        rebuilt = _rebuild_source_from_db(manager, conn, src)
        print(f"  Rebuilt '{src}': {rebuilt} points")

    if not orphans and not excess:
        print("Nothing to clean.")

    conn.close()


if __name__ == "__main__":
    main()
