"""Async Neo4j client for the LexOrch-KG knowledge graph.

Provides connection pooling, Cypher query execution, and graph operations
for legal entity storage, relationship management, and graph traversals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger
from neo4j import AsyncGraphDatabase, AsyncManagedTransaction

from app.core.config import settings


class Neo4jClient:
    """Async Neo4j driver wrapper with connection pooling and query helpers."""

    def __init__(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=20,
            connection_acquisition_timeout=30,
        )
        self._database = settings.NEO4J_DATABASE

    async def close(self) -> None:
        """Close the Neo4j driver connection pool."""
        await self._driver.close()

    async def verify_connectivity(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            await self._driver.verify_connectivity()
            logger.info("Neo4j connection verified")
            return True
        except Exception as exc:
            logger.error(f"Neo4j connection failed: {exc}")
            return False

    async def run_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher read query and return results as dicts.

        Args:
            query: Cypher query string.
            parameters: Query parameters.

        Returns:
            List of result records as dictionaries.
        """
        records, _, _ = await self._driver.execute_query(
            query,
            parameters or {},
            database_=self._database,
        )
        return [dict(record) for record in records]

    async def run_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher write query (create/update/delete).

        Args:
            query: Cypher query string.
            parameters: Query parameters.

        Returns:
            List of result records as dictionaries.
        """
        records, _, _ = await self._driver.execute_query(
            query,
            parameters or {},
            database_=self._database,
        )
        return [dict(record) for record in records]

    async def create_constraints(self) -> None:
        """Create Neo4j uniqueness constraints and indexes for all node types."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Section) REQUIRE n.section_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Act) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:LegalPrinciple) REQUIRE n.principle_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Case) REQUIRE n.case_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Court) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE (n.entity_type, n.name) IS NODE KEY",
        ]

        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Section) ON (n.act)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Section) ON (n.section_number)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Case) ON (n.court_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.entity_type)",
        ]

        for cypher in constraints + indexes:
            try:
                await self.run_write(cypher)
            except Exception as exc:
                logger.warning(f"Constraint/index creation note: {exc}")

    async def seed_from_govintel(self, datasets_dir: Path | None = None) -> dict[str, int]:
        """Seed the knowledge graph from GovIntel section and edge JSON files.

        Args:
            datasets_dir: Path to the datasets directory. Defaults to settings value.

        Returns:
            Dict with counts of created nodes and relationships.
        """
        base = datasets_dir or settings.LEGAL_CORPUS_DIR
        govintel_dir = base / "GovIntel"
        sections_dir = govintel_dir / "sections"
        graph_dir = govintel_dir / "graph"

        stats = {"sections": 0, "edges": 0, "errors": 0}

        if not sections_dir.exists():
            logger.warning(f"GovIntel sections directory not found: {sections_dir}")
            return stats

        # Import sections
        section_files = [
            ("bns_sections.json", "BNS 2023"),
            ("bnss_sections.json", "BNSS 2023"),
            ("bsa_sections.json", "BSA 2023"),
            ("ipc_sections.json", "IPC 1860"),
        ]

        for filename, act_name in section_files:
            filepath = sections_dir / filename
            if not filepath.exists():
                continue

            try:
                with open(filepath) as f:
                    sections_data = json.load(f)

                for section in sections_data:
                    section_id = section.get("section_id", "")
                    section_num = section.get("section_number", "")
                    title = section.get("section_title", section.get("title", ""))
                    text = section.get("section_text", section.get("text", ""))

                    await self.run_write(
                        """
                        MERGE (s:Section {section_id: $section_id})
                        SET s.section_number = $section_num,
                            s.title = $title,
                            s.text = $text,
                            s.act = $act
                        MERGE (a:Act {name: $act})
                        MERGE (s)-[:BELONGS_TO]->(a)
                        """,
                        {
                            "section_id": section_id,
                            "section_num": str(section_num),
                            "title": title,
                            "text": text[:5000],
                            "act": act_name,
                        },
                    )
                    stats["sections"] += 1

            except Exception as exc:
                logger.error(f"Failed to import {filename}: {exc}")
                stats["errors"] += 1

        # Import edges
        edge_files = [
            "deterministic_edges.json",
            "cross_code_edges.json",
            "judgment_edges.json",
            "autonomous_edges.json",
            "all_edges.json",
        ]

        for filename in edge_files:
            filepath = graph_dir / filename
            if not filepath.exists():
                continue

            try:
                with open(filepath) as f:
                    edges_data = json.load(f)

                for edge in edges_data:
                    source_id = edge.get("source", edge.get("source_id", ""))
                    target_id = edge.get("target", edge.get("target_id", ""))
                    rel_type = edge.get("relationship", edge.get("edge_type", "RELATES_TO"))
                    properties = edge.get("properties", edge.get("metadata", {}))

                    # Sanitize relationship type (replace spaces/slashes with underscores)
                    rel_type = rel_type.replace(" ", "_").replace("/", "_").upper()

                    await self.run_write(
                        f"""
                        MATCH (s:Section {{section_id: $source_id}})
                        MATCH (t:Section {{section_id: $target_id}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        SET r += $properties
                        """,
                        {
                            "source_id": source_id,
                            "target_id": target_id,
                            "properties": properties or {},
                        },
                    )
                    stats["edges"] += 1

            except Exception as exc:
                logger.error(f"Failed to import edges from {filename}: {exc}")
                stats["errors"] += 1

        logger.info(f"KG seeding complete: {stats['sections']} sections, {stats['edges']} edges")
        return stats

    async def get_case_graph(self, case_id: str) -> dict[str, Any]:
        """Retrieve the full knowledge graph for a specific case.

        Args:
            case_id: The database case ID.

        Returns:
            Dict with 'nodes' and 'edges' lists for visualization.
        """
        result = await self.run_query(
            """
            MATCH (c:Case {case_id: $case_id})
            OPTIONAL MATCH (c)-[r]-(n)
            RETURN c, collect(DISTINCT {type: type(r), props: properties(r), target: n}) AS relationships
            """,
            {"case_id": case_id},
        )
        return result[0] if result else {"nodes": [], "edges": []}


# Global singleton
_neo4j_client: Neo4jClient | None = None


async def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        if not await _neo4j_client.verify_connectivity():
            logger.warning("Neo4j is not available. KG features will be disabled.")
    return _neo4j_client
