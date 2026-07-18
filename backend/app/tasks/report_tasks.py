"""Async Celery tasks for report generation."""

from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2)
def generate_report_async(self, case_id: str) -> dict:
    """Background task to generate a legal advisory report.

    Args:
        case_id: The database ID of the case.

    Returns:
        Status dictionary with report path.
    """
    # Phase 11 implementation
    return {"status": "pending", "case_id": case_id}
