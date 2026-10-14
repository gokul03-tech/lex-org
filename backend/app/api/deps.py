"""API dependency injection for FastAPI.

Provides shared dependencies like database sessions, current user extraction,
and service singletons.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import decode_token
from app.db.session import get_db

# OAuth2 scheme for extracting Bearer tokens from Authorization header.
# `auto_error=False` lets us fall back to a `?token=` query parameter, which
# is required for SSE/EventSource clients that cannot set custom headers.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    token_query: Annotated[str | None, Query(alias="token")] = None,
) -> str | None:
    """Extract the current user ID from a JWT Bearer token or ?token= query parameter.

    Returns None when no token is provided; raises 401 for a malformed or
    expired token. There is intentionally no development fallback user — every
    caller must present a valid token.
    """
    raw_token = token or token_query
    if raw_token is None:
        return None

    try:
        payload = decode_token(raw_token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


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


async def get_current_user(
    user_id: Annotated[str, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resolve the authenticated user ID to a persisted, active User record."""
    from app.db.models import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: Annotated[object, Depends(get_current_user)],
):
    """Require an authenticated administrator (role == 'admin' or is_superuser)."""
    role = getattr(user, "role", None)
    is_superuser = bool(getattr(user, "is_superuser", False))
    if not is_superuser and role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[str, Depends(require_user)]
CurrentUserObj = Annotated[object, Depends(get_current_user)]
AdminUser = Annotated[object, Depends(require_admin)]
OptionalUser = Annotated[str | None, Depends(get_current_user_id)]
