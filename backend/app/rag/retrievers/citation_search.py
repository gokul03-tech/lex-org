"""Citation-based legal retriever.

Extracts legal citations from queries and retrieves
the exact section text from indexed Acts and codes.
"""

from __future__ import annotations

import re
import time
from typing import Any

from loguru import logger


class CitationRetriever:
    """Direct citation lookup for legal sections.

    Recognizes patterns like:
    - "Section 302 IPC" / "Sec 302 of IPC"
    - "BNS Section 63" / "BNSS 176"
    - "Art. 14" / "Article 21"
    - "Rule 3(2)(a)"
    """

    # Citation regex patterns
    CITATION_PATTERNS = [
        # "Section 302 of IPC" or "Section 302 IPC"
        re.compile(
            r"(?:Section|Sec\.?)\s*(\d+[A-Za-z]*(?:\(\d+\))?)\s*(?:of\s+)?(?:the\s+)?"
            r"(BNS|BNSS|BSA|IPC|CrPC|IEA|Indian Penal Code|Bharatiya Nyaya Sanhita|"
            r"Bharatiya Nagarik Suraksha Sanhita|Bharatiya Sakshya Adhiniyam)",
            re.IGNORECASE,
        ),
        # "BNS Section 63" or "IPC 302"
        re.compile(
            r"(BNS|BNSS|BSA|IPC|CrPC|IEA)\s*(?:Section|Sec\.?)?\s*(\d+[A-Za-z]*)",
            re.IGNORECASE,
        ),
        # "Article 21" or "Art. 14"
        re.compile(
            r"(?:Article|Art\.?)\s*(\d+[A-Za-z]*)",
            re.IGNORECASE,
        ),
        # Bare section in context: "under section 302"
        re.compile(
            r"(?:under|u/s|u\.s\.|as per)\s+(?:Section|Sec\.?)?\s*(\d+[A-Za-z]*)",
            re.IGNORECASE,
        ),
    ]

    # Act name normalization
    ACT_ALIASES = {
        "ipc": "Indian Penal Code",
        "indian penal code": "Indian Penal Code",
        "crpc": "Code of Criminal Procedure 1973",
        "iea": "Indian Evidence Act 1872",
        "bns": "Bharatiya Nyaya Sanhita",
        "bharatiya nyaya sanhita": "Bharatiya Nyaya Sanhita",
        "bnss": "Bharatiya Nagarik Suraksha Sanhita",
        "bharatiya nagarik suraksha sanhita": "Bharatiya Nagarik Suraksha Sanhita",
        "bsa": "Bharatiya Sakshya Adhiniyam",
        "bharatiya sakshya adhiniyam": "Bharatiya Sakshya Adhiniyam",
    }

    def __init__(self) -> None:
        pass

    async def search(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for cited legal sections.

        Args:
            query: The search query.
            top_k: Max results.

        Returns:
            List of result dicts.
        """
        start_time = time.monotonic()
        citations = self.extract_citations(query)

        if not citations:
            logger.info("No citations found in query")
            return []

        results: list[dict[str, Any]] = []

        try:
            from app.embeddings.qdrant_client import get_qdrant_manager
            from app.core.config import settings

            qdrant = get_qdrant_manager()

            for citation in citations[:5]:
                section_num = citation["section_number"]
                act = citation["act"]

                # Search for exact section in Qdrant
                filter_results = qdrant.search(
                    query_vector=[0.0] * settings.QDRANT_VECTOR_SIZE,  # Dummy vector for filtered search
                    top_k=5,
                    collection_name=settings.QDRANT_COLLECTION_SECTIONS,
                    filter_conditions={"section_number": section_num},
                )

                # If no results with filter, try broader
                if not filter_results:
                    filter_results = qdrant.search(
                        query_vector=[0.0] * settings.QDRANT_VECTOR_SIZE,
                        top_k=5,
                        collection_name=settings.QDRANT_COLLECTION_DOCS,
                    )

                for r in filter_results:
                    r["source"] = "citation"
                    r["citation"] = {
                        "section_number": section_num,
                        "act": act,
                        "matched_text": citation["matched_text"],
                    }
                    results.append(r)

        except Exception as exc:
            logger.warning(f"Citation retrieval via Qdrant failed: {exc}")
            # Fallback: return citation info as results
            for citation in citations[:top_k]:
                results.append({
                    "text": f"Citation: Section {citation['section_number']} of {citation['act']}",
                    "score": 1.0,
                    "source": "citation",
                    "metadata": {
                        "section_number": citation["section_number"],
                        "act": citation["act"],
                        "citation_type": "extracted",
                    },
                })

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"Citation search returned {len(results)} results in {duration_ms:.0f}ms")
        return results[:top_k]

    def extract_citations(self, query: str) -> list[dict[str, Any]]:
        """Extract all legal citations from a query string.

        Args:
            query: The query text.

        Returns:
            List of citation dicts with section_number, act, matched_text.
        """
        citations: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for pattern in self.CITATION_PATTERNS:
            for match in pattern.finditer(query):
                groups = match.groups()
                matched_text = match.group(0)

                # Determine section number and act based on pattern
                if "Section" in matched_text or "Sec." in matched_text:
                    section_num = groups[0]
                    act = groups[1] if len(groups) > 1 else ""
                elif any(a in matched_text.upper() for a in ["BNS", "BNSS", "BSA", "IPC", "CRPC", "IEA"]):
                    act = groups[0]
                    section_num = groups[1] if len(groups) > 1 else ""
                elif "Article" in matched_text or "Art." in matched_text:
                    section_num = groups[0]
                    act = "Constitution of India"
                else:
                    section_num = groups[0]
                    act = ""

                # Normalize act name
                act_normalized = self.ACT_ALIASES.get(act.lower(), act)

                key = (section_num, act_normalized)
                if key not in seen:
                    seen.add(key)
                    citations.append({
                        "section_number": section_num,
                        "act": act_normalized,
                        "matched_text": matched_text,
                    })

        return citations
