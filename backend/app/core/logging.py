"""Structured logging configuration using Loguru."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Configure Loguru with structured output based on application settings."""
    logger.remove()

    if settings.LOG_FORMAT == "json":
        # JSON structured logging for production
        logger.add(
            sys.stdout,
            serialize=True,
            level=settings.LOG_LEVEL,
            enqueue=True,
            format="{time} {level} {name} {function} {line} {message} {extra}",
        )
    else:
        # Human-readable console logging for development
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    # File logging (always structured)
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_file,
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        serialize=True,
        level="DEBUG",
        enqueue=True,
    )

    logger.info(f"Logging configured | level={settings.LOG_LEVEL} format={settings.LOG_FORMAT}")


# Ensure logging is configured on import
setup_logging()
