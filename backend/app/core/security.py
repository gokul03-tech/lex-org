"""Authentication and security utilities.

Provides JWT token creation/verification and password hashing using passlib + python-jose.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context (bcrypt)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _pwd_context.hash(password)


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject (typically user ID).
        extra_claims: Additional claims to include in the token payload.
        expires_delta: Custom expiration; defaults to settings value.

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token.

    Args:
        subject: The token subject (typically user ID).
        expires_delta: Custom expiration; defaults to 7 days.

    Returns:
        Encoded JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: The JWT string to decode.

    Returns:
        The token payload as a dictionary.

    Raises:
        JWTError: If the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise JWTError(f"Token validation failed: {exc}") from exc
