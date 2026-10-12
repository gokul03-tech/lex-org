"""API dependency injection for FastAPI.

Provides shared dependencies like database sessions, current user extraction,
and service singletons.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# OAuth2 scheme for extracting Bearer tokens from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    token_query: Annotated[str | None, Query(alias="token")] = None,
) -> str | None:
    """Extract the current user ID from a JWT Bearer token or ?token= query parameter.

    Returns None when no token is provided.
    Missing or invalid tokens are rejected in every environment.
    """
    raw_token = token or token_query
    if raw_token is None:
        return None

    try:
        payload = decode_token(raw_token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required")
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim",
            )
        return user_id
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc


async def require_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> str:
    """Require an authenticated user. Raises 401 if no valid token is present."""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def require_admin(
    user_id: Annotated[str, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Require an active admin account; a token role claim alone is insufficient."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or (user.role != "admin" and not user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user_id


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[str, Depends(require_user)]
OptionalUser = Annotated[str | None, Depends(get_current_user_id)]
