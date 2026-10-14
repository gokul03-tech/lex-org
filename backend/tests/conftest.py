"""Shared pytest fixtures: in-memory DB, ASGI client, and user/token factories."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401 - register ORM models on Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app


@pytest_asyncio.fixture
async def db_engine():
    """A single-connection in-memory SQLite engine with all tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    """An async_sessionmaker bound to the in-memory test engine."""
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """An httpx AsyncClient bound to the app with get_db overridden."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_factory(db_engine) -> Callable[..., Any]:
    """Factory producing (auth_headers, user_id) for a persisted user.

    Roles cannot be escalated through the public API, so tests that need an
    admin (or a specific role) create the row directly.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    counter = {"n": 0}

    async def _make(
        role: str = "advocate", is_superuser: bool = False
    ) -> tuple[dict[str, str], str]:
        from app.core.security import create_access_token, hash_password
        from app.db.models import User

        counter["n"] += 1
        uid = str(uuid.uuid4())
        async with factory() as session:
            user = User(
                id=uid,
                email=f"user{counter['n']}@example.com",
                hashed_password=hash_password("password123"),
                full_name=f"User {counter['n']}",
                role=role,
                is_active=True,
                is_superuser=is_superuser,
            )
            session.add(user)
            await session.commit()
        token = create_access_token(subject=uid, extra_claims={"role": role})
        return {"Authorization": f"Bearer {token}"}, uid

    return _make
