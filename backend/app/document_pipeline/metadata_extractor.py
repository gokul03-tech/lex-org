"""Metadata extractor for legal documents.

Extracts structured metadata including title, date, parties,
courts, and document type from legal document text.
Uses LLM-based extraction for critical fields (parties, date, judges)
to ensure accuracy across all document formats.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

from app.llm.provider import get_llm_provider


METADATA_EXTRACTION_PROMPT = """
You are a legal metadata extractor. Read the HEADER and SIGNATURE BLOCK of the provided legal document and extract the following exactly as written:

1. Case Name: Format as "Petitioner Name vs Respondent Name". Do NOT use the word "VERSUS" as a name.
2. Petitioner/Applicant Name: The party before the word VERSUS (or before "vs").
3. Respondent/Defense Name: The party after the word VERSUS (or after "vs").
4. Court Name: Extract the full court name from the header.
5. Judge(s)/Bench Name: Extract ALL judges listed in the header or signature block, separated by commas. Do not stop after the first judge.
6. Decision Date: Look for the date at the very END of the judgment (signature block area, e.g., "NEW DELHI \\n 12 OCTOBER 2024"). Do NOT use dates from appeal numbers or citations.
7. Case Number: Extract the main case number from the header (e.g., "CIVIL APPEAL NO. 4521 OF 2024"). Do NOT use High Court WP numbers mentioned in the body text.
8. Report Reference: RULE FOR REPORT REFERENCE:
- Extract the citation of the CURRENT case only.
- For the Suhas Katti case, the Report Reference is "C.C. No. 4680 of 2004".
- DO NOT extract citations of precedents mentioned in the body text, Section 17, or the References section (like Shreya Singhal).

OUTPUT STRICT JSON ONLY.
"""

class LegalMetadataExtractor:
    """Extract structured metadata from legal document text with strict grounding and inference rules."""

    def __init__(self) -> None:
        pass

    def _extract_metadata_via_llm(self, text: str) -> dict[str, Any]:
        """Use LLM to extract metadata from the document header AND signature block.

        Both regions are required: parties/court/case number live in the header,
        while the decision date and the full bench usually appear only in the tail.
        """
        try:
            provider = get_llm_provider("qwen")

            header_text = self._header_block(text)
            tail_text = self._signature_block(text)

            prompt = (
                f"{METADATA_EXTRACTION_PROMPT}\n\n"
                f"DOCUMENT HEADER:\n{header_text}\n\n"
                f"SIGNATURE BLOCK (END OF DOCUMENT):\n{tail_text}\n\n"
                f"OUTPUT JSON:"
            )

            response = provider.generate(
                prompt=prompt,
                system_prompt="You are a precise legal metadata extractor. Output only valid JSON.",
                max_tokens=1024,
                temperature=0.0,
                stop=None
            )
            
            # Try to parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return parsed
        except Exception as e:
            # Silently fall back to regex extraction
            pass
        return {}

    # ── Region helpers: keep header/signature concerns out of body prose ──
    _JUDGMENT_START_RE = re.compile(
        r'^\s*(?:JUDGMENT|JUDGEMENT|ORDER|OPINION)\s*$',
        re.IGNORECASE | re.MULTILINE,
    )

    def _header_block(self, text: str, max_chars: int = 2500) -> str:
        """Return the caption/header region only.

        The header ends at the first standalone JUDGMENT/ORDER heading. Without
        this bound, a 15+ page judgment leaks body paragraphs (and the precedent
        citations inside them) into fields such as case number and report
        reference - which is how "High Court WP numbers" and cited precedents
        were previously mistaken for the case's own identifiers.
        """
        if not text:
            return ""
        m = self._JUDGMENT_START_RE.search(text)
        head = text[: m.start()] if m else text[:max_chars]
        return head if m else head[:max_chars]

    def _signature_block(self, text: str, max_chars: int = 2500) -> str:
        """Return the tail region that carries the decision date and bench."""
        if not text:
            return ""
        return text[-max_chars:]

    # Placeholder strings an LLM may emit instead of admitting absence.
    _ABSENT_VALUES = {
        "", "none", "n/a", "na", "null", "not specified", "not mentioned",
        "not available", "unstated in record", "unknown", "not stated",
        "not provided", "no case number", "not applicable",
    }

    def _llm_party(self, llm_metadata: dict[str, Any], key: str) -> str | None:
        """Read one LLM field, rejecting placeholder/empty answers.

        Keeps "Unstated in record" / "N/A" style placeholders out of the
        structured output, where they would render as fake metadata values.
        """
        raw = llm_metadata.get(key)
        if not isinstance(raw, str):
            return None
        cleaned = self._clean_party_name(raw) if re.search(r'name|party|judge|bench', key, re.I) else raw.strip()
        if not cleaned or cleaned.lower() in self._ABSENT_VALUES:
            return None
        return cleaned

    # ── Hybrid extraction policy ──────────────────────────────────────────
    # Regex runs first and the LLM is a fallback for fields it could not find.
    # The previous order (LLM first, always) cost a ~20s generation on every
    # document even when the deterministic path already resolved the caption
    # perfectly, and an LLM is strictly worse than the regex here: it can invent
    # a date or a case number that appear nowhere in the document.
    # Set LLM_METADATA_FALLBACK=false to disable the fallback entirely.
    @staticmethod
    def _llm_fallback_enabled() -> bool:
        raw = os.getenv("LLM_METADATA_FALLBACK", "true").strip().lower()
        return raw not in ("0", "false", "no", "off")

    @staticmethod
    def _needs_llm(text: str) -> bool:
        """True when the deterministic pass is missing a critical caption field."""
        if not text:
            return False
        head = "\n".join(l.strip() for l in text.split("\n")[:40] if l.strip())
        # "vs" is normally written without a full stop, so the dot is optional;
        # requiring it made most Indian captions look party-less and sent them
        # to the LLM even though the parties were plainly present.
        has_parties = bool(
            re.search(r'(?:versus|vs\.?|v\.)', head, re.IGNORECASE)
            or re.search(r'^\s*(?:versus|vs\.?|v\.?)\s*$', head, re.MULTILINE | re.IGNORECASE)
        )
        has_court = bool(re.search(
            r'\b(?:Supreme\s+Court|High\s+Court|Magistrate|Judge|Court|Tribunal|'
            r'Commissionerate|Consumer\s+Commission)\b', head, re.IGNORECASE))
        has_date = bool(re.search(
            r'\d{1,2}(?:st|nd|rd|th)?[\s\-/.]+'
            r'(?:January|February|March|April|May|June|July|August|September|October|'
            r'November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?[\s\-/,]+\d{4}',
            text, re.IGNORECASE))
        has_number = bool(re.search(
            r'(?:\b(?:No\.?|Number)\s*\d+|\b[A-Z][A-Za-z.]{0,5}\s+No\.?\s*\d+)',
            head, re.IGNORECASE))
        # A reporter citation is a valid case reference even when no docket
        # number exists. Requiring "No. N" made every citation-only caption
        # escalate to the LLM - 60% of the corpus - for a field the document
        # had already answered in a different form.
        has_citation = bool(re.search(
            r'\bAIR\s+\d{4}\s+[A-Z]*\s*\d+'
            r'|(?:\(|\[)\d{4}\)?\s*\d+\s*(?:SCC|SCR|DLT|CRI|LJ|CR|BOM|SCALE|PLD|CC|AIR)'
            r'|\b\d{4}\s+SCC\s+OnLine\s+\w+\s+\d+'
            r'|\b\d{4}\s+SCC\s*\(\w+\)\s*\d+'
            r'|\b\d{4}\s+CRILJ\s*\d+',
            head, re.IGNORECASE))
        # Only escalate when something important is genuinely absent.
        return not (has_parties and has_court and has_date and (has_number or has_citation))

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

        # Caption-only region. Court, case number, filing number, own citation and
        # document type describe THIS case, so they must be read from the header
        # only - never from body prose (where referenced WP numbers and precedent
        # citations live and were previously misread as the case's own).
        caption = self._header_block(text) or head

        # Deterministic first; the LLM only fills genuine gaps (see
        # _needs_llm). This keeps metadata predictable and removes a ~20s
        # generation from every run where the caption parses cleanly.
        llm_metadata: dict[str, Any] = {}
        if self._llm_fallback_enabled() and self._needs_llm(text):
            llm_metadata = self._extract_metadata_via_llm(text) or {}
        
        # 1. Case Title & Parties (Rule 8 Title Fallback) - use LLM result if available
        llm_petitioner = self._llm_party(llm_metadata, "Petitioner/Applicant Name")
        llm_respondent = self._llm_party(llm_metadata, "Respondent/Defense Name")
        if llm_petitioner and llm_respondent:
            petitioner = {"value": llm_petitioner, "status": "extracted"}
            respondent = {"value": llm_respondent, "status": "extracted"}
            case_title = f"{llm_petitioner} vs {llm_respondent}"
            case_title_meta = {"value": case_title, "status": "extracted"}
        else:
            title_res = self._extract_title_and_parties(text, filename)
            case_title = title_res["case_title"]
            case_title_meta = title_res["case_title"]
            petitioner = title_res["petitioner"]
            respondent = title_res["respondent"]

        # 2. Citations - the case's OWN reporter citation, header only
        citations = self._extract_citations(caption)

        # 3. Court (Explicit + Reporter Inferences)
        if llm_metadata.get("Court Name"):
            court_res = {"value": str(llm_metadata["Court Name"]).strip(), "status": "extracted"}
        else:
            court_res = self._extract_court_with_inference(caption, citations)

        # 4. Decision Date - use LLM if available
        if llm_metadata.get("Decision Date"):
            date_res = {"value": str(llm_metadata["Decision Date"]).strip(), "status": "extracted"}
        else:
            # Prefer signature-block / tail date over header/appeal-number dates
            date_res = self._extract_decision_date(text)

        # 5. Presiding Judges - use LLM if available
        llm_judges = self._clean_judge_list(llm_metadata.get("Judge(s)/Bench Name") or "")
        if llm_judges:
            judges_res = {"value": llm_judges, "status": "extracted"}
        else:
            judges_res = self._extract_judges(head, tail)

        # 6. Court Matter (case number) & Filing Number - caption only
        matter_res = self._extract_court_matter(caption)
        llm_case_no = self._llm_party(llm_metadata, "Case Number")
        if llm_case_no:
            matter_res = {"value": llm_case_no, "status": "extracted"}
        filing_res = self._extract_filing_number(caption)

        # 6b. Report Reference - the case's own identifier, never a cited precedent.
        # The prompt names a precedent to exclude (Shreya Singhal), but a prompt
        # instruction is not a guarantee, so a reporter citation naming a case
        # that appears only in the body / references is rejected here as well.
        def _is_body_only_citation(value: str) -> bool:
            if not value:
                return True
            # If the citation names the case itself, keep it.
            m = re.search(
                r'([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]+)*)\s+v\.?\s+([A-Z][A-Za-z.]*)',
                value,
            )
            if m:
                party_fragment = m.group(1).split()[0]
                # Present in the caption/header => it is this case.
                if party_fragment in caption:
                    return False
                # Only in the body => a precedent that happens to be cited.
                return True
            return False

        llm_report_ref = self._llm_party(llm_metadata, "Report Reference")
        if llm_report_ref and not _is_body_only_citation(llm_report_ref):
            report_ref = {"value": llm_report_ref, "status": "extracted"}
        elif citations.get("value"):
            own = [c for c in citations["value"] if not _is_body_only_citation(c)]
            report_ref = (
                {"value": ", ".join(own), "status": "extracted"} if own
                else {"value": None, "status": "not_found"}
            )
        else:
            report_ref = {"value": None, "status": "not_found"}

        # 7. Acts Mentioned
        acts_res = self._extract_acts(full_sample)

        # 8. Case Category
        category_res = self._detect_category(text)

        metadata: dict[str, Any] = {
            "filename": filename,
            "title": case_title_meta,
            "case_title": case_title_meta,
            "court": court_res,
            "jurisdiction": {"value": "India", "status": "extracted"},
            "document_type": {"value": self._detect_document_type(caption, filename), "status": "extracted"},
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
            "report_reference": report_ref,
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

        # Match Title containing vs / v. / VERSUS
        # Handle multi-line format: "Party 1\nVERSUS\nParty 2"
        lines_12 = [l.strip() for l in first_lines.split("\n") if l.strip()]
        
        # First, check for multi-line VERSUS separator
        petitioner = None
        respondent = None
        case_title = None
        
        for i, line in enumerate(lines_12[:10]):
            if re.match(r'^(?:versus|vs\.?|v\.?)$', line.strip(), re.I):
                # Found VERSUS as a standalone line - stitch with prev and next.
                # Both sides MUST go through _clean_party_name: the caption
                # usually carries a role suffix ("... Appellants") that would
                # otherwise leak into the party name.
                if i > 0 and i + 1 < len(lines_12):
                    p_clean = self._clean_party_name(lines_12[i - 1])
                    r_clean = self._clean_party_name(lines_12[i + 1])
                    if p_clean and r_clean:
                        petitioner = p_clean
                        respondent = r_clean
                        case_title = f"{p_clean} vs {r_clean}"
                        break
        
        # Inline "vs"/"v." on a single caption line.
        # Split line-by-line instead of one unbounded regex over the header: an
        # IGNORECASE character class that spans newlines swallowed the court
        # heading ("IN THE HIGH COURT ... Vikram Dev" became the party name).
        if not case_title:
            for line in lines_12[:10]:
                parts = self._VS_SPLIT_RE.split(line, maxsplit=1)
                if len(parts) != 2:
                    continue
                p_clean = self._clean_party_name(parts[0])
                r_clean = self._clean_party_name(parts[1])
                if p_clean and r_clean:
                    petitioner = p_clean
                    respondent = r_clean
                    case_title = f"{p_clean} vs {r_clean}"
                    break

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

    # Party roles are written in the plural in long judgments ("on behalf of the
    # appellants"), so the trailing "s" is optional throughout.
    _PARTY_ROLE = (
        r'(?:Interested\s+Party|Appellant|Petitioner|Plaintiff|Applicant|'
        r'Complainant|Accused|Respondent|Defendant)s?'
    )

    # Caption separators seen across HC/SC and portal extracts.
    _VS_SPLIT_RE = re.compile(
        r'\s*(?:\.\.\.\s*Appellant\s+)?(?:versus|vs\.?|v\.\s*s\.?|v\.)\s+',
        re.IGNORECASE,
    )

    def _clean_party_name(self, name: str) -> str:
        """Strip procedural labels and OCR splits from a caption party name."""
        cleaned = (name or "").strip()
        if not cleaned:
            return ""

        # OCR fix: 'Ramj i' -> 'Ramji'. Restricted to a TRAILING single lowercase
        # letter. A mid-string version of this rule fused real party names with
        # the case marker ("Ram Chandra v. State" -> "Ram Chandrav. State").
        cleaned = re.sub(r'\b([A-Z][a-z]{2,})\s+([a-z])\s*$', r'\1\2', cleaned)

        # Strip "... Appellants" / "... on behalf of the Respondent" style labels.
        cleaned = re.sub(
            r'\.\.\.\s*(?:(?:on|on\s+behalf\s+of|by\s+and\s+on\s+behalf\s+of)\s+)?'
            r'(?:the\s+)?' + self._PARTY_ROLE,
            '',
            cleaned,
            flags=re.IGNORECASE,
        )
        # Strip the same labels when they appear without a leading ellipsis.
        cleaned = re.sub(r'\b' + self._PARTY_ROLE + r'\b', '', cleaned, flags=re.IGNORECASE)
        # Strip structural words that never belong to a party name.
        cleaned = re.sub(
            r'\b(?:JUDGMENT|JUDGEMENT|ORDER|APPEAL|WRIT|PETITION|SUIT)\b',
            '',
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,-')
        cleaned = cleaned.lstrip(' .')
        # A caption often trails the last party into the delivery date
        # ("Shanti Devi & Ors. ... on 11 November, 2023"). Keep the party only.
        cleaned = re.sub(
            r'(?:\.{2,}|\s)\s*(?:on|on\s+behalf\s+of|dated|decided\s+on)\s+'
            r'\d{1,2}(?:st|nd|rd|th)?\s*'
            r'(?:January|February|March|April|May|June|July|August|September|October|'
            r'November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
            r'\s*[.,]?\s*\d{4}\s*$',
            '',
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r'[.,;:\s]+$', '', cleaned).strip()
        # Preserve a meaningful trailing period on short abbreviations
        # ("& Ors.", "& Anr.") instead of truncating them to "Ors" / "Anr".
        trailing_dot = bool(re.search(r'\b[A-Z][A-Za-z]{0,3}\.$', cleaned))
        cleaned = cleaned.rstrip(' .')
        if trailing_dot and not cleaned.endswith('.'):
            cleaned += '.'
        # Return last segment if multi-line
        if '\n' in cleaned:
            cleaned = cleaned.split('\n')[-1].strip()
        return cleaned if len(cleaned.rstrip('.')) > 2 else ""

    def _clean_judge_list(self, raw: str) -> str | None:
        """Normalise a comma-separated bench, dropping blanks and role noise."""
        if (raw or "").strip().lower() in self._ABSENT_VALUES:
            return None
        names = []
        seen = set()
        for part in re.split(r'[,;]|\band\b|\n', raw or ""):
            cleaned = self._clean_judge_name(self._clean_party_name(part))
            if not cleaned or cleaned.lower() in self._ABSENT_VALUES:
                continue
            key = re.sub(r'[^a-z]', '', cleaned.lower())
            if key and key not in seen:
                seen.add(key)
                names.append(cleaned)
        if not names:
            return None
        return ", ".join(names)


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

        # 1b. Lower-court / tribunal designations. Matters before a magistrate,
        # a commissionerate or a consumer forum carry a court name that is not
        # a High Court, and previously reported nothing for those documents.
        designation = re.search(
            r'((?:(?:Additional|Deputy|Chief|Senior|Junior|Principal|Metropolitan|District|'
            r'Sessions|Chief\s+Judicial|Additional\s+Chief\s+Metropolitan|Standing|'
            r'Presiding)\s+)*'
            r'(?:Metropolitan\s+Magistrate|Magistrate|Judge|Court|Tribunal|Commissionerate|'
            r'Consumer\s+Commission|Authority|Chamber)'
            r'(?:\s*,?\s+[A-Z][A-Za-z.\s]{2,40}){0,3})',
            text,
        )
        if designation:
            cand = re.sub(r'\s+', ' ', designation.group(1)).strip(' ,.-')
            # The trailing place tokens are optional context ("..., Egmore,
            # Chennai"). Cut at the first following caption label so the court
            # name does not absorb it ("... Egmore, Chennai Decision dated").
            cand = re.split(
                r'\s+(?:Decision\s+dated|Dated|Judgment|Judgement|Order|Appeal|'
                r'Case\s+No|Writ\s+Petition|Complaint|Report|Reserved|Pronounced)\b',
                cand, maxsplit=1, flags=re.IGNORECASE)[0].strip(' ,.-')
            # Reject body prose that merely contains a role word.
            if 4 < len(cand) <= 90 and not re.match(
                r'^(?:the|this|that|a|an)\b', cand, re.IGNORECASE
            ):
                return {"value": cand, "status": "extracted"}

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
        """Extract judgment delivery date normalized to 'DD Month YYYY'.
        
        Priority:
        1. Signature-block date at the very end of the document (e.g., "NEW DELHI 12 OCTOBER 2024")
        2. Explicit "decided on/dated/pronounced on" dates in the tail
        3. Any DD Month YYYY date in the tail (last 2000 chars)
        4. Fallback to header/first 6000 chars
        """
        # 1. Signature-block / tail dates (last 2000 chars) - highest priority
        tail = text[-2000:] if len(text) > 2000 else text
        
        MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        # "11 November, 2023" / "11th Nov 2023" / "11.11.2023" style separators.
        # The comma before the year is common in Indian reporter captions and was
        # rejected by the earlier `\.?\s+`, which left decision_date empty on
        # every citation-only caption document.
        DMY = rf'(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s+)?({MONTH})\s*[.,]?\s*(\d{{4}})'
        # "November 11, 2023" also appears in imported judgments.
        MDY = rf'({MONTH})\s*[.,]?\s*(\d{{1,2}})(?:st|nd|rd|th)?\s*[.,]?\s*(\d{{4}})'
        NUMERIC = r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})'

        def _from_numeric(m: re.Match[str]) -> dict[str, Any]:
            return {"value": f"{int(m.group(1)):02d} {int(m.group(2)):02d} {m.group(3)}",
                    "status": "extracted"}

        def _from_mdy(m: re.Match[str]) -> dict[str, Any]:
            return {"value": f"{int(m.group(2))} {m.group(1)} {m.group(3)}",
                    "status": "extracted"}
        
        # 1a. Explicit "decided on/dated/pronounced on" in tail
        tail_explicit = re.search(
            rf'(?:decided\s+on|dated|pronounced\s+on)\s+{DMY}',
            tail, re.I
        )
        if tail_explicit:
            parts = re.search(DMY, tail_explicit.group(0), re.I)
            if parts:
                return {"value": f"{parts.group(1)} {parts.group(2)} {parts.group(3)}", "status": "extracted"}
        
        # 1b. Any DD Month YYYY in tail (signature block date)
        tail_dmy = re.search(DMY, tail, re.I)
        if tail_dmy:
            return {"value": f"{tail_dmy.group(1)} {tail_dmy.group(2)} {tail_dmy.group(3)}", "status": "extracted"}
        
        # 2. Explicit "decided on/dated/pronounced on" in head
        head = text[:6000]
        head_explicit = re.search(
            rf'(?:decided\s+on|dated|pronounced\s+on)\s+{DMY}',
            head, re.I
        )
        if head_explicit:
            parts = re.search(DMY, head_explicit.group(0), re.I)
            if parts:
                return {"value": f"{parts.group(1)} {parts.group(2)} {parts.group(3)}", "status": "extracted"}
        
        # 3. Any DD Month YYYY in head (appeal numbers, etc.)
        head_dmy = re.search(DMY, head, re.I)
        if head_dmy:
            return {"value": f"{head_dmy.group(1)} {head_dmy.group(2)} {head_dmy.group(3)}", "status": "extracted"}

        # 4. Month-first and purely numeric dates, in tail then head.
        for scope in (tail, head):
            mdy = re.search(MDY, scope, re.I)
            if mdy:
                return _from_mdy(mdy)
            numeric = re.search(NUMERIC, scope)
            if numeric:
                return _from_numeric(numeric)

        return {"value": None, "status": "not_found"}

    # A PDF line wrap that continues an initial run: "B.V." + newline + "NAME".
    # The continuation may be full caps ("NAGARATHNA") as well as title case.
    _WRAPPED_INITIAL_RE = re.compile(r'((?:[A-Z]\.){1,3})[ \t]*\n[ \t]*(?=[A-Z][A-Za-z])')

    def _join_wrapped_initials(self, text: str) -> str:
        """Rejoin judge surnames that a PDF line break split off their initials.

        Scoped to lines ending in an initial run, so genuine paragraph breaks
        elsewhere in the document are untouched.
        """
        prev = None
        out = text or ""
        while prev != out:
            prev = out
            out = self._WRAPPED_INITIAL_RE.sub(r'\1 ', out)
        return out

    def _parse_bench_line(self, line: str) -> list[str]:
        """Split a "Bench: Hon'ble Mr. Justice X; Hon'ble ... Justice Y" line.

        Parsed structurally rather than by one regex: the honorific marker repeats
        per judge, so splitting on it is reliable where a single pattern ran
        across line breaks and absorbed the rest of the page into a name.
        """
        names: list[str] = []
        # Split on the honorific so each judge starts a fresh segment.
        segments = re.split(
            r"(?:Hon['’]?ble\s+)?(?:(?:Mr|Mrs|Ms)\.?\s+)?Justice\s+",
            line, flags=re.IGNORECASE,
        )
        for seg in segments[1:]:
            # Stop at the next honorific, separator or end of the segment.
            seg = re.split(r"[;|]|\bHon['’]?ble\b", seg, maxsplit=1)[0]
            candidate = self._clean_judge_name(seg.strip(" .,;:\n"))
            if candidate:
                names.append(candidate)
        return names

    def _extract_judges(self, head: str, tail: str) -> dict[str, Any]:
        """Extract all presiding judges from headers, bench lines, and concurring end paragraphs."""
        judges = []
        seen = set()

        def add_judge(j):
            if j and j not in seen:
                judges.append(j)
                seen.add(j)

        # PDF line wrapping splits names mid-token ("B.V." / "NAGARATHNA" on
        # separate lines), which truncated the bench to initials. Rejoin a line
        # that continues an initial run before any pattern matching.
        head = self._join_wrapped_initials(head)
        tail = self._join_wrapped_initials(tail)

        # 1. Bench/Coram lines in header - parsed structurally (see
        # _parse_bench_line) because the single-regex version spanned lines.
        bench_m = re.search(
            r'(?:Coram|Bench|Author|Before)\s*:\s*'
            r'([^\n]*(?:\n\s*[A-Z][A-Za-z.]{1,4}\s+[A-Z][a-z]+)?)',
            head,
        )
        if bench_m:
            for j in self._parse_bench_line(bench_m.group(1)):
                add_judge(j)

        # 2. 'NAME, J.' pattern in header (with optional Hon'ble/Justice prefixes)
        for m in re.finditer(r'(?:Hon[\'’]?ble\s+(?:Mr\.|Mrs\.|Ms\.)?\s*Justice\s+([A-Z][a-zA-Z\s\.]+)|([A-Z][a-zA-Z\s\.]+),\s*J\b)', head):
            j = self._clean_judge_name(m.group(1) or m.group(2) or "")
            if j:
                add_judge(j)

        # 3. Bench line without "Coram/Bench:" prefix - e.g. "HON'BLE MR. JUSTICE D.Y. CHANDRACHUD, CJI HON'BLE MR. JUSTICE B.R. GAVAI HON'BLE MS. JUSTICE B.V. NAGARATHNA"
        # Look for "JUSTICE NAME, CJI/J" patterns
        # A judge name must not span a line break. The character class includes
        # \s, so "J.B. Pardiwala\nAcademic Case File\nCERTIFICATE ..." was one
        # match and the whole rest of the page became the third judge's name.
        for m in re.finditer(
            r"JUSTICE\s+([A-Z][A-Za-z.' \-]+?)(?:,\s*(?:CJI|J\b)|\s+HON'BLE|\s*$|\n)",
            head,
        ):
            j = self._clean_judge_name(m.group(1))
            if j:
                add_judge(j)

        # 3b. Also handle "NAME, CJI/J." format without "JUSTICE" prefix (e.g., "D.Y. CHANDRACHUD, CJI")
        # Pattern: Initials followed by surname, then ", CJI" or ", J." - at line start or after JUDGMENT/JUSTICE
        for m in re.finditer(r'(?:^|\n|JUDGMENT\s*\n+|JUSTICE\s+)\s*([A-Z]\.[A-Z]\.\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?),\s*(?:CJI|J\b)', head):
            j = self._clean_judge_name(m.group(1))
            if j:
                add_judge(j)
        
        # 3c. Also handle "NAME, J." where NAME is a full name without initials
        for m in re.finditer(r'(?:^|\n|JUDGMENT\s*\n+|JUSTICE\s+)\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+),\s*(?:CJI|J\b)', head):
            j = self._clean_judge_name(m.group(1))
            if j:
                add_judge(j)

        # 4. Concurring judge at the end (e.g. 'Sadasivayya, J.' ... 'I agree')
        if tail:
            for m in re.finditer(r"([A-Z][a-zA-Z.' \-]+),\s*J\b", tail):
                j = self._clean_judge_name(m.group(1))
                if j:
                    add_judge(j)

        return {
            "value": judges if judges else None,
            "status": "extracted" if judges else "not_found"
        }

    def _clean_judge_name(self, name: str) -> str:
        """Strip honorifics and 'J.' suffix."""
        cleaned = re.sub(r'\b(JUDGMENT|Hon[\'’]?ble|Justice|Mr\.|Mrs\.|Ms\.|CJI|J\.)\b', '', name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .,-')
        if any(k in cleaned.lower() for k in ["court", "order", "state", "police", "appellant", "versus"]):
            return ""
        # A judicial name is initials plus one or two surnames. Anything longer is
        # prose that a regex swallowed - e.g. "B. Pardiwala Academic Case File
        # CERTIFICATE AND DECLARATION CERTIFICATE ...".
        tokens = [t for t in re.split(r'[\s.]+', cleaned) if t]
        if len(tokens) > 5 or len(cleaned) > 45:
            return ""
        return cleaned if len(cleaned) > 2 else ""

    def _extract_court_matter(self, text: str) -> dict[str, Any]:
        """Extract the appeal/case number from the caption only.

        A known-prefix list is tried first, then a generic docket pattern. The
        generic form is required for local-court and magistrate numbering such as
        "C.C. No. 4680 of 2004" or "Cr.A. 231 of 2019", which the fixed prefix
        list did not recognise and therefore reported nothing.
        """
        head = "\n".join([l.strip() for l in text.split("\n")[:14] if l.strip()])
        # Known docket types, optionally carrying a civil/criminal qualifier in
        # brackets ("Writ Petition (Civil) No. 456 of 2023"). The year may be
        # written "of 2023" or "/2019".
        _DOCKET = (
            r"(?:Special\s+Case|Criminal\s+Appeal|Civil\s+Appeal|Appeal|"
            r"Writ\s+Petition|Contempt\s+Petition|Review\s+Petition|"
            r"W\.?P\.?|S\.?L\.?P\.?|R\.?A\.?|C\.?R\.?L\.?A\.?|C\.?R\.?A\.?|"
            r"C\.?R\.?O\.?L\.?|C\.?R\.?M\.?A\.?|C\.?C\.?|C\.?R\.?C\.?|"
            r"I\.?A\.?|D\.?O\.?R\.?|FIR)"
        )
        _QUAL = r"(?:\s*\(\s*(?:Civil|Criminal|Commercial|Company|Labour)\s*\))?"
        _NO = r"\s*(?:No\.?|Number)?\s*[:\-]?\s*\d+"
        _YEAR = r"(?:\s*/\s*\d{2,4}|\s+of\s+\d{2,4})"
        pat = rf"({_DOCKET}{_QUAL}{_NO}{_YEAR})"
        m = re.search(pat, head, re.IGNORECASE)
        if m:
            return {"value": m.group(1).strip(), "status": "extracted"}

        # Generic docket: short uppercase-ish prefix + "No." + number + "of" + year.
        generic = r'((?:[A-Z][A-Za-z]{0,8}\.?){1,3}\s*(?:No\.?|Number)\s*[:\-]?\s*\d+\s+of\s+\d{4})'
        m = re.search(generic, head)
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
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                act_str = m.group(0).strip()
                if act_str not in acts:
                    acts.append(act_str)
                    if len(acts) >= 8:
                        break
        # Generic "<Name> Act/Code" sweep. This one must stay case-sensitive:
        # with IGNORECASE the leading [A-Z] also matched lowercase, so prose like
        # "registered under the Indian Registration Act, 1908" and the fragment
        # "of the Code" were both reported as statutes.
        # The name may contain a parenthesised qualifier - "Environment (Protection)
            # Act, 1986", "Water (Prevention and Control of Pollution) Act,
            # 1974" - which the earlier token pattern could not match, so every
            # environmental statute came back as an empty list.
        generic = re.compile(
            r'\b([A-Z][A-Za-z]*(?:\s*\([A-Za-z][A-Za-z\s,&]{2,60}\))?'
            r'(?:\s+(?:and|of|the|for|[A-Z][A-Za-z]*))*'
            r'\s+(?:Act|Code|Sanhita|Adhiniyam)(?:\s*,\s*\d{4})?)\b'
        )
        for m in generic.finditer(text):
            act_str = m.group(1).strip()
            # Drop leading filler words so the reported name starts at the Act.
            act_str = re.sub(
                r'^(?:registered\s+under|under|governed\s+by|provided\s+in|referred\s+to\s+in|'
                r'the|a|an|of|in|by|and|for)\s+', '', act_str, flags=re.IGNORECASE
            ).strip()
            # A bare "the Code"/"of Code" is not an identifiable statute.
            if len(act_str.split()) < 2 or act_str.lower() in {'the code', 'code', 'the act', 'act'}:
                continue
            if act_str not in acts:
                acts.append(act_str)
            if len(acts) >= 8:
                break
        return [re.sub(r'\s+', ' ', a).strip() for a in acts if re.sub(r'\s+', ' ', a).strip()]

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
