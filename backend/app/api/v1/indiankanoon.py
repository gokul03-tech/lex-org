"""Indian Kanoon API endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.models import Case, Document
from app.db.session import get_db
from app.services.indiankanoon import IndianKanoonService

router = APIRouter()


@router.get("/search")
async def search_judgments(
    query: str = Query(..., description="Search query string"),
    page: int = Query(0, ge=0, description="Page index (starts at 0)"),
    current_user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Search for judgments in the Indian Kanoon database."""
    service = IndianKanoonService()
    try:
        results = await service.search_judgments(query, page)
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(exc)}")


@router.get("/doc/{doc_id}")
async def get_judgment(
    doc_id: str,
    current_user_id: str = Depends(require_user),
) -> dict[str, Any]:
    """Fetch details/text of a specific judgment by document ID."""
    service = IndianKanoonService()
    try:
        doc = await service.get_judgment(doc_id)
        return doc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(exc)}")


@router.post("/import/{case_id}/{doc_id}")
async def import_judgment(
    case_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fetch a judgment from Indian Kanoon and import it as a Document for a case."""
    # Verify the case exists and belongs to the authenticated user.
    stmt = select(Case).where(Case.id == case_id, Case.user_id == current_user_id)
    result = await db.execute(stmt)
    case_obj = result.scalar_one_or_none()
    if not case_obj:
        raise HTTPException(status_code=404, detail=f"Case with ID {case_id} not found")

    service = IndianKanoonService()
    try:
        judgment_data = await service.get_judgment(doc_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch judgment from Indian Kanoon: {exc}",
        )

    # Extract metadata/text
    title = judgment_data.get("title", f"Indian Kanoon Judgment {doc_id}")
    raw_text = judgment_data.get("doc", "")
    author = judgment_data.get("author", "")
    bench = judgment_data.get("bench", "")
    publishdate = judgment_data.get("publishdate", "")
    docsource = judgment_data.get("docsource", "")

    # Persist the fetched text to disk so the shared ingestion lifecycle
    # (parse -> chunk -> embed -> index) can process it uniformly.
    document_id = str(uuid.uuid4())
    relative_path = Path("data/documents") / f"judgment_{doc_id}.txt"
    file_path = Path("data/documents")
    file_path.mkdir(parents=True, exist_ok=True)
    with open(relative_path, "w", encoding="utf-8") as handle:
        handle.write(raw_text or "")

    char_count = len(raw_text or "")
    word_count = len((raw_text or "").split())

    doc_obj = Document(
        id=document_id,
        case_id=case_id,
        filename=f"judgment_{doc_id}.txt",
        file_path=str(relative_path),
        document_type="judgment",
        description=f"Imported from Indian Kanoon (TID: {doc_id})",
        status="uploaded",
        raw_text=raw_text,
        chunk_count=0,
        mime_type="text/plain",
        metadata_={
            "tid": doc_id,
            "title": title,
            "author": author,
            "bench": bench,
            "publishdate": publishdate,
            "docsource": docsource,
            "char_count": char_count,
            "word_count": word_count,
            "source": "indian_kanoon",
        },
    )

    db.add(doc_obj)
    case_obj.status = "documents_uploaded"
    await db.commit()

    from app.document_pipeline.ingestion import ingest_document

    background_tasks.add_task(ingest_document, document_id)

    return {
        "message": f"Successfully imported judgment '{title}' into case {case_id}",
        "document_id": document_id,
        "title": title,
        "char_count": char_count,
    }
