"""Analysis endpoints: trigger multi-agent analysis, get results, stream progress."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/case/{case_id}")
async def analyze_case(case_id: str) -> dict[str, str]:
    """Trigger the full multi-agent analysis pipeline for a case."""
    return {"message": f"Trigger analysis for case {case_id} - Phase 8 implementation"}


@router.get("/case/{case_id}")
async def get_analysis(case_id: str) -> dict[str, str]:
    """Get the latest analysis results for a case."""
    return {"message": f"Get analysis for case {case_id} - Phase 8 implementation"}


@router.get("/case/{case_id}/stream")
async def stream_analysis(case_id: str) -> dict[str, str]:
    """Stream real-time analysis progress via SSE."""
    return {"message": f"Stream analysis for case {case_id} - Phase 8 implementation"}
