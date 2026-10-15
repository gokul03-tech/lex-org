"""Conservative, auditable corrections for recurring legal-document OCR errors."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class OCRCorrection:
    """One correction applied to extracted text."""

    pattern: str
    replacement: str
    rule: str


# Keep corrections specific enough that normal legal words are not rewritten.
# Short fragments such as ``Ap`` are deliberately excluded because they match
# ordinary words like ``Appeal`` and ``Applicant``.
OCR_CORRECTIONS: tuple[OCRCorrection, ...] = (
    OCRCorrection(r"\bIndran\b", "Indian", "common_word"),
    OCRCorrection(r"\bChrnrndramauli\b", "Chandramauli", "name"),
    OCRCorrection(r"\bBhrskar\b", "Bhaskar", "name"),
    OCRCorrection(r"\bHonbte\b", "Hon'ble", "legal_title"),
    OCRCorrection(r"\bHou,er\.er\b", "However", "common_word"),
    OCRCorrection(r"\bCrimina-l\b", "Criminal", "hyphenated_word"),
    OCRCorrection(r"\bI760\s+I20I3\b", "1760 of 2013", "case_number"),
    OCRCorrection(r"\bI306\s*/\s*2016\b", "1306 of 2016", "case_number"),
    OCRCorrection(r"\b7446\s+of\s+20I7\b", "7446 of 2017", "case_number"),
    OCRCorrection(r"\bDelhia\b", "Delhi", "place_name"),
)


def correct_ocr_errors(text: str) -> tuple[str, list[dict[str, str]]]:
    """Apply conservative OCR fixes and return an audit trail.

    The audit trail makes every automatic correction inspectable and prevents
    the extractor from silently changing source text without explanation.
    """
    corrected = text or ""
    changes: list[dict[str, str]] = []
    for correction in OCR_CORRECTIONS:
        corrected, count = re.subn(
            correction.pattern,
            correction.replacement,
            corrected,
            flags=re.IGNORECASE if correction.rule != "name" else 0,
        )
        if count:
            changes.append(
                {
                    "pattern": correction.pattern,
                    "replacement": correction.replacement,
                    "rule": correction.rule,
                    "count": str(count),
                }
            )
    return corrected, changes
