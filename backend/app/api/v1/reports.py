"""Report endpoints: generate, get, download advisory reports."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import require_user
from app.db.models import Case
from app.db.session import get_db

router = APIRouter()


async def _require_owned_case(
    case_id: str, user_id: str, db: AsyncSession
) -> Case:
    """Return the case only when it belongs to the given user, else 404."""
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    return case


@router.post("/case/{case_id}")
async def generate_report(
    case_id: str,
    current_user_id: Annotated[str, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Generate a legal advisory report for a case."""
    await _require_owned_case(case_id, current_user_id, db)
    return {"message": f"Generate report for case {case_id} - Phase 11 implementation"}


@router.get("/case/{case_id}")
async def get_report(
    case_id: str,
    current_user_id: Annotated[str, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Get the latest report for a case."""
    await _require_owned_case(case_id, current_user_id, db)
    return {"message": f"Get report for case {case_id} - Phase 11 implementation"}


@router.get("/case/{case_id}/download")
async def download_report(
    case_id: str,
    current_user_id: Annotated[str, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = "pdf",
) -> dict[str, str]:
    """Download report in specified format (pdf, json, docx)."""
    await _require_owned_case(case_id, current_user_id, db)
    return {"message": f"Download report for case {case_id} as {format} - Phase 11 implementation"}
