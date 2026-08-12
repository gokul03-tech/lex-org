"""FastAPI application entry point for LexOrch-KG.

Initializes CORS, exception handlers, lifespan events, and mounts all API routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1 import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} | env={settings.APP_ENV}")

    # Startup: initialize connections, warm up caches
    # These are deferred to actual service initialization to avoid import failures
    # when optional dependencies (neo4j, qdrant, etc.) are not installed.
    try:
        from app.db.base import Base
        from app.db.session import engine
        import app.db.models  # Import to register schemas
        
        # Ensure database folder exists
        import os
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
        
        # Ensure Qdrant collections exist
        try:
            from app.embeddings.qdrant_client import get_qdrant_manager
            qdrant = get_qdrant_manager()
            if qdrant.is_available():
                qdrant.create_collections()
                logger.info("Qdrant collections verified/created successfully.")
        except Exception as q_exc:
            logger.error(f"Startup Qdrant collections setup error: {q_exc}")
    except Exception as exc:
        logger.error(f"Startup DB error: {exc}")

    yield

    # Shutdown: close connections gracefully
    logger.info("Shutting down application")
    try:
        logger.info("Application shutdown complete")
    except Exception as exc:
        logger.error(f"Shutdown error: {exc}")


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version=settings.APP_VERSION,
        description=(
            "Trust-Aware Multi-Agent Legal Advisory Framework using "
            "Dynamic Evidence Knowledge Graphs, Adaptive Multi-Stage RAG, "
            "Explainable AI and LangGraph."
        ),
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global Exception Handler ────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all exception handler for unhandled errors."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": type(exc).__name__,
                "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            },
        )

    # ── Health Check ────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint for load balancers and monitoring."""
        return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    # ── Mount API Router ────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


# Application instance used by uvicorn
app = create_app()
