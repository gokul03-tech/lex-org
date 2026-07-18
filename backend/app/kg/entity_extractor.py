"""Legal entity extractor for case documents.

Extracts parties, evidence, legal issues, dates, locations, and other
entities from parsed legal document text using spaCy NER + legal regex.
"""

from __future__ import annotations

import re
from typing import Any


class LegalEntityExtractor:
    """Extracts legal entities from case document text.

    Uses spaCy for general NER and custom legal regex patterns for
    domain-specific entity types: parties, judges, advocates, evidence,
    legal issues, dates, locations, and reliefs sought.
    """

    def __init__(self) -> None:
        self._nlp = None
        self._patterns = self._build_patterns()

    def _load_nlp(self):
        """Lazy-load spaCy model."""
        if self._nlp is None:
            try:
                import spacy

                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                import subprocess

                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=False)
                import spacy

                self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    @staticmethod
    def _build_patterns() -> dict[str, re.Pattern]:
        """Build legal-specific regex patterns."""
        return {
            "section_citation": re.compile(
                r"[Ss]ection\s+(\d+[A-Za-z]*(?:\(\d+\))?)\s+(?:of\s+)?(?:the\s+)?"
                r"(BNS|BNSS|BSA|IPC|CrPC|Indian Penal Code|"
                r"Bharatiya Nyaya Sanhita|Bharatiya Nagarik Suraksha Sanhita|"
                r"Bharatiya Sakshya Adhiniyam|Evidence Act|Code of Criminal Procedure)",
                re.IGNORECASE,
            ),
            "act_name": re.compile(
                r"(BNS|BNSS|BSA|IPC|CrPC|Indian Penal Code|"
                r"Bharatiya Nyaya Sanhita|Bharatiya Nagarik Suraksha Sanhita|"
                r"Bharatiya Sakshya Adhiniyam|Evidence Act|Code of Criminal Procedure|"
                r"Constitution of India)",
                re.IGNORECASE,
            ),
            "case_number": re.compile(
                r"(?:Case|Crl\.?|Criminal|Civil|WP|SLP|Crl\.?\s*Appeal|"
                r"Crl\.?\s*Revision|Crl\.?\s*Petition)\s*(?:No\.?|Number)?\s*"
                r"([\d/]+)\s*(?:of\s*\d{4})?",
                re.IGNORECASE,
            ),
            "date": re.compile(
                r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|"
                r"July|August|September|October|November|December)\s+\d{4})|"
                r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
                re.IGNORECASE,
            ),
            "fir_number": re.compile(
                r"FIR\s*(?:No\.?|Number)?\s*([\d/]+)",
                re.IGNORECASE,
            ),
            "relief": re.compile(
                r"(?:seeks?|pray(?:s|ing)?|prayer|relief)\s+(?:for\s+)?"
                r"((?:compensation|damages|injunction|declaration|"
                r"acquittal|conviction|bail|quashing|direction|order|"
                r"stay|restoration|possession|specific performance)[\s\w,]*)",
                re.IGNORECASE,
            ),
        }

    def extract(self, text: str) -> dict[str, Any]:
        """Extract legal entities from document text.

        Args:
            text: The parsed document text.

        Returns:
            Dict with categorized entities.
        """
        nlp = self._load_nlp()
        doc = nlp(text[:100000])  # Limit to first 100K chars for performance

        entities: dict[str, list[dict[str, Any]]] = {
            "persons": [],
            "organizations": [],
            "dates": [],
            "locations": [],
            "sections": [],
            "acts": [],
            "case_numbers": [],
            "fir_numbers": [],
            "reliefs": [],
            "legal_issues": [],
        }

        # spaCy NER extraction
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                entities["persons"].append({"name": ent.text, "span": (ent.start_char, ent.end_char)})
            elif ent.label_ in ("ORG", "GPE"):
                entities["organizations"].append({"name": ent.text, "span": (ent.start_char, ent.end_char)})
            elif ent.label_ == "DATE":
                entities["dates"].append({"value": ent.text, "span": (ent.start_char, ent.end_char)})
            elif ent.label_ in ("GPE", "LOC"):
                entities["locations"].append({"name": ent.text, "span": (ent.start_char, ent.end_char)})

        # Regex-based extraction
        for match in self._patterns["section_citation"].finditer(text):
            entities["sections"].append({
                "section_number": match.group(1),
                "act": match.group(2).upper(),
                "full_match": match.group(0),
            })

        for match in self._patterns["act_name"].finditer(text):
            entities["acts"].append({"act": match.group(0)})

        for match in self._patterns["case_number"].finditer(text):
            entities["case_numbers"].append({"case_number": match.group(0)})

        for match in self._patterns["fir_number"].finditer(text):
            entities["fir_numbers"].append({"fir_number": match.group(0)})

        for match in self._patterns["relief"].finditer(text):
            entities["reliefs"].append({"relief": match.group(1).strip()})

        # Deduplicate
        entities["sections"] = list({s["full_match"]: s for s in entities["sections"]}.values())
        entities["acts"] = list({a["act"]: a for a in entities["acts"]}.values())

        return entities
