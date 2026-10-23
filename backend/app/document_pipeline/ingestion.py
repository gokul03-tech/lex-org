"""End-to-end document ingestion lifecycle.

Centralises parse -> clean -> metadata -> chunk -> embed -> index so every
upload entry point (case creation, standalone upload, Indian Kanoon import)
produces the same status transitions and consistently shaped Qdrant payloads
with case/page citation provenance.
"""

from __future__ import annotations

import asyncio
import hashlib
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

# Serialise ingestion of byte-identical files within the same case so a
# duplicate upload cannot race ahead of the one already embedding. The map
# only grows by distinct (case, content) pairs actually ingested.
_INGEST_LOCKS: dict[str, asyncio.Lock] = {}


def _lock_for(key: str) -> asyncio.Lock:
    lock = _INGEST_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _INGEST_LOCKS[key] = lock
    return lock


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


async def _find_content_duplicate(
    session: Any, case_id: str | None, document_id: str, file_hash: str
) -> Any:
    """Return a completed sibling document with the same content, if any."""
    from sqlalchemy import select

    from app.db.models import Document

    result = await session.execute(
        select(Document).where(
            Document.case_id == case_id,
            Document.id != document_id,
            Document.status == "complete",
        )
    )
    for other in result.scalars().all():
        meta = other.metadata_ if isinstance(other.metadata_, dict) else {}
        if meta.get("file_sha256") == file_hash:
            return other
    return None


async def _repair_ocr_pages(
    pages: list[str], max_chars: int | None
) -> list[str]:
    """Repair OCR-damaged page text with the LLM, preserving page boundaries.

    A badly scanned PDF otherwise embeds garbled text into Qdrant, so retrieval
    returns unusable chunks. The document is only passed to the LLM when it
    actually looks damaged, and only leading pages up to ``max_chars`` of source
    text are repaired, so clean or large digital documents incur no extra calls.
    Pages are repaired one at a time so per-page provenance survives, and any
    failure degrades to the original text.
    """
    if not pages:
        return pages
    try:
        from app.agents.agentic_pipeline import (
            _looks_like_ocr_noise,
            clean_ocr_text_with_llm,
        )

        if not _looks_like_ocr_noise("\n\n".join(pages)):
            return pages

        budget = max_chars if max_chars and max_chars > 0 else None
        repaired: list[str] = []
        spent = 0
        changed = False
        for page in pages:
            if not page.strip() or (budget is not None and spent >= budget):
                repaired.append(page)
                continue
            remaining = None if budget is None else max(budget - spent, 1)
            fixed = await clean_ocr_text_with_llm(page, force=True, max_chars=remaining)
            repaired.append(fixed)
            spent += len(page)
            changed = changed or fixed != page
        if changed:
            logger.info(
                f"ingest_document: OCR repair applied to scanned pages "
                f"(repaired head {spent} chars)"
            )
        return repaired
    except Exception as exc:  # noqa: BLE001 - repair must never break ingestion
        logger.warning(f"ingest_document: OCR repair skipped: {exc}")
        return pages


async def ingest_document(
    document_id: str,
    *,
    document_type: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run the full parse -> clean -> chunk -> embed -> index lifecycle.

    Args:
        document_id: Primary key of an existing Document row.
        document_type: Optional override for the chunk payload doc_type.
        force: Re-run even if another runner already claimed the document.

    Returns:
        A summary dict with the terminal status and chunk/index counts.
    """
    from app.db.models import Document

    async with async_session_factory() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            logger.warning(f"ingest_document: document {document_id} not found")
            return {"status": "not_found", "document_id": document_id}

        if not force:
            # Claim the document so exactly one runner ingests it. The upload
            # endpoint's background task and the analysis stream can both call
            # this; the conditional update means the first caller wins and the
            # other returns immediately instead of duplicating parse/embed work.
            from sqlalchemy import update

            claim = await session.execute(
                update(Document)
                .where(
                    Document.id == document_id,
                    Document.status.in_([STATUS_UPLOADED, STATUS_FAILED]),
                )
                .values(status=STATUS_PARSING)
                .execution_options(synchronize_session=False),
            )
            await session.commit()
            if claim.rowcount == 0:
                logger.info(
                    f"ingest_document: {document_id} already claimed "
                    f"(status={doc.status}); skipping duplicate run"
                )
                return {
                    "status": "already_claimed",
                    "document_id": document_id,
                    "current_status": doc.status,
                }
            doc.status = STATUS_PARSING

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
            file_hash = await asyncio.to_thread(_file_sha256, file_path)
        except OSError as exc:
            logger.warning(f"ingest_document: cannot hash {file_path}: {exc}")
            file_hash = ""

        lock_key = f"{case_id}:{file_hash}" if file_hash else f"doc:{document_id}"
        async with _lock_for(lock_key):
            if file_hash:
                duplicate = await _find_content_duplicate(
                    session, case_id, document_id, file_hash
                )
                if duplicate is not None:
                    doc.raw_text = duplicate.raw_text
                    doc.parsed_text = duplicate.parsed_text
                    doc.page_count = duplicate.page_count
                    doc.metadata_ = duplicate.metadata_
                    doc.chunk_count = duplicate.chunk_count
                    await set_status(STATUS_COMPLETE)
                    logger.info(
                        f"ingest_document: {filename} duplicates {duplicate.id} "
                        f"(identical content); skipped re-embedding"
                    )
                    return {
                        "status": STATUS_COMPLETE,
                        "document_id": document_id,
                        "chunk_count": duplicate.chunk_count,
                        "deduplicated": True,
                    }

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

                cleaned_pages = await _repair_ocr_pages(
                    cleaned_pages, settings.OCR_CLEAN_MAX_CHARS
                )
                cleaned_text = "\n\n".join(cleaned_pages).strip() or cleaned_text

                legal_meta = extract_metadata(cleaned_text)
                doc.raw_text = raw_text
                doc.parsed_text = cleaned_text
                doc.page_count = page_count
                doc.metadata_ = {
                    **(parser_meta or {}),
                    **(legal_meta or {}),
                    "pages": cleaned_pages,
                    "file_sha256": file_hash,
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
                chunks = await asyncio.to_thread(
                    LegalChunker().chunk_pages, cleaned_pages, base_meta
                )

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
