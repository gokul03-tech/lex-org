from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.api.deps import require_user
from app.db.session import get_db
from app.db.models import Document, Case
from app.document_pipeline.parser import DocumentParser

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: Annotated[str, Form()],
    file: UploadFile = File(...),
    document_type: Annotated[str, Form()] = "other",
    description: Annotated[str | None, Form()] = None,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a legal document (PDF, DOCX, TXT) for processing and auto-parse it."""
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
    
    file_path = upload_dir / f"{case_id}_{file.filename}"
    
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

    # Parse document content
    parsed_data = {"text": "", "page_count": 1, "metadata": {}, "needs_ocr": False}
    try:
        parser = DocumentParser()
        parsed_data = parser.parse(file_path, mime_type=file.content_type)
    except Exception as exc:
        logger.warning(f"Parsing failed for {file.filename}, proceeding with default text representation. Error: {exc}")
        parsed_data["text"] = f"[Error parsing text content: {exc}]"

    # Run Layer 1 Deterministic Legal Metadata Extraction on parsed text
    from app.agents.metadata_extractor import extract_metadata
    legal_meta = extract_metadata(parsed_data.get("text", ""))

    # Create document db entry
    db_doc = Document(
        case_id=case_id,
        filename=file.filename,
        file_path=str(file_path),
        document_type=document_type,
        description=description,
        status="uploaded",
        parsed_text=parsed_data.get("text", ""),
        raw_text=parsed_data.get("text", ""),
        page_count=parsed_data.get("page_count", 1),
        metadata_={
            **(parsed_data.get("metadata") or {}),
            **legal_meta,
            "pages": parsed_data.get("pages", [])
        },
        mime_type=file.content_type,
    )
    
    db.add(db_doc)
    
    # Update case status
    case.status = "documents_uploaded"
    
    await db.commit()
    await db.refresh(db_doc)
    
    return {
        "id": db_doc.id,
        "filename": db_doc.filename,
        "status": db_doc.status,
        "page_count": db_doc.page_count,
        "case_id": db_doc.case_id,
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

