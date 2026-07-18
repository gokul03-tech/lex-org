"""LLM-based query rewriting for legal search.

Expands and refines user queries into multiple search variants
to improve retrieval recall across vector, keyword, and KG searches.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.config import settings


class QueryRewriter:
    """Rewrite legal queries for improved search coverage.

    Generates multiple variants of a query:
    - Original (as-is)
    - Expanded (adds legal terminology, synonyms)
    - Rephrased (alternative formulation)
    - Section-focused (emphasizes statutory references)
    """

    def __init__(self) -> None:
        pass

    def rewrite(self, query: str, intent: str | None = None) -> list[str]:
        """Generate multiple query variants for parallel retrieval.

        Args:
            query: The original search query.
            intent: Detected legal intent (used to tailor variants).

        Returns:
            List of query variant strings (including original).
        """
        if not query or not query.strip():
            return [query]

        variants = [query.strip()]

        # Try LLM-based rewriting
        try:
            from app.llm.qwen import get_qwen_provider

            provider = get_qwen_provider()
            prompt = self._build_rewrite_prompt(query, intent)
            result = provider.generate(prompt, temperature=0.3)

            # Parse generated variants
            for line in result.strip().split("\n"):
                line = line.strip()
                if line and line not in variants:
                    variants.append(line)
        except Exception as exc:
            logger.warning(f"LLM query rewrite failed, using rule-based fallback: {exc}")
            variants.extend(self._rule_based_rewrite(query, intent))

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for v in variants:
            v_lower = v.lower()
            if v_lower not in seen and len(v) > 3:
                seen.add(v_lower)
                unique.append(v)

        logger.info(f"Rewrote query into {len(unique)} variants")
        return unique[:5]  # Limit to 5 variants

    def _build_rewrite_prompt(self, query: str, intent: str | None = None) -> str:
        """Build the LLM prompt for query rewriting."""
        intent_hint = f" with legal intent type: {intent}" if intent else ""
        return f"""Rewrite the following legal search query into 3-4 alternative formulations{intent_hint}.
Each variant should use different legal terminology, synonyms, or focus on different aspects.

Original query: {query}

Generate ONE variant per line. Include:
1. An expanded version with more legal terms
2. A version that focuses on applicable sections/acts
3. A version that focuses on case law/precedents
4. A simplified keyword version

Only output the variants, one per line, no numbering or prefixes:"""

    def _rule_based_rewrite(self, query: str, intent: str | None = None) -> list[str]:
        """Rule-based query variants when LLM is unavailable."""
        variants: list[str] = []

        # Add section-focused variant
        if "section" not in query.lower():
            variants.append(f"{query} applicable legal section")

        # Add precedent-focused variant
        variants.append(f"{query} precedent case law judgment")

        # Add act-focused variants
        for act in ["BNS 2023", "BNSS 2023", "BSA 2023", "IPC 1860"]:
            if act.lower() not in query.lower():
                variants.append(f"{query} {act}")

        # Add simplified version (remove stop words)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "regarding",
                      "about", "concerning", "what", "how", "when", "where", "which"}
        words = [w for w in query.split() if w.lower() not in stop_words]
        if len(words) < len(query.split()):
            variants.append(" ".join(words))

        return variants
