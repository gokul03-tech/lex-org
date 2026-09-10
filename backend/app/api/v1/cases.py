import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.background import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.api.deps import require_user
from app.db.session import get_db, async_session_factory
from app.db.models import Case, Document
from app.schemas import CaseResponse, CaseUpdate
from app.document_pipeline.parser import DocumentParser

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    title: str | None = Form(None),
    case_type: str = Form("Criminal Defense"),
    description: str | None = Form(None),
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    """Create a new legal case folder, optionally uploading an initial PDF/DOCX/TXT document.
    
    Document parsing happens asynchronously via background task to avoid blocking the HTTP response.
    """
    case_title = title
    if not case_title or not case_title.strip():
        if file and file.filename:
            file_path_obj = Path(file.filename)
            case_title = file_path_obj.stem.replace("_", " ").replace("-", " ").title()
        else:
            case_title = "Untitled Case"

    db_case = Case(
        user_id=current_user_id,
        title=case_title,
        description=description,
        case_type=case_type,
        status="draft" if not file else "documents_uploaded",
    )
    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)

    if file:
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = Path(file.filename or "unnamed").name
        stored_path = upload_dir / f"{uuid.uuid4().hex}_{safe_filename}"
        
        try:
            with open(stored_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as exc:
            logger.error(f"Failed to write file on case creation: {exc}")
            await db.delete(db_case)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save document file",
            )

        # Queue document processing as background task (non-blocking)
        background_tasks.add_task(
            _process_document_async,
            db_case.id,
            str(stored_path),
            file.filename,
            file.content_type,
        )

    return db_case


async def _process_document_async(
    case_id: str,
    file_path: str,
    original_filename: str,
    mime_type: str,
):
    """Background task: parse document, save metadata, index chunks."""
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
            document_type="judgment",
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


@router.get("/", response_model=list[CaseResponse])
async def list_cases(
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> list[Case]:
    """List all cases for the current user."""
    result = await db.execute(
        select(Case)
        .where(Case.user_id == current_user_id)
        .order_by(Case.created_at.desc())
    )
    cases = list(result.scalars().all())
    if not cases:
        res_all = await db.execute(select(Case).order_by(Case.created_at.desc()))
        return list(res_all.scalars().all())
    return cases


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    """Get a specific case by ID."""
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == current_user_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        result_any = await db.execute(select(Case).where(Case.id == case_id))
        case = result_any.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    return case


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_in: CaseUpdate,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    """Update an existing case."""
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == current_user_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        result_any = await db.execute(select(Case).where(Case.id == case_id))
        case = result_any.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    
    update_data = case_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)
        
    await db.commit()
    await db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a case."""
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == current_user_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        result_any = await db.execute(select(Case).where(Case.id == case_id))
        case = result_any.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    
    from app.db.models import Document, Analysis, Report
    from sqlalchemy import delete

    # Collect filenames BEFORE row deletion so we can purge their vectors
    doc_rows = await db.execute(
        select(Document.filename).where(Document.case_id == case_id)
    )
    filenames = [f for f in doc_rows.scalars().all() if f]

    # Cascade delete child records manually to satisfy foreign key constraints
    await db.execute(delete(Document).where(Document.case_id == case_id))
    await db.execute(delete(Analysis).where(Analysis.case_id == case_id))
    await db.execute(delete(Report).where(Report.case_id == case_id))

    await db.delete(case)
    await db.commit()

    # Purge the case's indexed chunks from Qdrant so deleted cases don't
    # leave orphan vectors polluting future retrieval results.
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        from app.core.config import settings as _settings
        from app.embeddings.qdrant_client import get_qdrant_manager

        qdrant = get_qdrant_manager()
        if qdrant.is_available() and filenames:
            qdrant.client.delete(
                collection_name=_settings.QDRANT_COLLECTION_DOCS,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_type",
                            match=MatchAny(any=["uploaded_document"]),
                        ),
                        FieldCondition(key="source", match=MatchAny(any=filenames)),
                    ]
                ),
            )
            logger.info(f"Purged Qdrant vectors for deleted case {case_id} ({len(filenames)} documents)")
    except Exception as exc:
        logger.warning(f"Qdrant vector cleanup failed for case {case_id}: {exc}")

