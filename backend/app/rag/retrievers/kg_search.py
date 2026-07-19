"""Knowledge Graph retriever using FalkorDB.

Performs Cypher-based traversals for related sections,
precedents, cross-references, and entity connections.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger


class KnowledgeGraphRetriever:
    """FalkorDB knowledge graph search for legal retrieval.

    Leverages the pre-built knowledge graph of sections,
    precedents, and cross-references to find legally
    related content that vector search might miss.
    """

    def __init__(self) -> None:
        pass

    async def search(
        self,
        query: str,
        top_k: int = 20,
        section_numbers: list[str] | None = None,
        act_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the knowledge graph for related legal content.

        Args:
            query: The search query.
            top_k: Max results to return.
            section_numbers: Optional list of known section numbers to expand from.
            act_filter: Optional act name filter (e.g., "BNS 2023").

        Returns:
            List of result dicts with text, score, and metadata.
        """
        start_time = time.monotonic()
        results: list[dict[str, Any]] = []

        try:
            from app.kg.falkordb_client import get_falkordb_client
            from app.kg.queries.legal_queries import get_query

            falkordb = await get_falkordb_client()
            connected = await falkordb.verify_connectivity()

            if not connected:
                logger.warning("FalkorDB unavailable for KG search")
                return []

            # If we have section numbers, do direct expansion
            if section_numbers:
                results.extend(await self._search_by_sections(falkordb, section_numbers, act_filter))
            else:
                # Text search on sections
                results.extend(await self._search_by_text(falkordb, query, top_k))

            # Add KG source annotation and scores
            for i, r in enumerate(results):
                r["source"] = "kg"
                # Score decays with position
                r["score"] = 0.9 - (i * 0.02)

            duration_ms = (time.monotonic() - start_time) * 1000
            logger.info(f"KG search returned {len(results)} results in {duration_ms:.0f}ms")
            return results[:top_k]

        except Exception as exc:
            logger.error(f"KG search failed: {exc}")
            return []

    async def _search_by_sections(
        self,
        falkordb,
        section_numbers: list[str],
        act_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Expand from known section numbers to find related sections."""
        results: list[dict[str, Any]] = []

        for section_num in section_numbers[:5]:  # Limit to 5 to avoid fan-out
            # Get the section
            section_records = await falkordb.run_query(
                """
                MATCH (s:Section)
                WHERE toString(s.section_number) CONTAINS $num
                """ + (" AND s.act CONTAINS $act" if act_filter else "") + """
                RETURN s.section_id AS id, s.title AS title, s.text AS text,
                       s.act AS act, s.section_number AS section_number,
                       s.chapter AS chapter
                LIMIT 3
                """,
                {"num": str(section_num).strip(), "act": act_filter or ""},
            )

            for record in section_records:
                section_id = record.get("id", "")
                results.append({
                    "text": f"Section {record.get('section_number', '')}: {record.get('title', '')}\n{record.get('text', '')[:300]}",
                    "metadata": {
                        "section_number": record.get("section_number"),
                        "act": record.get("act"),
                        "chapter": record.get("chapter"),
                        "section_id": section_id,
                    },
                })

                # Get related sections
                if section_id:
                    related = await falkordb.run_query(
                        """
                        MATCH (s:Section {section_id: $sid})-[r]-(related:Section)
                        RETURN related.section_id AS id, related.title AS title,
                               related.act AS act, related.section_number AS number,
                               type(r) AS relationship, r.reason AS reason
                        LIMIT 5
                        """,
                        {"sid": section_id},
                    )
                    for rel in related:
                        results.append({
                            "text": f"Related: Section {rel.get('number', '')} ({rel.get('act', '')}): {rel.get('title', '')}\nRelationship: {rel.get('relationship', '')}",
                            "metadata": {
                                "section_number": rel.get("number"),
                                "act": rel.get("act"),
                                "relationship_type": rel.get("relationship"),
                                "reason": rel.get("reason", ""),
                            },
                        })

        return results

    async def _search_by_text(
        self,
        falkordb,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Full-text search on section text."""
        # Extract potential section numbers from query
        import re
        section_matches = re.findall(r"(?:section|sec\.?)\s*(\d+[A-Za-z]*)", query, re.IGNORECASE)

        results: list[dict[str, Any]] = []

        if section_matches:
            return await self._search_by_sections(falkordb, section_matches)

        # Try full-text search on title
        records = await falkordb.run_query(
            """
            MATCH (s:Section)
            WHERE s.title CONTAINS $text OR s.text CONTAINS $text
            RETURN s.section_id AS id, s.section_number AS section_number,
                   s.title AS title, s.act AS act, s.text AS text,
                   s.chapter AS chapter
            LIMIT $limit
            """,
            {"text": query[:100], "limit": top_k},
        )

        for record in records:
            results.append({
                "text": f"Section {record.get('section_number', '')}: {record.get('title', '')}\n{record.get('text', '')[:500]}",
                "metadata": {
                    "section_number": record.get("section_number"),
                    "act": record.get("act"),
                    "chapter": record.get("chapter"),
                },
            })

        return results
