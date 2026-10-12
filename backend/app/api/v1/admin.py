"""Admin endpoints: system status, dataset ingestion, KG seeding, user management."""

from __future__ import annotations

import asyncio
from loguru import logger

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import settings
from app.db.models import User
from app.db.session import get_db

router = APIRouter()


async def _ingest_all_datasets() -> None:
    """Run the existing corpus loaders after returning the admin response."""
    try:
        from scripts.ingest_datasets import ingest_acts_pdfs, ingest_qa_dataset
        acts_stats = await asyncio.to_thread(ingest_acts_pdfs)
        qa_stats = await asyncio.to_thread(ingest_qa_dataset)
        from app.kg.falkordb_client import get_falkordb_client
        graph = await get_falkordb_client()
        graph_stats = await graph.seed_from_govintel()
        logger.info("Admin dataset ingestion completed: acts={}, qa={}, graph={}", acts_stats, qa_stats, graph_stats)
    except Exception as exc:
        logger.exception("Admin dataset ingestion failed: {}", exc)


async def _seed_graph() -> None:
    try:
        from app.kg.falkordb_client import get_falkordb_client
        client = await get_falkordb_client()
        result = await client.seed_from_govintel()
        logger.info("Admin graph seed completed: {}", result)
    except Exception as exc:
        logger.exception("Admin graph seed failed: {}", exc)


@router.get("/status")
async def system_status(
    _: str = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Report live connectivity for configured persistence and queue services."""
    try:
        await db.execute(text("SELECT 1"))
        database = "online"
    except Exception:
        database = "offline"

    try:
        from app.embeddings.qdrant_client import get_qdrant_manager
        qdrant = await asyncio.to_thread(get_qdrant_manager().is_available)
        qdrant_status = "online" if qdrant else "offline"
    except Exception:
        qdrant_status = "offline"

    try:
        from app.kg.falkordb_client import get_falkordb_client
        graph_client = await get_falkordb_client()
        falkordb_status = "online" if await graph_client.verify_connectivity() else "offline"
    except Exception:
        falkordb_status = "offline"

    def _redis_ping() -> bool:
        from redis import Redis
        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        try:
            return bool(client.ping())
        finally:
            client.close()

    try:
        redis_status = "online" if await asyncio.to_thread(_redis_ping) else "offline"
    except Exception:
        redis_status = "offline"

    components = {"database": database, "qdrant": qdrant_status,
                  "falkordb": falkordb_status, "redis": redis_status}
    return {"status": "healthy" if all(v == "online" for v in components.values()) else "degraded",
            "components": components}


@router.post("/datasets/ingest")
async def ingest_datasets(
    background_tasks: BackgroundTasks, _: str = Depends(require_admin),
) -> dict[str, str]:
    """Trigger dataset ingestion pipeline."""
    background_tasks.add_task(_ingest_all_datasets)
    return {"status": "scheduled"}


@router.post("/kg/seed")
async def seed_knowledge_graph(
    background_tasks: BackgroundTasks, _: str = Depends(require_admin),
) -> dict[str, str]:
    """Trigger knowledge graph seeding from GovIntel data."""
    background_tasks.add_task(_seed_graph)
    return {"status": "scheduled"}


@router.get("/users")
async def list_users(
    _: str = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    """List all registered users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [
        {"id": user.id, "email": user.email, "full_name": user.full_name,
         "role": user.role, "is_active": user.is_active, "created_at": user.created_at.isoformat()}
        for user in result.scalars().all()
    ]
