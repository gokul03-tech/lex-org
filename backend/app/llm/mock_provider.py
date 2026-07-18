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
        """Generate a mock structured response that loosely follows the schema."""
        text_response = self.generate(prompt, system_prompt, temperature=temperature)
        return {"text": text_response, "confidence": 0.85, "source": "mock_provider"}

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
