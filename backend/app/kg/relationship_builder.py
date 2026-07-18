"""Relationship builder for legal knowledge graph.

Automatically generates edges between entities extracted from
case documents, linking them to Sections, Precedents, and other
legal concepts in the Neo4j knowledge graph.
"""

from __future__ import annotations

from typing import Any

from loguru import logger


class RelationshipBuilder:
    """Build relationships between legal entities in the knowledge graph.

    Generates edges of types:
    - REFERENCES_SECTION: Case/Document -> Section
    - CITES_PRECEDENT: Case -> Precedent/Judgment
    - INVOLVES_PARTY: Case -> Party (Plaintiff/Defendant/etc.)
    - PRESENTS_EVIDENCE: Case -> Evidence Item
    - RELATES_TO_ISSUE: Case -> Legal Issue
    - SEEKS_RELIEF: Party -> Relief Type
    - CROSS_REFERENCES: Section <-> Section
    """

    # Relationship type constants
    REL_TYPES = {
        "references_section": "REFERENCES_SECTION",
        "cites_precedent": "CITES_PRECEDENT",
        "involves_party": "INVOLVES_PARTY",
        "presents_evidence": "PRESENTS_EVIDENCE",
        "relates_to_issue": "RELATES_TO_ISSUE",
        "seeks_relief": "SEEKS_RELIEF",
        "cross_references": "CROSS_REFERENCES",
        "has_contradiction": "HAS_CONTRADICTION",
        "has_timeline_event": "HAS_TIMELINE_EVENT",
        "appears_in_court": "APPEARS_IN_COURT",
    }

    def __init__(self) -> None:
        pass

    def build_from_entities(
        self,
        case_id: str,
        entities: dict[str, Any],
        sections: list[dict[str, Any]] | None = None,
        precedents: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Build relationship edges from extracted entities.

        Args:
            case_id: The case node identifier.
            entities: Entity extraction output from entity_extractor.
            sections: List of applicable section dicts.
            precedents: List of precedent/judgment dicts.

        Returns:
            List of edge dicts with source, target, type, properties.
        """
        edges: list[dict[str, Any]] = []

        # ── Party relationships ──
        parties = entities.get("parties", {})
        for role, party_name in parties.items():
            if party_name and isinstance(party_name, str):
                edges.append({
                    "source": case_id,
                    "target": f"party:{party_name}",
                    "type": self.REL_TYPES["involves_party"],
                    "properties": {"role": role},
                })

        for party_name in parties.get("others", []):
            edges.append({
                "source": case_id,
                "target": f"party:{party_name}",
                "type": self.REL_TYPES["involves_party"],
                "properties": {"role": "other"},
            })

        # ── Issue relationships ──
        for issue in entities.get("legal_issues", []):
            issue_id = f"issue:{hash(issue) % 100000}"
            edges.append({
                "source": case_id,
                "target": issue_id,
                "type": self.REL_TYPES["relates_to_issue"],
                "properties": {"issue_text": issue},
            })

        # ── Section references ──
        if sections:
            for section in sections:
                sec_id = f"{section.get('act', 'UNKNOWN')}_{section.get('section_number', '?')}"
                edges.append({
                    "source": case_id,
                    "target": sec_id,
                    "type": self.REL_TYPES["references_section"],
                    "properties": {
                        "relevance_score": section.get("relevance_score", 0.0),
                    },
                })

        # ── Precedent citations ──
        if precedents:
            for precedent in precedents:
                case_name = precedent.get("case_name", "Unknown")
                edges.append({
                    "source": case_id,
                    "target": f"precedent:{case_name}",
                    "type": self.REL_TYPES["cites_precedent"],
                    "properties": {
                        "citation": precedent.get("citation", ""),
                        "relevance_score": precedent.get("relevance_score", 0.0),
                    },
                })

        # ── Cross-references between sections (transitive closure) ──
        if sections and len(sections) > 1:
            for i, s1 in enumerate(sections):
                for s2 in sections[i + 1:]:
                    edges.append({
                        "source": f"{s1.get('act', '')}_{s1.get('section_number', '')}",
                        "target": f"{s2.get('act', '')}_{s2.get('section_number', '')}",
                        "type": self.REL_TYPES["cross_references"],
                        "properties": {"via_case": case_id},
                    })

        # ── Court relationships ──
        courts = entities.get("courts", [])
        for court in courts:
            edges.append({
                "source": case_id,
                "target": f"court:{court}",
                "type": self.REL_TYPES["appears_in_court"],
                "properties": {},
            })

        logger.info(f"Built {len(edges)} relationships for case {case_id}")
        return edges

    def build_timeline_edges(
        self,
        case_id: str,
        timeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build chronological edges between timeline events.

        Args:
            case_id: The case node identifier.
            timeline: List of timeline event dicts with 'date' and 'event'.

        Returns:
            List of edge dicts.
        """
        edges: list[dict[str, Any]] = []
        for i, event in enumerate(timeline):
            event_id = f"event:{case_id}:{i}"
            edges.append({
                "source": case_id,
                "target": event_id,
                "type": self.REL_TYPES["has_timeline_event"],
                "properties": {
                    "date": event.get("date", ""),
                    "event": event.get("event", ""),
                    "sequence": i,
                },
            })

        return edges

    def build_contradiction_edges(
        self,
        case_id: str,
        contradictions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build edges representing detected contradictions.

        Args:
            case_id: The case node identifier.
            contradictions: List of contradiction dicts.

        Returns:
            List of edge dicts.
        """
        edges: list[dict[str, Any]] = []
        for i, contradiction in enumerate(contradictions):
            cont_id = f"contradiction:{case_id}:{i}"
            edges.append({
                "source": case_id,
                "target": cont_id,
                "type": self.REL_TYPES["has_contradiction"],
                "properties": {
                    "severity": contradiction.get("severity", "unknown"),
                    "confidence": contradiction.get("confidence", 0.0),
                    "type": contradiction.get("type", ""),
                },
            })

        return edges

    def to_cypher(
        self,
        edges: list[dict[str, Any]],
    ) -> list[str]:
        """Convert relationship edges to Cypher MERGE statements.

        Args:
            edges: List of edge dicts.

        Returns:
            List of Cypher query strings.
        """
        queries: list[str] = []
        for edge in edges:
            props = ", ".join(
                f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}"
                for k, v in edge.get("properties", {}).items()
            )
            query = (
                f"MERGE (a {{id: '{edge['source']}'}}) "
                f"MERGE (b {{id: '{edge['target']}'}}) "
                f"MERGE (a)-[:{edge['type']} {{{props}}}]->(b)"
            )
            queries.append(query)

        return queries
