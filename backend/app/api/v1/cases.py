from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import require_user
from app.db.session import get_db
from app.db.models import Case
from app.schemas import CaseCreate, CaseResponse, CaseUpdate

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_in: CaseCreate,
    current_user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    """Create a new legal case."""
    db_case = Case(
        user_id=current_user_id,
        title=case_in.title,
        description=case_in.description,
        case_type=case_in.case_type,
        court_name=case_in.court_name,
        case_number=case_in.case_number,
        filing_date=case_in.filing_date,
        status="draft",
    )
    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)
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

