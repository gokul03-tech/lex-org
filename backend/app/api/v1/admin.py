"""Admin endpoints: system status, dataset ingestion, KG seeding, user management.

Every route requires an authenticated user with administrator privileges.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import require_admin
from app.db.session import get_db

router = APIRouter()

AdminOnly = Annotated[object, Depends(require_admin)]


@router.get("/status")
async def system_status(_admin: AdminOnly) -> dict[str, str]:
    """Get system health status including all connected services."""
    return {"message": "System status endpoint - Phase 13 implementation"}


@router.post("/datasets/ingest")
async def ingest_datasets(_admin: AdminOnly) -> dict[str, str]:
    """Trigger dataset ingestion pipeline."""
    return {"message": "Dataset ingestion endpoint - Phase 5 implementation"}


@router.post("/kg/seed")
async def seed_knowledge_graph(_admin: AdminOnly) -> dict[str, str]:
    """Trigger knowledge graph seeding from GovIntel data."""
    return {"message": "KG seeding endpoint - Phase 6 implementation"}


@router.get("/users")
async def list_users(
    _admin: AdminOnly,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List all registered users (admin only)."""
    from app.db.models import User

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {
        "total": len(users),
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
            }
            for u in users
        ],
    }
