"""SQLAlchemy declarative base and common mixins."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """Mixin that adds a UUID primary key column."""

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
