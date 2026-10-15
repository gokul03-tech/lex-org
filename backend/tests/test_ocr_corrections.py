"""Regression tests for conservative OCR normalization."""

from __future__ import annotations

from app.document_pipeline.ocr_corrections import correct_ocr_errors


def test_corrects_known_ocr_errors_with_audit_trail() -> None:
    corrected, changes = correct_ocr_errors(
        "Honbte High Court. Crl.M.P.No.I760 I20I3. Delhia."
    )

    assert corrected == "Hon'ble High Court. Crl.M.P.No.1760 of 2013. Delhi."
    assert {change["rule"] for change in changes} == {
        "legal_title",
        "case_number",
        "place_name",
    }


def test_does_not_apply_unsafe_short_fragment_replacements() -> None:
    original = "Appeal by the Applicant was allowed."

    corrected, changes = correct_ocr_errors(original)

    assert corrected == original
    assert changes == []
