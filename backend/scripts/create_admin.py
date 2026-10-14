#!/usr/bin/env python3
"""Create or promote an administrator account.

Public registration refuses to grant administrative privileges, so the first
admin must be provisioned out-of-band with this script.

Usage:
    python scripts/create_admin.py
    python scripts/create_admin.py --email admin@example.com --password 'S3cret!'
    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='S3cret!' python scripts/create_admin.py
"""

import argparse
import asyncio
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from sqlalchemy.future import select

from app.core.security import hash_password
from app.db.models import User
from app.db.session import async_session_factory


async def create_or_promote(email: str, password: str, full_name: str) -> tuple[str, bool]:
    """Create an admin user, or promote an existing account to admin.

    Returns:
        (user_id, created) where ``created`` is True for a new account.
    """
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role="admin",
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id, True

        user.role = "admin"
        user.is_superuser = True
        user.is_active = True
        user.hashed_password = hash_password(password)
        user.full_name = full_name
        await session.commit()
        await session.refresh(user)
        return user.id, False


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@lexorch.local"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    parser.add_argument("--full-name", default=os.environ.get("ADMIN_FULL_NAME", "Administrator"))
    args = parser.parse_args()

    generated = not args.password
    password = args.password or secrets.token_urlsafe(18)

    _, created = asyncio.run(create_or_promote(args.email, password, args.full_name))
    action = "Created" if created else "Updated/promoted"
    logger.info(f"{action} admin user: {args.email}")
    if generated:
        logger.info(f"Generated password (shown once, store securely): {password}")


if __name__ == "__main__":
    main()
