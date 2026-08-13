"""API v1 router aggregation.

All v1 endpoint routers are mounted here under a single prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, analysis, auth, cases, documents, indiankanoon, reports, health

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(indiankanoon.router, prefix="/indiankanoon", tags=["Indian Kanoon"])
api_router.include_router(health.router, prefix="/health", tags=["Health Checks"])
