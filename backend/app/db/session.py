"""Async SQLAlchemy database session management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Async engine for SQLite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session.

    Usage:
        @router.get("/items")
        async def get_items(db: Annotated[AsyncSession, Depends(get_db)]):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
