"""Evidence checks for extracted legal metadata."""

from __future__ import annotations

import re
from typing import Any


def _value(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if isinstance(value, dict):
        value = value.get("value")
    return str(value or "").strip()


def _contains(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    normalized_haystack = re.sub(r"\W+", "", haystack).lower()
    normalized_needle = re.sub(r"\W+", "", needle).lower()
    normalized_haystack = re.sub(r"versus|vs", "v", normalized_haystack)
    normalized_needle = re.sub(r"versus|vs", "v", normalized_needle)
    return normalized_needle in normalized_haystack


def validate_metadata_evidence(
    text: str,
    metadata: dict[str, Any],
    *,
    header_chars: int = 2500,
    tail_chars: int = 2500,
) -> dict[str, Any]:
    """Validate critical fields against the region where they should occur."""
    header = text[:header_chars]
    tail = text[-tail_chars:]
    checks: list[dict[str, Any]] = []

    for field in ("case_title", "petitioner", "respondent", "court", "case_number"):
        value = _value(metadata, field)
        if not value:
            continue
        checks.append(
            {
                "field": field,
                "region": "header",
                "verified": _contains(header, value),
                "value": value,
            }
        )

    date = _value(metadata, "decision_date")
    if date:
        date_match = _contains(tail, date)
        dated_context = bool(
            re.search(
                r"(?:dated|date|pronounced|ordered)\W{0,30}"
                + re.escape(date).replace(r"\ ", r"\W+"),
                tail,
                re.IGNORECASE,
            )
        )
        checks.append(
            {
                "field": "decision_date",
                "region": "signature",
                "verified": date_match and dated_context,
                "value": date,
            }
        )

    failures = [check["field"] for check in checks if not check["verified"]]
    return {
        "passed": not failures,
        "failures": failures,
        "checks": checks,
    }
