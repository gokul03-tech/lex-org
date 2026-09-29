"""LexOrch-KG — Deterministic Metadata Extractor (Layer 1).
Runs BEFORE the LLM so date/parties/citations/judges can never fail again.
"""
from __future__ import annotations

import re
from typing import Any


def fix_name(n: str) -> str:
    n = re.sub(r'\s+', ' ', n).strip()
    n = re.sub(r'([A-Za-z]+) ([a-z])\b', r'\1\2', n)   # OCR fix: "Ramj i" -> "Ramji"
    return n.strip(' ,;:')


def _f(value: Any, status: str) -> dict[str, Any]:
    return {"value": value, "status": status}


def extract_metadata(text: str) -> dict[str, Any]:
    """Deterministic metadata, delegating to the canonical extractor.

    This module previously carried a second, weaker implementation of the same
    job. The two diverged: the pipeline (via case_understanding_agent) used this
    one, which returned not_found for petitioner, court and case number on
    documents the other extractor handled correctly - which is why the report
    showed "only the date correct" even though extraction worked. One canonical
    implementation is now used everywhere; the legacy key names and shapes are
    preserved below so existing consumers keep working.
    """
    from app.document_pipeline.metadata_extractor import LegalMetadataExtractor

    canonical = LegalMetadataExtractor().extract(text or "")

    def val(key: str, *aliases: str) -> Any:
        for k in (key, *aliases):
            v = canonical.get(k)
            if isinstance(v, dict) and v.get("value"):
                return v["value"]
            if v and not isinstance(v, dict):
                return v
        return None

    m: dict[str, Any] = dict(canonical)

    # Legacy shape: these consumers expect the case category as a bare string.
    category = canonical.get("case_category")
    if isinstance(category, dict):
        category = category.get("value")
    m["case_category"] = category or "criminal"

    # Aliases kept for backward compatibility with existing report/API code.
    if not m.get("bench"):
        m["bench"] = val("judges")
    m["title"] = canonical.get("case_title")
    return m
