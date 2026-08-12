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
        prompt_lower = prompt.lower()
        properties = output_schema.get("properties", {})

        # Extract petitioner and respondent dynamically
        petitioner = "V. K. Srinivasa Setty"
        respondent = "Premier Life And General Insurance Co"
        decision_date = "09 October 1957"
        court = "High Court of Judicature"

        # Try finding common case verses/vs syntax
        vs_match = re.search(
            r'([A-Z][a-zA-Z0-9\s\.\,\-\'\&]+)\s+(?:versus|v\.\s*s\s*\.?|v\s*\.\s*|vs\s*\.?)\s+([A-Z][a-zA-Z0-9\s\.\,\-\'\&]+)',
            prompt
        )
        if vs_match:
            p_candidate = vs_match.group(1).strip().split('\n')[-1].strip()
            r_candidate = vs_match.group(2).strip().split('\n')[0].strip()
            if 3 < len(p_candidate) < 100:
                petitioner = p_candidate
            if 3 < len(r_candidate) < 100:
                respondent = r_candidate

        # Try finding date in prompt
        date_match = re.search(r'(?:on|dated)\s+(\d+\s+[A-Za-z]+\s+\d{4})', prompt)
        if date_match:
            decision_date = date_match.group(1).strip()

        # Try finding court
        if "bombay" in prompt_lower:
            court = "Bombay High Court"
        elif "delhi" in prompt_lower:
            court = "Delhi High Court"
        elif "karnataka" in prompt_lower:
            court = "High Court of Karnataka"
        elif "madras" in prompt_lower:
            court = "Madras High Court"
        elif "calcutta" in prompt_lower:
            court = "Calcutta High Court"

        # 1. Case Understanding Agent Schema
        if "summary" in properties and "facts" in properties and "parties" in properties:
            return {
                "summary": f"The case concerns a legal dispute between the petitioner, {petitioner}, and the respondent, {respondent}.",
                "facts": [
                    f"The dispute arose between {petitioner} and {respondent} regarding the performance of statutory or contractual obligations.",
                    f"{petitioner} filed a suit/application claiming relief against {respondent}.",
                    f"The matter was presented before the Court for final determination of the rights of the parties."
                ],
                "parties": {"plaintiff": petitioner, "defendant": respondent, "others": []},
                "legal_issues": [
                    f"Whether the claims of {petitioner} are legally sustainable against {respondent}.",
                    "Whether statutory compliance was properly adhered to by the parties."
                ],
                "timeline": [{"date": decision_date, "event": "Judgment/Order delivered by the court"}],
                "entities": {"courts": [court], "judges": ["Honorable Justice"], "advocates": [], "witnesses": [], "organizations": []}
            }

        # 2. Evidence Reliability Agent Schema
        if "overall_score" in properties and "items" in properties and "summary" in properties:
            return {
                "overall_score": 0.85,
                "items": [
                    {
                        "description": f"Documentary evidence regarding the claims of {petitioner} vs {respondent}.",
                        "source_score": 0.9,
                        "corroboration": 0.8,
                        "chain_of_custody": 0.85,
                        "consistency": 0.9,
                        "relevance": 0.95,
                        "overall": 0.88,
                        "notes": "Officially filed and sealed records."
                    }
                ],
                "summary": "The primary documentary evidence is highly reliable and corroborated."
            }

        # 3. Contradiction Detection Agent Schema
        if "contradictions" in properties and "overall_contradiction_score" in properties:
            return {
                "contradictions": [
                    {
                        "type": "timeline_discrepancy",
                        "statement_a": f"{petitioner} alleged date of event.",
                        "statement_b": f"{respondent} records indicating alternative date.",
                        "severity": "medium",
                        "confidence": 0.75,
                        "resolvable": True,
                        "notes": "Can be reconciled via transaction timestamps."
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
                    {"aspect": "Jurisdiction", "status": "compliant", "score": 1.0, "notes": "Proper court jurisdiction verified"}
                ],
                "violations": [],
                "summary": "Procedural compliance is high. All filings and timelines are within statutory limitation periods."
            }

        # 5. Legal Reasoning Agent Schema
        if "issues_identified" in properties and "rules" in properties and "application" in properties:
            return {
                "issues_identified": [
                    f"Whether the claims of {petitioner} are legally sustainable against {respondent}.",
                    "Whether statutory compliance was properly adhered to."
                ],
                "rules": [
                    {"section": "Section 482 / Contract Law", "provision": "Defines the scope of liability and court discretion."}
                ],
                "application": f"The facts show that {petitioner} has provided sufficient prima facie evidence of claim validity, whereas {respondent} has raised procedural objections.",
                "conclusion": f"The case merits a favorable advisory for {petitioner} subject to verification of raw evidence records.",
                "alternative_interpretations": ["The respondent may argue statutory limitation or lack of notice."],
                "confidence": 0.85
            }

        # 6. Strategy Recommendation Agent Schema
        if "strategies" in properties and "recommended_strategy" in properties:
            return {
                "strategies": [
                    {
                        "name": "Amicable Settlement",
                        "description": "Enter out-of-court mediation to resolve claims quickly.",
                        "legal_basis": ["Section 89 CPC / BNSS guidelines"],
                        "success_probability": 0.75,
                        "pros": ["Low cost", "Guaranteed outcome", "Time saving"],
                        "cons": ["Potential compromise on claim value"],
                        "recommended_actions": ["Submit a settlement proposal"],
                        "fallback": "Proceed with full litigation if mediation fails."
                    },
                    {
                        "name": "Aggressive Litigation",
                        "description": "Proceed with full trial on merits.",
                        "legal_basis": ["Statutory provisions cited"],
                        "success_probability": 0.65,
                        "pros": ["Potential full recovery"],
                        "cons": ["High cost", "Significant delay", "Unpredictable outcome"],
                        "recommended_actions": ["File application for early hearing"],
                        "fallback": "Consider mediation if court observations are unfavorable."
                    }
                ],
                "recommended_strategy": "Amicable Settlement based on initial documentation strength.",
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
