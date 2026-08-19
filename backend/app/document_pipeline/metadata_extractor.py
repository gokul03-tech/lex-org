"""Metadata extractor for legal documents.

Extracts structured metadata including title, date, parties,
courts, and document type from legal document text.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class LegalMetadataExtractor:
    """Extract structured metadata from legal document text with strict grounding and inference rules."""

    def __init__(self) -> None:
        pass

    def extract(self, text: str, filename: str = "") -> dict[str, Any]:
        """Extract all metadata from legal text following Master Grounding Rules.

        Args:
            text: The full document text.
            filename: Original filename for fallback extraction.

        Returns:
            Dict of extracted metadata fields with explicit status tags.
        """
        head = text[:8000]
        tail = text[-6000:] if len(text) > 6000 else ""
        full_sample = text[:35000]
        word_count = len(text.split()) if text else 0

        # 1. Case Title & Parties (Rule 8 Title Fallback)
        title_res = self._extract_title_and_parties(text, filename)
        case_title = title_res["case_title"]
        petitioner = title_res["petitioner"]
        respondent = title_res["respondent"]

        # 2. Citations
        citations = self._extract_citations(head)

        # 3. Court (Explicit + Reporter Inferences)
        court_res = self._extract_court_with_inference(head, citations)

        # 4. Decision Date
        date_res = self._extract_decision_date(head)

        # 5. Presiding Judges (Header + Concurring Tail Judges)
        judges_res = self._extract_judges(head, tail)

        # 6. Court Matter & Filing Number
        matter_res = self._extract_court_matter(head)
        filing_res = self._extract_filing_number(head)

        # 7. Acts Mentioned
        acts_res = self._extract_acts(full_sample)

        # 8. Case Category
        category_res = self._detect_category(text)

        metadata: dict[str, Any] = {
            "filename": filename,
            "title": case_title,
            "case_title": case_title,
            "court": court_res,
            "jurisdiction": {"value": "India", "status": "extracted"},
            "document_type": {"value": self._detect_document_type(head, filename), "status": "extracted"},
            "court_matter": matter_res,
            "case_number": matter_res,
            "filing_number": filing_res,
            "decision_date": date_res,
            "date": date_res,
            "presiding_judges": judges_res,
            "judges": judges_res,
            "petitioner": petitioner,
            "respondent": respondent,
            "parties": {"petitioner": petitioner.get("value"), "respondent": respondent.get("value")},
            "citation_numbers": citations,
            "citation": {"value": ", ".join(citations.get("value") or []) if citations.get("value") else None, "status": citations.get("status")},
            "acts_referenced": acts_res,
            "acts_mentioned": acts_res,
            "language": {"value": "English", "status": "extracted"},
            "case_category": category_res,
            "word_count": word_count
        }

        return metadata

    def _extract_title_and_parties(self, text: str, filename: str) -> dict[str, Any]:
        """Extract case title and split into petitioner/respondent with civil/criminal unification."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first_lines = "\n".join(lines[:12])

        # Match Title containing vs / v.
        vs_match = re.search(
            r'([A-Z0-9\.\'\s\-\&\,]+?)\s+(?:versus|vs\.?|v\.\s*s\s*\.?|v\s*\.\s*|\.\.\.\s*Appellant\s+Versus)\s+([A-Z0-9\.\'\s\-\&\,]+?)(?:\s+(?:\.\.\.\s*on|\.\.\.\s*Respondent|\.\.\.\s*Defendant|on\s+\d{1,2}|\n|\Z))',
            first_lines,
            re.IGNORECASE
        )

        petitioner = None
        respondent = None
        case_title = None

        if vs_match:
            p_raw = vs_match.group(1).strip()
            r_raw = vs_match.group(2).strip()

            # Clean OCR artifacts and trailing words
            p_clean = self._clean_party_name(p_raw)
            r_clean = self._clean_party_name(r_raw)

            if p_clean and r_clean:
                petitioner = p_clean
                respondent = r_clean
                case_title = f"{p_clean} vs {r_clean}"

        # If not found in first lines, try filename or first non-empty line
        if not case_title:
            for line in lines[:3]:
                if 5 < len(line) < 150 and not any(k in line.lower() for k in ["indiankanoon", "http", "page 1", "section"]):
                    case_title = line
                    break

        if not case_title and filename:
            case_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")

        return {
            "case_title": {"value": case_title, "status": "extracted" if case_title else "not_found"},
            "petitioner": {"value": petitioner, "status": "extracted" if petitioner else "not_found"},
            "respondent": {"value": respondent, "status": "extracted" if respondent else "not_found"}
        }

    def _clean_party_name(self, name: str) -> str:
        """Strip procedural labels and OCR splits."""
        # OCR fix: 'Ramj i' -> 'Ramji'
        cleaned = re.sub(r'(\b[A-Za-z]{2,})\s+([a-z]\b)', r'\1\2', name)
        # Strip trailing/leading procedural tokens
        for tag in [
            r'\.\.\.\s*Appellant', r'\.\.\.\s*Petitioner', r'\.\.\.\s*Plaintiff', r'\.\.\.\s*Applicant',
            r'\.\.\.\s*Complainant', r'\.\.\.\s*Accused', r'\.\.\.\s*Respondent', r'\.\.\.\s*Defendant',
            r'\bAppellant\b', r'\bPetitioner\b', r'\bPlaintiff\b', r'\bRespondent\b', r'\bDefendant\b',
            r'\bAccused\b', r'\bComplainant\b', r'\bJUDGMENT\b', r'\bOrder\b'
        ]:
            cleaned = re.sub(tag, '', cleaned, flags=re.IGNORECASE).strip()

        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .,-')
        # Return last segment if multi-line
        if '\n' in cleaned:
            cleaned = cleaned.split('\n')[-1].strip()
        return cleaned if len(cleaned) > 2 else ""

    def _extract_citations(self, text: str) -> dict[str, Any]:
        """Extract compressed & standard Indian citation formats without spaces."""
        citations = []
        patterns = [
            r'\(\d{4}\)\s*\d+\s*[A-Z]+\s*\d+',      # (1994)96BOMLR808
            r'\d{4}\s*CRILJ\s*\d+',                  # 1994CRILJ1987
            r'AIR\s*\d{4}\s*[A-Z]+\s*\d+',           # AIR1958KANT53, AIR1958MYS53
            r'\[\d{4}\]\s*\d+\s*SCR\s*\d+',          # [1958] SCR 53
            r'\d{4}\s*SCC\s*\(\w+\)\s*\d+',          # 2023 SCC (Cri) 12
            r'\d{4}\s*\(\d+\)\s*SCALE\s*\d+',        # 2022 (4) SCALE 100
            r'ILR\s*\d{4}\s*[A-Z]+\s*\d+',           # ILR 1958 KAR 53
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                cit = m.group(0).strip().replace(" ", "")
                if cit not in citations:
                    citations.append(cit)

        return {
            "value": citations if citations else None,
            "status": "extracted" if citations else "not_found"
        }

    def _extract_court_with_inference(self, text: str, citations: dict[str, Any]) -> dict[str, Any]:
        """Extract explicit court name or infer accurately from citation reporter codes."""
        # 1. Explicit Court Names
        explicit_patterns = [
            r'(Supreme\s+Court\s+of\s+India)',
            r'(Bombay\s+High\s+Court|High\s+Court\s+of\s+Bombay|High\s+Court\s+of\s+Judicature\s+at\s+Bombay)',
            r'(Delhi\s+High\s+Court|High\s+Court\s+of\s+Delhi)',
            r'(Karnataka\s+High\s+Court|High\s+Court\s+of\s+Karnataka|High\s+Court\s+of\s+Mysore)',
            r'(Madras\s+High\s+Court|High\s+Court\s+of\s+Madras)',
            r'(Calcutta\s+High\s+Court|High\s+Court\s+of\s+Calcutta)',
            r'(Allahabad\s+High\s+Court|High\s+Court\s+of\s+Allahabad)',
            r'([A-Z][a-zA-Z\s]{2,20}\s+High\s+Court)',
        ]
        for pat in explicit_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return {"value": m.group(1).strip(), "status": "extracted"}

        # 2. Infer from citation reporters
        cit_tokens = "".join(citations.get("value") or []) + " " + text[:2000]
        if any(rep in cit_tokens for rep in ["BOMLR", "BomCR", "BOM"]):
            return {"value": "Bombay High Court", "status": "inferred"}
        if any(rep in cit_tokens for rep in ["KANT", "MYS", "KAR"]):
            return {"value": "High Court of Mysore (Karnataka)", "status": "inferred"}
        if any(rep in cit_tokens for rep in ["SCR", "SCC", "SCALE"]):
            return {"value": "Supreme Court of India", "status": "inferred"}
        if any(rep in cit_tokens for rep in ["DLT", "DEL"]):
            return {"value": "Delhi High Court", "status": "inferred"}
        if any(rep in cit_tokens for rep in ["MLJ", "MAD"]):
            return {"value": "Madras High Court", "status": "inferred"}

        return {"value": None, "status": "not_found"}

    def _extract_decision_date(self, text: str) -> dict[str, Any]:
        """Extract judgment delivery date normalized to 'DD Month YYYY'."""
        patterns = [
            r'(?:\.\.\.\s*on|on|Decided\s+on|Dated)\s+(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})',
            r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})'
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw_d = m.group(1).replace(",", "").strip()
                # Normalize ordinal suffix '9th' -> '9'
                norm_d = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', raw_d)
                return {"value": norm_d, "status": "extracted"}

        return {"value": None, "status": "not_found"}

    def _extract_judges(self, head: str, tail: str) -> dict[str, Any]:
        """Extract all presiding judges from headers, bench lines, and concurring end paragraphs."""
        judges = []

        # 1. Bench/Coram lines in header
        bench_m = re.search(r'(?:Coram|Bench|Author|Before)\s*:\s*([A-Z][a-zA-Z\s\.,&]+?)(?:\n|\r|\.\s)', head)
        if bench_m:
            for seg in re.split(r',|\band\b|&', bench_m.group(1)):
                j = self._clean_judge_name(seg)
                if j and j not in judges:
                    judges.append(j)

        # 2. 'NAME, J.' pattern in header
        for m in re.finditer(r'(?:Hon[\'’]?ble\s+(?:Mr\.|Mrs\.|Ms\.)?\s*Justice\s+([A-Z][a-zA-Z\s\.]+)|([A-Z][a-zA-Z\s\.]+),\s*J\b)', head):
            j = self._clean_judge_name(m.group(1) or m.group(2) or "")
            if j and j not in judges:
                judges.append(j)

        # 3. Concurring judge at the end (e.g. 'Sadasivayya, J.' ... 'I agree')
        if tail:
            for m in re.finditer(r'([A-Z][a-zA-Z\s\.]+),\s*J\b', tail):
                j = self._clean_judge_name(m.group(1))
                if j and j not in judges:
                    judges.append(j)

        return {
            "value": judges if judges else None,
            "status": "extracted" if judges else "not_found"
        }

    def _clean_judge_name(self, name: str) -> str:
        """Strip honorifics and 'J.' suffix."""
        cleaned = re.sub(r'\b(JUDGMENT|Hon[\'’]?ble|Justice|Mr\.|Mrs\.|Ms\.|J\.)\b', '', name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .,-')
        if any(k in cleaned.lower() for k in ["court", "order", "state", "police", "appellant", "versus"]):
            return ""
        return cleaned if len(cleaned) > 2 else ""

    def _extract_court_matter(self, text: str) -> dict[str, Any]:
        """Extract appeal or special case number."""
        pat = r'((?:Special\s+Case|Criminal\s+Appeal|Civil\s+Appeal|Appeal|Writ\s+Petition|W\.?P\.?|S\.?L\.?P\.?|R\.?A\.?)\s*(?:No\.?|Number)?\s*[:\-]?\s*\d+\s+of\s+\d{2,4})'
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return {"value": m.group(1).strip(), "status": "extracted"}
        return {"value": None, "status": "not_found"}

    def _extract_filing_number(self, text: str) -> dict[str, Any]:
        """Extract filing/registration number if explicitly present."""
        pat = r'((?:Filing|Registration)\s*(?:No\.?|Number)\s*[:\-]?\s*[A-Za-z0-9\/\-]+)'
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return {"value": m.group(1).strip(), "status": "extracted"}
        return {"value": None, "status": "not_found"}

    def _extract_acts(self, text: str) -> list[str]:
        """Extract explicitly cited statutes."""
        acts = []
        patterns = [
            r'\b(?:N\.?D\.?P\.?S\.?\s+Act|Narcotic\s+Drugs\s+and\s+Psychotropic\s+Substances\s+Act(?:\s*,\s*\d{4})?)\b',
            r'\b(?:I\.?P\.?C\.?|Indian\s+Penal\s+Code(?:\s*,\s*\d{4})?)\b',
            r'\b(?:Cr\.?P\.?C\.?|Code\s+of\s+Criminal\s+Procedure(?:\s*,\s*\d{4})?)\b',
            r'\b(?:BNS|Bharatiya\s+Nyaya\s+Sanhita(?:\s*,\s*\d{4})?)\b',
            r'\b(?:BNSS|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:\s*,\s*\d{4})?)\b',
            r'\b(?:BSA|Bharatiya\s+Sakshya\s+Adhiniyam(?:\s*,\s*\d{4})?)\b',
            r'\b(?:Evidence\s+Act|Indian\s+Evidence\s+Act(?:\s*,\s*\d{4})?)\b',
            r'\b(?:Insurance\s+Act(?:\s*,\s*\d{4})?)\b',
            r'\b([A-Z][a-zA-Z\s]{2,40}\s+(?:Act|Code|Sanhita|Adhiniyam)(?:\s*,\s*\d{4})?)\b',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                act_str = m.group(0).strip()
                if act_str not in acts:
                    acts.append(act_str)
                    if len(acts) >= 8:
                        break
        return acts

    def _detect_category(self, text: str) -> dict[str, Any]:
        """Classify case as criminal or civil."""
        text_lower = text[:10000].lower()
        crim_signals = sum(text_lower.count(k) for k in ["accused", "prosecution", "fir", "ndps", "conviction", "police", "penal", "crpc", "bail"])
        civ_signals = sum(text_lower.count(k) for k in ["plaintiff", "defendant", "suit", "policy", "insurance", "damages", "decree", "contract"])

        if crim_signals > civ_signals:
            return {"value": "criminal", "status": "extracted"}
        elif civ_signals > 0:
            return {"value": "civil", "status": "extracted"}
        return {"value": "unknown", "status": "not_found"}

    def _detect_document_type(self, text: str, filename: str) -> str:
        """Detect document type."""
        t_low = text[:2000].lower()
        if "judgment" in t_low or "judgement" in t_low:
            return "judgment"
        if "order" in t_low:
            return "order"
        if "petition" in t_low:
            return "petition"
        if "notice" in t_low:
            return "notice"
        return "judgment"

        scores = {k: sum(1 for kw in v if kw in combined) for k, v in indicators.items()}
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        return best if scores[best] > 0 else "judgment"
