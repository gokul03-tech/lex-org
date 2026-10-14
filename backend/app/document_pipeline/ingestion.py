"""End-to-end document ingestion lifecycle.

Centralises parse -> clean -> metadata -> chunk -> embed -> index so every
upload entry point (case creation, standalone upload, Indian Kanoon import)
produces the same status transitions and consistently shaped Qdrant payloads
with case/page citation provenance.
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.core.config import settings
from app.db.session import async_session_factory

# Document processing statuses (mirror app.schemas.DocumentStatus).
STATUS_UPLOADED = "uploaded"
STATUS_PARSING = "parsing"
STATUS_CHUNKING = "chunking"
STATUS_EMBEDDING = "embedding"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"


async def ingest_document(
    document_id: str,
    *,
    document_type: str | None = None,
) -> dict[str, Any]:
    """Run the full ingest lifecycle for a persisted Document row.

    Transitions status uploaded -> parsing -> chunking -> embedding -> complete
    (or failed) and indexes chunks into Qdrant carrying case_id, document_id,
    filename, page_number and chunk_id provenance.

    Args:
        document_id: Primary key of an existing Document row.
        document_type: Optional override for the chunk payload doc_type.

    Returns:
        A summary dict with the terminal status and chunk/index counts.
    """
    from app.db.models import Document

    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            logger.warning(f"ingest_document: document {document_id} not found")
            return {"status": "not_found", "document_id": document_id}

        file_path = doc.file_path
        filename = doc.filename
        mime_type = doc.mime_type
        doc_type = document_type or doc.document_type or "other"
        case_id = doc.case_id

        async def set_status(status: str, error: str | None = None) -> None:
            doc.status = status
            doc.processing_error = error
            await session.commit()

        try:
            await set_status(STATUS_PARSING)

            from app.agents.metadata_extractor import extract_metadata
            from app.document_pipeline.cleaner import TextCleaner
            from app.document_pipeline.parser import DocumentParser

            def _parse_and_clean() -> tuple[str, str, list[str], int, dict[str, Any]]:
                parsed = DocumentParser().parse(file_path, mime_type=mime_type)
                raw = parsed.get("text", "") or ""
                pages = parsed.get("pages") or [raw]
                cleaner = TextCleaner()
                cleaned_pages = cleaner.clean_pages(pages)
                cleaned = "\n\n".join(cleaned_pages).strip() or cleaner.clean(raw)
                if not cleaned.strip():
                    # Never overwrite usable content with an empty result.
                    cleaned, cleaned_pages = raw, pages
                return (
                    raw,
                    cleaned,
                    cleaned_pages,
                    parsed.get("page_count", len(pages)),
                    parsed.get("metadata") or {},
                )

            (
                raw_text,
                cleaned_text,
                cleaned_pages,
                page_count,
                parser_meta,
            ) = await asyncio.to_thread(_parse_and_clean)

            legal_meta = extract_metadata(cleaned_text)
            doc.raw_text = raw_text
            doc.parsed_text = cleaned_text
            doc.page_count = page_count
            doc.metadata_ = {
                **(parser_meta or {}),
                **(legal_meta or {}),
                "pages": cleaned_pages,
            }
            await session.commit()

            await set_status(STATUS_CHUNKING)

            from app.document_pipeline.chunker import LegalChunker

            base_meta: dict[str, Any] = {
                "source": filename,
                "filename": filename,
                "doc_type": doc_type,
                "act": "",
                "case_id": case_id,
                "document_id": document_id,
            }
            chunks = await asyncio.to_thread(LegalChunker().chunk_pages, cleaned_pages, base_meta)

            await set_status(STATUS_EMBEDDING)

            from app.document_pipeline.embedder import EmbeddingGenerator
            from app.embeddings.qdrant_client import get_qdrant_manager

            def _embed_and_index(chunk_list: list[dict[str, Any]]) -> int:
                if not chunk_list:
                    return 0
                embedded = EmbeddingGenerator().embed_chunks(chunk_list)
                return get_qdrant_manager().upsert_chunks(
                    embedded,
                    collection_name=settings.QDRANT_COLLECTION_DOCS,
                )

            indexed = await asyncio.to_thread(_embed_and_index, chunks)

            doc.chunk_count = len(chunks)
            await set_status(STATUS_COMPLETE)
            logger.info(
                f"Ingested document {document_id} ({filename}): "
                f"{len(chunks)} chunks, {indexed} vectors indexed"
            )
            return {
                "status": STATUS_COMPLETE,
                "document_id": document_id,
                "chunk_count": len(chunks),
                "indexed": indexed,
            }
        except Exception as exc:
            logger.error(f"Document ingestion failed for {document_id}: {exc}")
            await set_status(STATUS_FAILED, str(exc))
            return {"status": STATUS_FAILED, "document_id": document_id, "error": str(exc)}
