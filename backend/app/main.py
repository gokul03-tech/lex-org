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

    # Propagate the HF token to the process environment before any Hub calls,
    # so model metadata checks are authenticated (silences rate-limit warnings).
    import os as _os
    if settings.HF_TOKEN:
        _os.environ.setdefault("HF_TOKEN", settings.HF_TOKEN)
        _os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", settings.HF_TOKEN)

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
                
                # Startup Validation: check collections & dimensions
                for col in [settings.QDRANT_COLLECTION_DOCS, settings.QDRANT_COLLECTION_SECTIONS]:
                    try:
                        info = qdrant.client.get_collection(collection_name=col)
                        logger.info(f"Qdrant collection '{col}' is healthy. Points count: {info.points_count} | Vector size: {info.config.params.vectors.size}")
                        if info.config.params.vectors.size != settings.QDRANT_VECTOR_SIZE:
                            logger.error(f"CRITICAL: Qdrant collection '{col}' vector size mismatch! Expected {settings.QDRANT_VECTOR_SIZE}, got {info.config.params.vectors.size}")
                    except Exception as col_err:
                        logger.error(f"Failed to validate collection '{col}': {col_err}")
            else:
                logger.error("CRITICAL: Qdrant vector database is unavailable! Retrieval services will run in DEGRADED mode.")
        except Exception as q_exc:
            logger.error(f"Startup Qdrant collections setup error: {q_exc}")

        # Check FalkorDB Connectivity
        try:
            from app.kg.falkordb_client import get_falkordb_client
            falkor = await get_falkordb_client()
            if await falkor.verify_connectivity():
                logger.info("FalkorDB connection verified successfully. Knowledge Graph features are active.")
            else:
                logger.error("CRITICAL: FalkorDB is unavailable on port 6379! Knowledge Graph features will run in DEGRADED mode.")
        except Exception as f_exc:
            logger.error(f"Startup FalkorDB connectivity check failed: {f_exc}")

        # Warm up ML models (BGE-M3 embedder + CrossEncoder reranker) in a background task
        # so server startup is instant (under 10ms) and does not block HTTP requests or reload events.
        async def _warmup_models_background():
            import asyncio
            def _sync_warmup():
                try:
                    import time as _time
                    t0 = _time.monotonic()
                    from app.embeddings.bge_m3 import get_bge_m3
                    if get_bge_m3().load():
                        logger.info(f"BGE-M3 embedder warmed up in {_time.monotonic() - t0:.1f}s")
                    else:
                        logger.warning("BGE-M3 failed to load; embeddings will use deterministic fallback.")
                except Exception as emb_exc:
                    logger.warning(f"BGE-M3 warmup skipped: {emb_exc}")

                try:
                    import time as _time
                    t0 = _time.monotonic()
                    from app.rag.reranker import warmup_reranker
                    if warmup_reranker():
                        logger.info(f"CrossEncoder reranker warmed up in {_time.monotonic() - t0:.1f}s")
                    else:
                        logger.warning("CrossEncoder unavailable; reranking falls back to score-based mode.")
                except Exception as rr_exc:
                    logger.warning(f"Reranker warmup skipped: {rr_exc}")

            await asyncio.to_thread(_sync_warmup)

        import asyncio
        asyncio.create_task(_warmup_models_background())
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
