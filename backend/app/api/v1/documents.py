from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.background import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.api.deps import require_user
from app.db.session import get_db, async_session_factory
from app.db.models import Document, Case
from app.document_pipeline.parser import DocumentParser

router = APIRouter()


async def _process_upload_async(
    case_id: str,
    file_path: str,
    original_filename: str,
    mime_type: str,
    document_type: str,
    description: str | None,
):
    """Background task: parse uploaded document, extract metadata, save to DB."""
    import asyncio

    def _sync_parse():
        parser = DocumentParser()
        return parser.parse(file_path, mime_type=mime_type)

    try:
        parsed_data = await asyncio.to_thread(_sync_parse)
    except Exception as exc:
        logger.warning(f"Parser failed for {original_filename}: {exc}")
        parsed_data = {"text": f"[Error parsing text content: {exc}]", "page_count": 1, "metadata": {}}

    from app.agents.metadata_extractor import extract_metadata
    legal_meta = extract_metadata(parsed_data.get("text", ""))

    async with async_session_factory() as session:
        db_doc = Document(
            case_id=case_id,
            filename=original_filename,
            file_path=file_path,
            document_type=document_type,
            description=description,
            status="uploaded",
            parsed_text=parsed_data.get("text", ""),
            raw_text=parsed_data.get("text", ""),
            page_count=parsed_data.get("page_count", 1),
            metadata_={
                **(parsed_data.get("metadata") or {}),
                **legal_meta,
                "pages": parsed_data.get("pages", []),
            },
            mime_type=mime_type,
        )
        session.add(db_doc)
        await session.commit()
        logger.info(f"Background processed document {original_filename} for case {case_id}")


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    case_id: Annotated[str, Form()],
    file: UploadFile = File(...),
    document_type: Annotated[str, Form()] = "other",
    description: Annotated[str | None, Form()] = None,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a legal document (PDF, DOCX, TXT) for processing and auto-parse it.
    
    Document parsing happens asynchronously via background task to avoid blocking.
    """
    # Verify case exists and belongs to user
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == current_user_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case directory not found",
        )

    # Prepare file storage folder
    upload_dir = Path("./data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename: strip any directory components to prevent path traversal,
    # then store under a unique server-generated name to avoid collisions.
    safe_filename = Path(file.filename or "unnamed").name
    stored_name = f"{uuid.uuid4().hex}_{safe_filename}"
    file_path = upload_dir / stored_name
    
    # Save the file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.error(f"Failed to save file: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save file to server storage",
        )

    # Queue document processing as background task (non-blocking)
    background_tasks.add_task(
        _process_upload_async,
        case_id,
        str(file_path),
        file.filename,
        file.content_type,
        document_type,
        description,
    )

    # Update case status immediately
    case.status = "documents_uploaded"
    await db.commit()

    return {
        "id": str(uuid.uuid4()),
        "filename": file.filename,
        "status": "uploaded",
        "page_count": 0,
        "case_id": case_id,
    }


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Check processing status of an uploaded document."""
    result = await db.execute(
        select(Document).join(Case).where(
            Document.id == document_id,
            Case.user_id == current_user_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return {
        "id": doc.id,
        "status": doc.status,
        "filename": doc.filename,
    }


@router.get("/")
async def list_documents(
    case_id: str | None = None,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all documents for a case."""
    query = select(Document).join(Case).where(Case.user_id == current_user_id)
    if case_id:
        query = query.where(Document.case_id == case_id)
        
    result = await db.execute(query)
    docs = result.scalars().all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "status": doc.status,
            "created_at": doc.created_at,
        }
        for doc in docs
    ]


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream or download the original uploaded PDF document."""
    from fastapi.responses import FileResponse
    result = await db.execute(
        select(Document).join(Case).where(
            Document.id == document_id,
            Case.user_id == current_user_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc or not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk",
        )
    return FileResponse(
        doc.file_path,
        media_type=doc.mime_type or "application/pdf",
        filename=doc.filename,
    )


@router.get("/case/{case_id}/file")
async def get_case_primary_document_file(
    case_id: str,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the primary PDF document file for a case dossier."""
    from fastapi.responses import FileResponse
    result = await db.execute(
        select(Document).join(Case).where(
            Document.case_id == case_id,
            Case.user_id == current_user_id
        ).order_by(Document.created_at.desc())
    )
    doc = result.scalars().first()
    if not doc or not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document file found for this case",
        )
    return FileResponse(
        doc.file_path,
        media_type=doc.mime_type or "application/pdf",
        filename=doc.filename,
    )

