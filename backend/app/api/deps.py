"""API dependency injection for FastAPI.

Provides shared dependencies like database sessions, current user extraction,
and service singletons.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.security import decode_token

# OAuth2 scheme for extracting Bearer tokens from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> str | None:
    """Extract the current user ID from a JWT Bearer token.

    Returns None when no token is provided (for public endpoints).
    Raises 401 when an invalid/expired token is provided.
    """
    if token is None:
        return None

    try:
        payload = decode_token(token)
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


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[str, Depends(require_user)]
OptionalUser = Annotated[str | None, Depends(get_current_user_id)]
