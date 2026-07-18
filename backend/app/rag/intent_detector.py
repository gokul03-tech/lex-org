"""Legal intent detector for query classification.

Classifies user queries into one of six legal intent categories:
case_understanding, section_lookup, precedent_search,
legal_reasoning, strategy_advice, procedural_check.
"""

from __future__ import annotations

from enum import Enum

from loguru import logger


class LegalIntent(str, Enum):
    """Legal query intent categories."""
    CASE_UNDERSTANDING = "case_understanding"
    SECTION_LOOKUP = "section_lookup"
    PRECEDENT_SEARCH = "precedent_search"
    LEGAL_REASONING = "legal_reasoning"
    STRATEGY_ADVICE = "strategy_advice"
    PROCEDURAL_CHECK = "procedural_check"
    GENERAL = "general"


class IntentDetector:
    """Detect legal query intent using keyword + LLM hybrid approach.

    First applies fast rule-based detection, then falls back
    to LLM classification for ambiguous queries.
    """

    # Keyword indicators for each intent type
    INTENT_KEYWORDS: dict[LegalIntent, list[str]] = {
        LegalIntent.SECTION_LOOKUP: [
            "section", "provision", "article", "clause", "subsection",
            "act", "code", "sanhita", "adhiniyam", "statute",
            "under which section", "which section", "what section",
            "ipc", "bns", "bnss", "bsa", "crpc",
        ],
        LegalIntent.PRECEDENT_SEARCH: [
            "precedent", "judgment", "case law", "ruling", "held that",
            "supreme court", "high court", "citation", "ratio decidendi",
            "overruled", "distinguished", "followed",
        ],
        LegalIntent.PROCEDURAL_CHECK: [
            "procedure", "fir", "arrest", "bail", "charge sheet",
            "jurisdiction", "limitation", "court fee", "affidavit",
            "summon", "warrant", "cognizance", "investigation",
            "compliance", "due process",
        ],
        LegalIntent.STRATEGY_ADVICE: [
            "strategy", "approach", "how to", "what should", "recommend",
            "best course", "option", "alternative", "settlement",
            "mediation", "plea bargaining", "defense", "prosecution",
        ],
        LegalIntent.CASE_UNDERSTANDING: [
            "summarize", "summary", "facts", "brief", "explain",
            "what happened", "timeline", "parties", "evidence",
            "document", "petition", "complaint",
        ],
        LegalIntent.LEGAL_REASONING: [
            "reasoning", "analysis", "apply", "argue", "interpret",
            "construction", "doctrine", "principle", "rule of law",
            "ratio", "obiter", "issue rule application conclusion",
        ],
    }

    def __init__(self) -> None:
        pass

    def detect(self, query: str) -> LegalIntent:
        """Detect the legal intent of a query.

        Args:
            query: The search query text.

        Returns:
            The detected LegalIntent category.
        """
        if not query or not query.strip():
            return LegalIntent.GENERAL

        query_lower = query.lower()

        # Score each intent based on keyword matches
        scores: dict[LegalIntent, float] = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(
                1.0 if kw in query_lower else 0.0
                for kw in keywords
            )
            # Normalize by keyword count to avoid bias towards larger lists
            scores[intent] = score / len(keywords) if keywords else 0

        # Get the best matching intent
        best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_intent]

        # If no strong match, try LLM classification
        if best_score < 0.05:
            best_intent = self._llm_classify(query)

        logger.info(f"Detected intent: {best_intent.value} (score={best_score:.3f})")
        return best_intent

    def _llm_classify(self, query: str) -> LegalIntent:
        """Use LLM to classify ambiguous queries."""
        try:
            from app.llm.qwen import get_qwen_provider

            provider = get_qwen_provider()
            prompt = (
                f"Classify the following legal query into EXACTLY ONE category:\n\n"
                f"Query: {query}\n\n"
                f"Categories:\n"
                f"- case_understanding: Summarizing or understanding case facts and documents\n"
                f"- section_lookup: Finding specific legal sections, provisions, or acts\n"
                f"- precedent_search: Searching for case law, judgments, or precedents\n"
                f"- legal_reasoning: Applying legal principles to analyze arguments\n"
                f"- strategy_advice: Seeking litigation strategy or recommendations\n"
                f"- procedural_check: Checking procedural compliance or requirements\n"
                f"- general: None of the above\n\n"
                f"ONLY output the category name (one word, lowercase):"
            )
            result = provider.generate(prompt, temperature=0.1).strip().lower()

            # Map result to enum
            intent_map = {
                "case_understanding": LegalIntent.CASE_UNDERSTANDING,
                "section_lookup": LegalIntent.SECTION_LOOKUP,
                "precedent_search": LegalIntent.PRECEDENT_SEARCH,
                "legal_reasoning": LegalIntent.LEGAL_REASONING,
                "strategy_advice": LegalIntent.STRATEGY_ADVICE,
                "procedural_check": LegalIntent.PROCEDURAL_CHECK,
            }
            return intent_map.get(result, LegalIntent.GENERAL)
        except Exception as exc:
            logger.warning(f"LLM intent classification failed: {exc}")
            return LegalIntent.GENERAL

    def get_retriever_weights(self, intent: LegalIntent) -> dict[str, float]:
        """Get retriever weight distribution for a given intent.

        Args:
            intent: The detected legal intent.

        Returns:
            Dict mapping retriever names to weight multipliers.
        """
        weights = {
            LegalIntent.SECTION_LOOKUP: {
                "vector": 0.3, "kg": 0.25, "citation": 0.35, "keyword": 0.1,
            },
            LegalIntent.PRECEDENT_SEARCH: {
                "vector": 0.3, "kg": 0.2, "citation": 0.25, "keyword": 0.25,
            },
            LegalIntent.PROCEDURAL_CHECK: {
                "vector": 0.2, "kg": 0.3, "citation": 0.3, "keyword": 0.2,
            },
            LegalIntent.STRATEGY_ADVICE: {
                "vector": 0.4, "kg": 0.2, "citation": 0.1, "keyword": 0.3,
            },
            LegalIntent.CASE_UNDERSTANDING: {
                "vector": 0.4, "kg": 0.15, "citation": 0.1, "keyword": 0.35,
            },
            LegalIntent.LEGAL_REASONING: {
                "vector": 0.3, "kg": 0.25, "citation": 0.2, "keyword": 0.25,
            },
            LegalIntent.GENERAL: {
                "vector": 0.3, "kg": 0.2, "citation": 0.2, "keyword": 0.3,
            },
        }
        return weights.get(intent, weights[LegalIntent.GENERAL])
