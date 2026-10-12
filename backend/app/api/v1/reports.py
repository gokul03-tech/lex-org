"""Ownership-protected access and export for generated legal reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.models import Case, Report
from app.db.session import get_db
from app.services.report_service import ReportGenerator

router = APIRouter()


async def _latest_owned_report(case_id: str, user_id: str, db: AsyncSession) -> Report:
    result = await db.execute(
        select(Report)
        .join(Case, Report.case_id == Case.id)
        .where(Report.case_id == case_id, Case.user_id == user_id)
        .order_by(Report.created_at.desc())
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _report_payload(report: Report) -> dict[str, Any]:
    return {
        "id": report.id,
        "case_id": report.case_id,
        "title": report.title,
        "sections": report.sections,
        "trust_score": report.trust_score,
        "confidence_scores": report.confidence_scores,
        "explanation_graph": report.explanation_graph,
        "knowledge_graph": report.knowledge_graph,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.post("/case/{case_id}")
async def generate_report(
    case_id: str,
    user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the report produced by case analysis; analysis performs generation."""
    return _report_payload(await _latest_owned_report(case_id, user_id, db))


@router.get("/case/{case_id}")
async def get_report(
    case_id: str,
    user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return _report_payload(await _latest_owned_report(case_id, user_id, db))


@router.get("/case/{case_id}/download")
async def download_report(
    case_id: str,
    format: str = Query("pdf", pattern="^(pdf|json)$"),
    user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _latest_owned_report(case_id, user_id, db)
    payload = _report_payload(report)
    safe_case_id = "".join(ch for ch in case_id if ch.isalnum() or ch in "-_" )
    if format == "json":
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report_{safe_case_id}.json"'},
        )

    generator = ReportGenerator()
    export_data = {
        "meta": {"case_id": report.case_id, "case_title": report.title,
                 "generated_at": payload["created_at"]},
        "sections": report.sections or [],
    }
    output = Path(generator.output_dir) / f"report_{safe_case_id}_{report.id}.pdf"
    generated_path = Path(generator.generate_pdf(export_data, str(output)))
    media_type = "application/pdf" if generated_path.suffix == ".pdf" else "application/json" if generated_path.suffix == ".json" else "text/html"
    return FileResponse(generated_path, media_type=media_type, filename=generated_path.name)
