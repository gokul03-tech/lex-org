#!/usr/bin/env python3
"""JSON Output to Qdrant Ingestor.
Imports processed legal data from json_output folder into Qdrant vector store.
"""

import json
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.core.config import settings
from app.document_pipeline.embedder import EmbeddingGenerator
from app.embeddings.qdrant_client import get_qdrant_manager

class JSONToQdrantImporter:
    """Imports data from json_output into Qdrant."""

    def __init__(self, json_output_root: Path | None = None):
        self.json_output_root = json_output_root or (
            settings.PROJECT_ROOT / "json_output"
        )
        self.logger = logger

    def _load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load a JSONL file (one JSON object per line)."""
        objects = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        objects.append(obj)
                    except json.JSONDecodeError as exc:
                        self.logger.warning(f"Failed to parse line {line_num} in {file_path}: {exc}")
                        continue
        except Exception as exc:
            self.logger.error(f"Failed to read file {file_path}: {exc}")
        return objects

    async def import_all(self) -> Dict[str, int]:
        """Import all json_output data into Qdrant."""
        self.logger.info("Starting import of ALL json_output data into Qdrant...")

        embedder = EmbeddingGenerator()
        qdrant = get_qdrant_manager()
        qdrant.create_collections()

        stats = {"points_upserted": 0, "files_processed": 0, "errors": 0}

        # 1. Import Acts, Constitution, and Court Judgments (to COLLECTION_DOCS)
        paths_to_docs = [
            self.json_output_root / "acts",
            self.json_output_root / "constitution",
            self.json_output_root / "legal_corpus" / "Supreme_Court",
            self.json_output_root / "legal_corpus" / "highcourt"
        ]

        for base_path in paths_to_docs:
            if not base_path.exists():
                continue

            for doc_dir in base_path.iterdir():
                if not doc_dir.is_dir():
                    continue

                data_file = doc_dir / "data.json"
                if not data_file.exists():
                    continue

                try:
                    objects = self._load_jsonl_file(data_file)
                    chunks = []
                    for idx, obj in enumerate(objects):
                        text = obj.get("text", "")
                        if not text:
                            continue

                        # Construct chunk format required by QdrantManager.upsert_chunks
                        chunk = {
                            "text": text,
                            "chunk_index": idx,
                            "metadata": {
                                "source": doc_dir.name,
                                "doc_type": "act",
                                "act": doc_dir.name,
                                **obj.get("metadata", {})
                            }
                        }
                        chunks.append(chunk)

                    if chunks:
                        embedded = embedder.embed_chunks(chunks)
                        upserted = qdrant.upsert_chunks(
                            embedded,
                            collection_name=settings.QDRANT_COLLECTION_DOCS
                        )
                        stats["points_upserted"] += upserted
                        stats["files_processed"] += 1
                except Exception as exc:
                    self.logger.error(f"Failed to import {data_file}: {exc}")
                    stats["errors"] += 1

        # 2. Import QA Pairs (to COLLECTION_SECTIONS)
        qa_path = self.json_output_root / "legal_corpus" / "BNS_BNSS_BSA"
        if qa_path.exists():
            for category_dir in qa_path.iterdir():
                if not category_dir.is_dir():
                    continue

                data_file = category_dir / "data.json"
                if not data_file.exists():
                    continue

                try:
                    objects = self._load_jsonl_file(data_file)
                    chunks = []
                    for idx, obj in enumerate(objects):
                        text = obj.get("text", "")
                        if not text:
                            continue

                        chunk = {
                            "text": text,
                            "chunk_index": idx,
                            "metadata": {
                                "source": f"qa_{category_dir.name}",
                                "doc_type": "qa_pair",
                                **obj.get("metadata", {})
                            }
                        }
                        chunks.append(chunk)

                    if chunks:
                        embedded = embedder.embed_chunks(chunks)
                        upserted = qdrant.upsert_chunks(
                            embedded,
                            collection_name=settings.QDRANT_COLLECTION_SECTIONS
                        )
                        stats["points_upserted"] += upserted
                        stats["files_processed"] += 1
                except Exception as exc:
                    self.logger.error(f"Failed to import QA {data_file}: {exc}")
                    stats["errors"] += 1

        self.logger.info(f"JSON output to Qdrant import completed: {stats}")
        return stats

if __name__ == "__main__":
    import asyncio
    importer = JSONToQdrantImporter()
    asyncio.run(importer.import_all())
