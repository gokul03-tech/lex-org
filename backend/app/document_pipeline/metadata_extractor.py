"""Metadata extractor for legal documents.

Extracts structured metadata including title, date, parties,
courts, and document type from legal document text.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class LegalMetadataExtractor:
    """Extract structured metadata from legal document text."""

    # Regex patterns for legal metadata extraction
    COURT_PATTERNS = [
        r"(?:Supreme\s+Court|High\s+Court|District\s+Court|Sessions\s+Court|Magistrate[\s']*s?\s+Court|Family\s+Court|NCLT|NCLAT|DRT|DRAT|NCDRC|SCDRC|DCDRC)",
        r"(?:Hon['\u2019]?ble)\s+(?:Supreme\s+)?Court",
    ]

    CASE_NUMBER_PATTERNS = [
        r"(?:Crl\.?|Cri\.?|W\.?P\.?|S\.?L\.?P\.?|R\.?P\.?|M\.?A\.?|Cont\.?|Arb\.?)\s*(?:Appeal|Petition|Case|Application)?\s*(?:No\.?|Number)?\s*[:\-]?\s*\d+[\/\-]\d{2,4}",
        r"(?:Case|Crime|FIR)\s*(?:No\.?|Number)?\s*[:\-]?\s*\d+[\/\-]\d{2,4}",
    ]

    DATE_PATTERNS = [
        r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})",
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})",
    ]

    ACT_PATTERNS = [
        r"(?:the\s+)?(?:N\.?D\.?P\.?S\.?\s+Act|Narcotic\s+Drugs\s+and\s+Psychotropic\s+Substances\s+Act(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:I\.?P\.?C\.?|Indian\s+Penal\s+Code(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:Cr\.?P\.?C\.?|Code\s+of\s+Criminal\s+Procedure(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:BNS|Bharatiya\s+Nyaya\s+Sanhita(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:BNSS|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:BSA|Bharatiya\s+Sakshya\s+Adhiniyam(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:Evidence\s+Act|Indian\s+Evidence\s+Act(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:Information\s+Technology\s+Act|IT\s+Act(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:Prevention\s+of\s+Corruption\s+Act|PC\s+Act(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?(?:Motor\s+Vehicles\s+Act|MV\s+Act(?:\s*,\s*\d{4})?)",
        r"(?:the\s+)?([A-Z][a-zA-Z\s]{2,45}\s+(?:Act|Code|Sanhita|Adhiniyam)(?:\s*,\s*\d{4})?)",
    ]

    PARTY_PATTERNS = [
        r"(?:Petitioner|Plaintiff|Appellant|Complainant)[:\s]+([\w\s,.]+?)(?:\s+(?:vs\.?|v\.|versus|and|&))",
        r"(?:vs\.?|v\.|versus)\s+([\w\s,.]+?)(?:\s+(?:Respondent|Defendant))?",
        r"(?:Respondent|Defendant|Accused)[:\s]+([\w\s,.]+)",
    ]

    def __init__(self) -> None:
        self._court_pattern = re.compile(
            "|".join(f"({p})" for p in self.COURT_PATTERNS),
            re.IGNORECASE,
        )
        self._case_pattern = re.compile(
            "|".join(f"({p})" for p in self.CASE_NUMBER_PATTERNS),
            re.IGNORECASE,
        )
        self._act_pattern = re.compile(
            "|".join(f"({p})" for p in self.ACT_PATTERNS),
            re.IGNORECASE,
        )

    def extract(self, text: str, filename: str = "") -> dict[str, Any]:
        """Extract all metadata from legal text.

        Args:
            text: The document text.
            filename: Original filename for fallback extraction.

        Returns:
            Dict of extracted metadata fields.
        """
        head = text[:6000]
        full_sample = text[:30000]

        def to_meta_status(val: Any) -> dict[str, Any]:
            if val is None or val == "" or val == "Unknown" or val == "Untitled Document" or val == "other":
                return {"value": None, "status": "not_found"}
            return {"value": val, "status": "extracted"}

        raw_parties = self._extract_parties(head)
        petitioner = raw_parties.get("petitioner")
        respondent = raw_parties.get("respondent")
        word_count = len(text.split()) if text else 0

        metadata: dict[str, Any] = {
            "filename": filename,
            "title": to_meta_status(self._extract_title(head, filename)),
            "court": to_meta_status(self._extract_court(head)),
            "case_number": to_meta_status(self._extract_case_number(head)),
            "date": to_meta_status(self._extract_date(head)),
            "acts_referenced": self._extract_acts(full_sample),
            "petitioner": to_meta_status(petitioner),
            "respondent": to_meta_status(respondent),
            "document_type": to_meta_status(self._detect_document_type(head, filename)),
            "parties": raw_parties,
            "word_count": word_count
        }

        return metadata

    def _extract_title(self, text: str, filename: str) -> str:
        """Extract document title from first few lines or filename."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # First non-empty, reasonable-length line is often the title
        for line in lines[:5]:
            if 10 < len(line) < 200:
                return line

        # Fallback: use filename without extension
        if filename:
            name = filename.rsplit(".", 1)[0]
            return name.replace("_", " ").replace("-", " ")
        return "Untitled Document"

    def _extract_court(self, text: str) -> str | None:
        """Extract court name."""
        match = self._court_pattern.search(text)
        return match.group(0) if match else None

    def _extract_case_number(self, text: str) -> str | None:
        """Extract case number / FIR number."""
        match = self._case_pattern.search(text)
        return match.group(0) if match else None

    def _extract_date(self, text: str) -> str | None:
        """Extract the first date found in the document."""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Try parsing
                        date_str = f"{groups[0]} {groups[1]} {groups[2]}"
                        return date_str
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_acts(self, text: str) -> list[str]:
        """Extract referenced legal acts."""
        matches = self._act_pattern.finditer(text)
        acts = []
        for m in matches:
            act_name = m.group(0).strip()
            if act_name not in acts:
                acts.append(act_name)
        return acts[:10]

    def _extract_parties(self, text: str) -> dict[str, str | None]:
        """Extract party names."""
        parties: dict[str, str | None] = {
            "petitioner": None,
            "respondent": None,
        }

        # Look for "X vs Y" pattern (most reliable)
        vs_match = re.search(r"([\w\s,.\u2019']+?)\s+(?:vs\.?|v\.|versus)\s+([\w\s,.\u2019']+)", text, re.IGNORECASE)
        if vs_match:
            parties["petitioner"] = vs_match.group(1).strip()[:100]
            parties["respondent"] = vs_match.group(2).strip()[:100]
            return parties

        # Try labeled patterns
        petitioner = re.search(r"(?:Petitioner|Plaintiff|Appellant|Complainant)[:\s]+([\w\s,.]+)", text, re.IGNORECASE)
        if petitioner:
            parties["petitioner"] = petitioner.group(1).strip()[:100]

        respondent = re.search(r"(?:Respondent|Defendant|Accused)[:\s]+([\w\s,.]+)", text, re.IGNORECASE)
        if respondent:
            parties["respondent"] = respondent.group(1).strip()[:100]

        return parties

    def _detect_document_type(self, text: str, filename: str = "") -> str:
        """Detect the type of legal document."""
        combined = (text + " " + filename).lower()

        indicators = {
            "petition": ["petition", "writ", "complaint", "plaint"],
            "judgment": ["judgment", "judgement", "order", "decree", "verdict"],
            "affidavit": ["affidavit", "sworn", "deposition"],
            "evidence": ["evidence", "exhibit", "document", "proof"],
            "notice": ["notice", "summon", "communication"],
            "contract": ["contract", "agreement", "deed", "lease", "settlement"],
            "chargesheet": ["charge sheet", "chargesheet", "final report"],
            "fir": ["first information report", "f.i.r", "fir"],
            "act": ["act, 1", "code, 1", "sanhita", "adhiniyam"],
        }

        scores = {k: sum(1 for kw in v if kw in combined) for k, v in indicators.items()}
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        return best if scores[best] > 0 else "other"
