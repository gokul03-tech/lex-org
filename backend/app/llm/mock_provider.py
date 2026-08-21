"""Mock LLM provider for development and testing.

Returns deterministic responses based on the prompt content.
Enables full system testing without requiring GPU or downloaded models.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.llm.provider import LLMProvider


class MockProvider(LLMProvider):
    """Deterministic mock LLM for development without GPU access.

    Generates plausible legal-sounding responses based on keyword matching.
    """

    def __init__(self, model_name: str = "mock", **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        """Generate a mock legal response based on prompt content."""
        prompt_lower = prompt.lower()

        # Detect query intent from keywords
        if any(kw in prompt_lower for kw in ["section", "bnss", "bns", "bsa", "ipc"]):
            return self._mock_section_response(prompt)
        elif any(kw in prompt_lower for kw in ["summarize", "summary", "facts", "case"]):
            return self._mock_case_summary(prompt)
        elif any(kw in prompt_lower for kw in ["contradiction", "conflict", "inconsistent"]):
            return self._mock_contradiction_response(prompt)
        elif any(kw in prompt_lower for kw in ["evidence", "reliability", "proof"]):
            return self._mock_evidence_response(prompt)
        elif any(kw in prompt_lower for kw in ["strategy", "recommend", "approach"]):
            return self._mock_strategy_response(prompt)
        elif any(kw in prompt_lower for kw in ["risk", "probability", "likelihood"]):
            return self._mock_risk_response(prompt)
        elif any(kw in prompt_lower for kw in ["procedure", "compliance", "jurisdiction"]):
            return self._mock_procedural_response(prompt)
        else:
            return self._mock_general_response(prompt)

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate a mock structured response that complies with the requested schema."""
        # Extract the case document text from the prompt
        properties = output_schema.get("properties", {})
        doc_text = ""
        doc_match = re.search(r"Case Document\(s\):\n(.*?)(\n\nAdditional Query:|\Z)", prompt, re.DOTALL)
        if doc_match:
            doc_text = doc_match.group(1).strip()
        else:
            doc_text = prompt

        doc_text_lower = doc_text.lower()

        from app.document_pipeline.metadata_extractor import LegalMetadataExtractor
        extractor = LegalMetadataExtractor()
        meta_extracted = extractor.extract(doc_text)

        petitioner = meta_extracted["petitioner"].get("value") if meta_extracted["petitioner"].get("status") == "extracted" else "the petitioner"
        respondent = meta_extracted["respondent"].get("value") if meta_extracted["respondent"].get("status") == "extracted" else "the respondent"
        court = meta_extracted["court"].get("value") if meta_extracted["court"].get("status") in ("extracted", "inferred") else "the court"
        decision_date = meta_extracted["decision_date"].get("value") if meta_extracted["decision_date"].get("status") == "extracted" else "Relevant Date"
        judges = meta_extracted["presiding_judges"].get("value") or []

        # Extract witnesses and key entities dynamically
        witnesses = []
        for wm in re.finditer(r"\b(PW\s*\d+|P\.W\.\s*\d+|Panch\s+Witnesses?|P\.I\.\s+[A-Z][a-z]+|Chemical\s+Analyser)\b", doc_text, re.IGNORECASE):
            w_str = wm.group(1).strip()
            if w_str not in witnesses:
                witnesses.append(w_str)
                if len(witnesses) >= 6:
                    break

        # Extract facts dynamically
        facts = []
        sentences = [s.strip() for s in re.split(r"[.!?\n]", doc_text) if len(s.strip()) > 35]
        for s in sentences:
            if not any(k in s.lower() for k in ["versus", "vs.", "coram:", "bench:", "judgment", "order", "page", "section 111"]):
                facts.append(s.replace("  ", " ") + ".")
                if len(facts) >= 4:
                    break
        if not facts:
            facts = [
                f"The matter arises before the {court} involving {petitioner} and {respondent}.",
                "The trial record encompasses witness testimonies, official panchnama, and documentary records.",
                "The legal submissions contest the procedural and statutory grounds established during the proceedings."
            ]

        # Extract legal issues dynamically
        legal_issues = []
        whether_matches = re.findall(r"([A-Z][^.!?]*?whether[^.!?]*?\?)", doc_text, re.IGNORECASE)
        for m in whether_matches:
            cleaned = m.strip().replace("\n", " ")
            if 20 < len(cleaned) < 220:
                legal_issues.append(cleaned)

        # Look for sections mentioned
        sections_found = re.findall(r"(?:Section|Sec\.)\s*(\d+[A-Za-z]*(?:\([a-z0-9]+\))?)", doc_text, re.IGNORECASE)
        for s in list(dict.fromkeys(sections_found))[:3]:
            legal_issues.append(f"Whether the requirements of Section {s} are satisfied under the facts of the case.")

        if not legal_issues:
            legal_issues = [
                f"Whether the claims of {petitioner} are legally sustainable against {respondent}.",
                "Whether statutory and procedural compliance was properly adhered to by the investigating authorities."
            ]

        # Label inferred issues
        labeled_issues = []
        for issue in legal_issues:
            if "whether" in issue.lower() and "satisfied under the facts" not in issue.lower():
                labeled_issues.append(issue)
            else:
                labeled_issues.append(f"AI-inferred legal issue: {issue}")

        # Extract timeline dynamically
        timeline = []
        for match in re.finditer(r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})", doc_text, re.IGNORECASE):
            dt = match.group(1)
            start = max(0, match.start() - 40)
            end = min(len(doc_text), match.end() + 60)
            event_desc = doc_text[start:end].strip().replace("\n", " ")
            if len(event_desc) > 30:
                timeline.append({"date": dt, "event": event_desc[:120] + "..."})
                if len(timeline) >= 4:
                    break
        if not timeline:
            timeline = [{"date": decision_date if decision_date != "Not found in document" else "Judgment Date", "event": "Judgment/Order delivered by the court"}]

        # 1. Case Understanding Agent Schema
        if "summary" in properties and "facts" in properties and "parties" in properties:
            return {
                "summary": f"This matter before the {court} concerns {petitioner} versus {respondent}, addressing questions of statutory compliance, factual reliability of evidence, and procedural legality.",
                "facts": facts,
                "parties": {"plaintiff": petitioner, "defendant": respondent, "others": []},
                "legal_issues": labeled_issues,
                "timeline": timeline,
                "entities": {"courts": [court], "judges": judges, "advocates": [], "witnesses": witnesses, "organizations": []}
            }

        # 2. Evidence Reliability Agent Schema
        if "overall_score" in properties and "items" in properties and "summary" in properties:
            evidence_items = []
            for term in ["agreement", "contract", "receipt", "FIR", "statement", "report", "policy"]:
                if term in doc_text_lower:
                    evidence_items.append({
                        "description": f"Documentary evidence concerning {term}.",
                        "source_score": 0.9,
                        "corroboration": 0.8,
                        "chain_of_custody": 0.85,
                        "consistency": 0.9,
                        "relevance": 0.95,
                        "overall": 0.88,
                        "notes": f"Explicitly cited in the judgment text."
                    })
            if not evidence_items:
                evidence_items = [
                    {
                        "description": f"Documentary records submitted by {petitioner}.",
                        "source_score": 0.8,
                        "corroboration": 0.7,
                        "chain_of_custody": 0.75,
                        "consistency": 0.8,
                        "relevance": 0.9,
                        "overall": 0.79,
                        "notes": "Filed in the proceedings."
                    }
                ]
            return {
                "overall_score": sum(e["overall"] for e in evidence_items) / len(evidence_items),
                "items": evidence_items,
                "summary": f"Documentary evidence regarding the claims of {petitioner} vs {respondent} is analyzed."
            }

        # 3. Contradiction Detection Agent Schema
        if "contradictions" in properties and "overall_contradiction_score" in properties:
            return {
                "contradictions": [
                    {
                        "type": "claim_discrepancy",
                        "statement_a": f"{petitioner} claims entitlement to full relief under the relevant provisions.",
                        "statement_b": f"{respondent} denies liability and highlights procedural non-compliance.",
                        "severity": "medium",
                        "confidence": 0.8,
                        "resolvable": True,
                        "notes": "Inherent conflict between the claims of the parties."
                    }
                ],
                "overall_contradiction_score": 0.25
            }

        # 4. Procedural Compliance Agent Schema
        if "compliance_score" in properties and "violations" in properties:
            return {
                "compliance_score": 0.9,
                "checks": [
                    {"aspect": "Filing Timeline", "status": "compliant", "score": 0.95, "notes": "Filing matches statutory timeline"},
                    {"aspect": "Jurisdiction", "status": "compliant", "score": 1.0, "notes": f"Jurisdiction established at {court}"}
                ],
                "violations": [],
                "summary": "Procedural compliance is high. All filings and timelines are within statutory limitation periods."
            }

        # 5. Legal Reasoning Agent Schema
        if "issues_identified" in properties and "rules" in properties and "application" in properties:
            rules = []
            for s in sections_found[:2]:
                rules.append({"section": f"Section {s}", "provision": f"Governs statutory rules mentioned in case."})
            if not rules:
                rules = [{"section": "Applicable Law", "provision": "Governs the rights and liabilities under the facts."}]
            return {
                "issues_identified": labeled_issues,
                "rules": rules,
                "application": f"The facts show that {petitioner} has provided sufficient prima facie evidence of claim validity, whereas {respondent} has raised procedural objections.",
                "conclusion": f"The case merits a favorable advisory for {petitioner} subject to verification of raw evidence records.",
                "alternative_interpretations": [f"The respondent ({respondent}) may argue lack of notice or statutory limitation."],
                "confidence": 0.85
            }

        # 6. Strategy Recommendation Agent Schema
        if "strategies" in properties and "recommended_strategy" in properties:
            return {
                "strategies": [
                    {
                        "name": "Amicable Settlement",
                        "description": f"Enter out-of-court mediation with {respondent} to resolve claims quickly.",
                        "legal_basis": ["Section 89 CPC / BNSS guidelines"],
                        "success_probability": 0.75,
                        "pros": ["Low cost", "Guaranteed outcome", "Time saving"],
                        "cons": ["Potential compromise on claim value"],
                        "recommended_actions": ["Submit a settlement proposal to respondent"],
                        "fallback": "Proceed with full litigation if mediation fails."
                    },
                    {
                        "name": "Aggressive Litigation",
                        "description": f"Proceed with full trial on merits against {respondent}.",
                        "legal_basis": ["Statutory provisions cited in judgment"],
                        "success_probability": 0.65,
                        "pros": ["Potential full recovery"],
                        "cons": ["High cost", "Significant delay", "Unpredictable outcome"],
                        "recommended_actions": ["File application for early hearing"],
                        "fallback": "Consider mediation if court observations are unfavorable."
                    }
                ],
                "recommended_strategy": f"Amicable Settlement based on initial documentation strength.",
                "overall_confidence": 0.8
            }

        # 7. Risk Assessment Agent Schema
        if "overall_strength" in properties and "strengths" in properties and "weaknesses" in properties:
            return {
                "overall_strength": 0.75,
                "strengths": [f"Well-documented initial claim by {petitioner}.", "Favorable statutory interpretations."],
                "weaknesses": [f"Procedural delays or lack of pre-suit notice to {respondent}."],
                "outcome_probabilities": {
                    "favorable": 0.65,
                    "unfavorable": 0.15,
                    "settlement": 0.20
                },
                "key_risks": ["Potential limitation period objections."],
                "mitigation": ["Draft a strong reply highlighting exceptions to limitation rules."],
                "confidence": 0.85
            }

        # Fallback dynamic generic schema matching
        result = {}
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "string")
            if prop_type == "string":
                result[prop_name] = f"Mock {prop_name} response"
            elif prop_type == "number":
                result[prop_name] = 0.85
            elif prop_type == "integer":
                result[prop_name] = 1
            elif prop_type == "boolean":
                result[prop_name] = True
            elif prop_type == "array":
                result[prop_name] = []
            elif prop_type == "object":
                result[prop_name] = {}

        return result


    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        """Stream mock tokens with a small delay for realism."""
        import time

        response = self.generate(prompt, system_prompt, max_tokens, temperature)
        words = response.split()
        for word in words:
            yield word + " "
            time.sleep(0.01)

    # ── Mock Response Generators ─────────────────────────────

    def _mock_section_response(self, prompt: str) -> str:
        """Mock a legal section lookup."""
        section_match = re.search(r"[Ss]ection\s+(\d+[A-Za-z]*)", prompt)
        section_num = section_match.group(1) if section_match else "applicable"
        return (
            f"Section {section_num} of the relevant statute provides the legal framework "
            f"for this matter. The provision establishes the essential elements, procedural "
            f"requirements, and applicable standards. [Source: Section {section_num}, "
            f"Bharatiya Nyaya Sanhita 2023]\n\n"
            f"The key elements required under this section include: "
            f"(1) a specific act or omission as defined by law, "
            f"(2) the requisite mental state (mens rea), and "
            f"(3) the presence of aggravating or mitigating circumstances as applicable."
        )

    def _mock_case_summary(self, prompt: str) -> str:
        """Mock a case summary."""
        return (
            "CASE SUMMARY:\n\n"
            "Parties: The Petitioner (plaintiff) vs. The Respondent (defendant)\n"
            "Court: District Court / High Court (as applicable)\n\n"
            "Facts of the Case:\n"
            "The case involves allegations concerning [subject matter]. "
            "The petitioner claims that [key allegations], while the respondent "
            "contends that [counter-arguments]. Key evidence includes "
            "[documentary evidence, witness testimony, forensic reports].\n\n"
            "Legal Issues Identified:\n"
            "1. Whether the essential elements of the alleged offence are satisfied.\n"
            "2. Whether procedural requirements under BNSS 2023 were complied with.\n"
            "3. Whether the evidence presented meets the admissibility standards "
            "under the Bharatiya Sakshya Adhiniyam 2023."
        )

    def _mock_contradiction_response(self, prompt: str) -> str:
        """Mock contradiction analysis."""
        return (
            "CONTRADICTION ANALYSIS:\n\n"
            "After cross-referencing all available evidence and witness statements, "
            "the following contradictions have been identified:\n\n"
            "1. [MINOR CONTRADICTION] Witness A's statement regarding the timeline "
            "differs from the documentary evidence by approximately 30 minutes. "
            "Confidence: 0.75\n\n"
            "2. [MATERIAL CONTRADICTION] The medical report findings are inconsistent "
            "with the alleged sequence of events as described in the FIR. "
            "Confidence: 0.92\n\n"
            "Recommended Action: Further investigation or cross-examination "
            "is advised to resolve these inconsistencies."
        )

    def _mock_evidence_response(self, prompt: str) -> str:
        """Mock evidence reliability assessment."""
        return (
            "EVIDENCE RELIABILITY ASSESSMENT:\n\n"
            "Evidence Item 1: Documentary Evidence\n"
            "  - Source Reliability: 0.90 (official government records)\n"
            "  - Corroboration: Supported by 2 independent sources\n"
            "  - Chain of Custody: Properly maintained\n"
            "  - Overall Score: 0.88\n\n"
            "Evidence Item 2: Witness Testimony\n"
            "  - Source Reliability: 0.65 (single witness, no corroboration)\n"
            "  - Corroboration: Not independently verified\n"
            "  - Consistency: Minor inconsistencies noted\n"
            "  - Overall Score: 0.62"
        )

    def _mock_strategy_response(self, prompt: str) -> str:
        """Mock litigation strategy recommendation."""
        return (
            "LITIGATION STRATEGY RECOMMENDATION:\n\n"
            "Option A: Pursue Summary Judgment\n"
            "  Pros: Faster resolution, lower costs, suitable when facts are undisputed\n"
            "  Cons: Limited discovery, risk of denial if material facts disputed\n"
            "  Success Probability: 0.65\n\n"
            "Option B: Full Trial with Discovery\n"
            "  Pros: Comprehensive evidence gathering, witness examination\n"
            "  Cons: Higher costs, longer timeline, greater uncertainty\n"
            "  Success Probability: 0.55\n\n"
            "RECOMMENDATION: Option A with targeted discovery on key disputed facts."
        )

    def _mock_risk_response(self, prompt: str) -> str:
        """Mock risk assessment."""
        return (
            "RISK ASSESSMENT:\n\n"
            "Overall Case Strength: Moderate (0.55)\n\n"
            "Key Strengths:\n"
            "  - Strong documentary evidence on core issues\n"
            "  - Favorable legal precedent in similar matters\n\n"
            "Key Weaknesses:\n"
            "  - Conflicting witness testimony\n"
            "  - Jurisdictional questions require clarification\n\n"
            "Litigation Risk: Moderate-High\n"
            "Settlement Recommendation: Consider ADR before proceeding to trial."
        )

    def _mock_procedural_response(self, prompt: str) -> str:
        """Mock procedural compliance check."""
        return (
            "PROCEDURAL COMPLIANCE ASSESSMENT (BNSS 2023):\n\n"
            "1. FIR Registration: COMPLIANT - Filed within prescribed timeline\n"
            "2. Arrest Procedure: COMPLIANT - Due process followed per Section 35 BNSS\n"
            "3. Evidence Collection: PARTIALLY COMPLIANT - Chain of custody gaps noted\n"
            "4. Jurisdiction: VERIFIED - Proper territorial jurisdiction established\n"
            "5. Limitation Period: COMPLIANT - Filed within statutory limitation\n\n"
            "Overall Compliance Score: 0.80/1.00"
        )

    def _mock_general_response(self, prompt: str) -> str:
        """Mock general legal response."""
        return (
            "Based on the information provided, a comprehensive legal analysis "
            "has been conducted. The applicable legal framework includes the "
            "relevant provisions of the Bharatiya Nyaya Sanhita 2023 (BNS), "
            "Bharatiya Nagarik Suraksha Sanhita 2023 (BNSS), and the "
            "Bharatiya Sakshya Adhiniyam 2023 (BSA), where applicable.\n\n"
            "For matters predating July 1, 2024, the Indian Penal Code 1860 (IPC), "
            "Code of Criminal Procedure 1973 (CrPC), and Indian Evidence Act 1872 "
            "continue to govern.\n\n"
            "IMPORTANT DISCLAIMER: This analysis is an AI-assisted advisory output "
            "for research and reference purposes only. It does not constitute legal "
            "advice. Please consult a qualified legal professional."
        )
