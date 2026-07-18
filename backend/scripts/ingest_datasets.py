#!/usr/bin/env python3
"""Dataset ingestion script for LexOrch-KG.

Processes all available datasets:
1. Acts PDFs -> parse -> clean -> chunk -> embed -> Qdrant
2. GovIntel sections -> Neo4j Section nodes
3. GovIntel edges -> Neo4j relationships
4. BNS_BNSS_BSA QA pairs -> embed -> Qdrant + Neo4j QA nodes

Usage:
    python scripts/ingest_datasets.py [--acts-only] [--kg-only] [--qa-only]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from app.core.config import settings
from app.document_pipeline.parser import DocumentParser
from app.document_pipeline.cleaner import TextCleaner
from app.document_pipeline.chunker import LegalChunker
from app.document_pipeline.embedder import EmbeddingGenerator
from app.embeddings.qdrant_client import get_qdrant_manager


def setup_logging() -> None:
    """Configure logging for the ingestion script."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "logs/ingest_{time}.log",
        rotation="10 MB",
        level="DEBUG",
    )


# ── PDF / Acts Processing ────────────────────────────────────
def ingest_acts_pdfs() -> dict[str, int]:
    """Process all Acts PDFs into Qdrant.

    Returns:
        Dict with stats (files_processed, chunks_created, points_upserted).
    """
    logger.info("=" * 60)
    logger.info("Starting ACTS PDF ingestion...")

    acts_dir = settings.PROJECT_ROOT / settings.ACTS_DIR
    if not acts_dir.exists():
        logger.error(f"Acts directory not found: {acts_dir}")
        return {"files_processed": 0, "chunks_created": 0, "points_upserted": 0}

    parser = DocumentParser()
    cleaner = TextCleaner()
    chunker = LegalChunker()
    embedder = EmbeddingGenerator()
    qdrant = get_qdrant_manager()

    # Create collections
    qdrant.create_collections()

    stats = {"files_processed": 0, "chunks_created": 0, "points_upserted": 0}
    pdf_files = list(acts_dir.glob("*.pdf"))

    logger.info(f"Found {len(pdf_files)} PDF files in {acts_dir}")

    for pdf_path in pdf_files:
        try:
            logger.info(f"Processing: {pdf_path.name}")

            # Parse
            result = parser.parse(str(pdf_path))
            raw_text = result["text"]

            # Clean
            cleaned = cleaner.clean(raw_text)
            if not cleaned or len(cleaned) < 100:
                logger.warning(f"Skipping {pdf_path.name}: insufficient text ({len(cleaned)} chars)")
                continue

            # Chunk
            chunks = chunker.chunk_with_metadata(
                cleaned,
                source=pdf_path.name,
                doc_type="act",
                act=pdf_path.stem,
            )
            stats["chunks_created"] += len(chunks)
            logger.info(f"  Created {len(chunks)} chunks")

            # Embed
            chunks = embedder.embed_chunks(chunks)

            # Upsert to Qdrant
            upserted = qdrant.upsert_chunks(
                chunks,
                collection_name=settings.QDRANT_COLLECTION_DOCS,
            )
            stats["points_upserted"] += upserted
            stats["files_processed"] += 1

        except Exception as exc:
            logger.error(f"Failed to process {pdf_path.name}: {exc}")

    logger.info(f"Acts ingestion complete: {stats}")
    return stats


# ── GovIntel KG Import ───────────────────────────────────────
def ingest_govintel_kg() -> dict[str, int]:
    """Import GovIntel sections and edges into Neo4j.

    Returns:
        Dict with stats (sections, edges, cross_code_edges, judgment_edges).
    """
    logger.info("=" * 60)
    logger.info("Starting GovIntel KG ingestion...")

    try:
        from app.kg.neo4j_client import get_neo4j_client
    except ImportError as exc:
        logger.error(f"Cannot import neo4j_client: {exc}")
        return {"sections": 0, "edges": 0, "cross_code": 0, "judgment": 0}

    legal_corpus = settings.PROJECT_ROOT / settings.LEGAL_CORPUS_DIR
    sections_dir = legal_corpus / "GovIntel" / "sections"
    graph_dir = legal_corpus / "GovIntel" / "graph"

    stats = {"sections": 0, "edges": 0, "cross_code": 0, "judgment": 0}

    # Import sections
    section_files = {
        "bns_sections.json": "Bharatiya Nyaya Sanhita",
        "bnss_sections.json": "Bharatiya Nagarik Suraksha Sanhita",
        "bsa_sections.json": "Bharatiya Sakshya Adhiniyam",
        "ipc_sections.json": "Indian Penal Code",
    }

    async def _import() -> dict[str, int]:
        neo4j = await get_neo4j_client()
        connected = await neo4j.verify_connectivity()
        if not connected:
            logger.warning("Neo4j not available, skipping KG import.")
            return stats

        # Use the seed importer from the neo4j client
        result = await neo4j.seed_from_govintel()
        return result

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        stats = loop.run_until_complete(_import())
    except Exception as exc:
        logger.error(f"KG import failed: {exc}")

    logger.info(f"GovIntel KG ingestion complete: {stats}")
    return stats


# ── QA Dataset Import ────────────────────────────────────────
def ingest_qa_dataset() -> dict[str, int]:
    """Import BNS_BNSS_BSA QA pairs into Qdrant.

    Returns:
        Dict with stats (qa_pairs_processed, points_upserted).
    """
    logger.info("=" * 60)
    logger.info("Starting QA dataset ingestion...")

    legal_corpus = settings.PROJECT_ROOT / settings.LEGAL_CORPUS_DIR
    qa_file = legal_corpus / "BNS_BNSS_BSA" / "bns_bnss_bsa_combined_legal_qa.jsonl"

    if not qa_file.exists():
        qa_file = legal_corpus / "BNS_BNSS_BSA" / "bns_legal_qa.jsonl"
    if not qa_file.exists():
        logger.error(f"QA dataset not found at expected location")
        return {"qa_pairs": 0, "points_upserted": 0}

    embedder = EmbeddingGenerator()
    qdrant = get_qdrant_manager()
    qdrant.create_collections()

    stats = {"qa_pairs": 0, "points_upserted": 0}
    batch: list[dict[str, Any]] = []
    batch_size = 100

    with open(qa_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                qa = json.loads(line.strip())

                # Create chunk from QA pair
                chunk = {
                    "text": f"Q: {qa.get('question', '')}\nA: {qa.get('answer', '')}",
                    "chunk_index": line_num,
                    "metadata": {
                        "source": f"qa_{qa.get('act', 'BNS')}_{qa.get('section_number', '')}",
                        "doc_type": "qa_pair",
                        "act": qa.get("act", ""),
                        "section_number": qa.get("section_number", ""),
                        "question_type": qa.get("question_type", ""),
                    },
                }

                batch.append(chunk)
                stats["qa_pairs"] += 1

                if len(batch) >= batch_size:
                    # Embed and upsert batch
                    batch = embedder.embed_chunks(batch)
                    upserted = qdrant.upsert_chunks(
                        batch,
                        collection_name=settings.QDRANT_COLLECTION_SECTIONS,
                    )
                    stats["points_upserted"] += upserted
                    logger.info(f"  Processed {stats['qa_pairs']} QA pairs...")
                    batch = []

            except json.JSONDecodeError as exc:
                logger.warning(f"Skipping invalid JSON at line {line_num}: {exc}")
            except Exception as exc:
                logger.error(f"Error at line {line_num}: {exc}")

    # Final batch
    if batch:
        batch = embedder.embed_chunks(batch)
        upserted = qdrant.upsert_chunks(
            batch,
            collection_name=settings.QDRANT_COLLECTION_SECTIONS,
        )
        stats["points_upserted"] += upserted

    logger.info(f"QA dataset ingestion complete: {stats}")
    return stats


# ── Main ─────────────────────────────────────────────────────
def main() -> None:
    """Run dataset ingestion based on CLI flags."""
    parser = argparse.ArgumentParser(
        description="LexOrch-KG Dataset Ingestion Script",
    )
    parser.add_argument(
        "--acts-only",
        action="store_true",
        help="Only process Acts PDFs",
    )
    parser.add_argument(
        "--kg-only",
        action="store_true",
        help="Only import GovIntel KG data",
    )
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Only import QA dataset",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Process all datasets (default)",
    )
    args = parser.parse_args()

    setup_logging()

    # Determine what to run
    run_all = args.all and not (args.acts_only or args.kg_only or args.qa_only)
    run_acts = run_all or args.acts_only
    run_kg = run_all or args.kg_only
    run_qa = run_all or args.qa_only

    start_time = time.monotonic()

    all_stats: dict[str, Any] = {}

    if run_acts:
        all_stats["acts"] = ingest_acts_pdfs()

    if run_kg:
        all_stats["kg"] = ingest_govintel_kg()

    if run_qa:
        all_stats["qa"] = ingest_qa_dataset()

    elapsed = time.monotonic() - start_time
    logger.info("=" * 60)
    logger.info(f"Ingestion complete in {elapsed:.1f}s")
    logger.info(f"Summary: {json.dumps(all_stats, indent=2, default=str)}")


if __name__ == "__main__":
    main()
