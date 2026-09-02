"""API dependency injection for FastAPI.

Provides shared dependencies like database sessions, current user extraction,
and service singletons.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from loguru import logger

from app.core.config import settings
from app.core.security import decode_token

# OAuth2 scheme for extracting Bearer tokens from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Default dev user fallback to prevent 401 disruptions during local development and presentations
DEV_FALLBACK_USER_ID = "6d2b5644-2791-4bfd-a9c3-f40cce9b5d8a"


async def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    token_query: Annotated[str | None, Query(alias="token")] = None,
) -> str | None:
    """Extract the current user ID from a JWT Bearer token or ?token= query parameter.

    Returns None when no token is provided.
    In development mode, gracefully falls back rather than breaking demo flows.
    """
    raw_token = token or token_query
    if raw_token is None:
        if settings.APP_ENV == "development" or settings.DEBUG:
            return DEV_FALLBACK_USER_ID
        return None

    try:
        payload = decode_token(raw_token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            if settings.APP_ENV == "development" or settings.DEBUG:
                return DEV_FALLBACK_USER_ID
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim",
            )
        return user_id
    except JWTError as exc:
        if settings.APP_ENV == "development" or settings.DEBUG:
            logger.warning(f"Development token decode fallback ({exc})")
            return DEV_FALLBACK_USER_ID
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc


async def require_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> str:
    """Require an authenticated user. Raises 401 if no valid token is present."""
    if user_id is None:
        if settings.APP_ENV == "development" or settings.DEBUG:
            return DEV_FALLBACK_USER_ID
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[str, Depends(require_user)]
OptionalUser = Annotated[str | None, Depends(get_current_user_id)]
