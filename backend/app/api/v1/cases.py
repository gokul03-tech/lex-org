import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.api.deps import require_user
from app.db.session import get_db
from app.db.models import Case, Document
from app.schemas import CaseResponse, CaseUpdate
from app.document_pipeline.parser import DocumentParser

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    file: UploadFile | None = File(None),
    title: str | None = Form(None),
    case_type: str = Form("Criminal Defense"),
    description: str | None = Form(None),
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    """Create a new legal case folder, optionally uploading an initial PDF/DOCX/TXT document."""
    # Determine case title from filename if not specified
    case_title = title
    if not case_title or not case_title.strip():
        if file and file.filename:
            file_path_obj = Path(file.filename)
            case_title = file_path_obj.stem.replace("_", " ").replace("-", " ").title()
        else:
            case_title = "Untitled Case"

    # Initialize Case ORM object
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
        # Save the file to disk
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = upload_dir / f"{db_case.id}_{file.filename}"
        
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

        # Parse file contents
        parsed_data = {"text": "", "page_count": 1, "metadata": {}}
        try:
            parser = DocumentParser()
            parsed_data = parser.parse(stored_path, mime_type=file.content_type)
        except Exception as exc:
            logger.warning(f"Parser failed for {file.filename}: {exc}")
            parsed_data["text"] = f"[Error parsing text content: {exc}]"

        # Save document entry
        db_doc = Document(
            case_id=db_case.id,
            filename=file.filename,
            file_path=str(stored_path),
            document_type="judgment",
            description=description,
            status="uploaded",
            parsed_text=parsed_data.get("text", ""),
            raw_text=parsed_data.get("text", ""),
            page_count=parsed_data.get("page_count", 1),
            metadata_=parsed_data.get("metadata", {}),
            mime_type=file.content_type,
        )
        db.add(db_doc)
        await db.commit()
    return db_case


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
    return list(result.scalars().all())


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    await db.delete(case)
    await db.commit()

