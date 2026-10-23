"""Regression tests for region-aware metadata validation."""

from __future__ import annotations

from app.document_pipeline.validation import validate_metadata_evidence


def test_critical_metadata_must_be_found_in_expected_regions() -> None:
    text = (
        "IN THE HIGH COURT OF DELHI\n"
        "Apex Infrastructure v. National Highways Authority\n"
        "Civil Appeal No. 42 of 2023\n"
        "JUDGMENT\n"
        "The matter was heard on 1 January 2023.\n"
        "DATED: 18 January 2023\n"
    )
    metadata = {
        "case_title": {"value": "Apex Infrastructure vs National Highways Authority"},
        "petitioner": {"value": "Apex Infrastructure"},
        "respondent": {"value": "National Highways Authority"},
        "court": {"value": "High Court of Delhi"},
        "case_number": {"value": "Civil Appeal No. 42 of 2023"},
        "decision_date": {"value": "18 January 2023"},
    }

    result = validate_metadata_evidence(text, metadata)

    assert result["passed"] is True


def test_validation_rejects_body_only_decision_date() -> None:
    text = (
        "IN THE HIGH COURT OF DELHI\n"
        "Apex Infrastructure v. National Highways Authority\n"
        "JUDGMENT\n"
        "Heard on 18 January 2023.\n"
        "Order pronounced today.\n"
    )
    metadata = {"decision_date": {"value": "18 January 2023"}}

    result = validate_metadata_evidence(text, metadata)

    assert result["passed"] is False
    assert "decision_date" in result["failures"]


def test_court_matter_prefers_appeal_over_fir() -> None:
    from app.document_pipeline.metadata_extractor import LegalMetadataExtractor

    caption = "Criminal Appeal No. 2847 of 2024\n(arising out of FIR No. 143 of 2024)"
    result = LegalMetadataExtractor()._extract_court_matter(caption)

    assert result["value"] == "Criminal Appeal No. 2847 of 2024"
    assert result["status"] == "extracted"


def test_court_matter_reads_fir_when_it_is_the_only_docket() -> None:
    from app.document_pipeline.metadata_extractor import LegalMetadataExtractor

    result = LegalMetadataExtractor()._extract_court_matter("FIR No. 143 of 2024")

    assert result["value"] == "FIR No. 143 of 2024"
