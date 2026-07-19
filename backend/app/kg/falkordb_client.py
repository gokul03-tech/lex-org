"""Async FalkorDB client for the LexOrch-KG knowledge graph.

Provides connection pooling, Cypher query execution, and graph operations
for legal entity storage, relationship management, and graph traversals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger
from falkordb.asyncio import FalkorDB
from redis.asyncio import BlockingConnectionPool
from falkordb.node import Node
from falkordb.edge import Edge

from app.core.config import settings


def _convert_value(val: Any) -> Any:
    """Helper to convert FalkorDB objects (Nodes/Edges) into dictionaries."""
    if isinstance(val, Node):
        res = dict(val.properties)
        res["_labels"] = val.labels
        res["_id"] = val.id
        return res
    elif isinstance(val, Edge):
        res = dict(val.properties)
        res["_relation"] = val.relation
        res["_id"] = val.id
        res["_src_node"] = val.src_node
        res["_dest_node"] = val.dest_node
        return res
    elif isinstance(val, list):
        return [_convert_value(v) for v in val]
    elif isinstance(val, dict):
        return {k: _convert_value(v) for k, v in val.items()}
    else:
        return val


class FalkorDBClient:
    """Async FalkorDB client wrapper with connection pooling and query helpers."""

    def __init__(self) -> None:
        self._pool = BlockingConnectionPool(
            host=settings.FALKORDB_HOST,
            port=settings.FALKORDB_PORT,
            password=settings.FALKORDB_PASSWORD or None,
            max_connections=20,
            decode_responses=True,
        )
        self._db = FalkorDB(connection_pool=self._pool)
        self._graph = self._db.select_graph(settings.FALKORDB_GRAPH_NAME)

    async def close(self) -> None:
        """Close the FalkorDB connection pool."""
        await self._pool.aclose()

    async def verify_connectivity(self) -> bool:
        """Check if FalkorDB is reachable by running a simple query."""
        try:
            await self._graph.query("RETURN 1")
            logger.info("FalkorDB connection verified")
            return True
        except Exception as exc:
            logger.error(f"FalkorDB connection failed: {exc}")
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
        res = await self._graph.query(query, params=parameters)
        header_names = [h[1] for h in res.header] if res.header else []
        if not header_names:
            return []
        
        results = []
        for row in res.result_set:
            record = {}
            for name, val in zip(header_names, row):
                record[name] = _convert_value(val)
            results.append(record)
        return results

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
        return await self.run_query(query, parameters)

    async def create_constraints(self) -> None:
        """Create FalkorDB range indexes and unique constraints."""
        # 1. Range indexes (must exist before unique constraints in FalkorDB)
        indexes = [
            ("Section", "section_id"),
            ("Act", "name"),
            ("LegalPrinciple", "principle_id"),
            ("Case", "case_id"),
            ("Court", "name"),
            ("Entity", "entity_type"),
            ("Section", "act"),
            ("Section", "section_number"),
            ("Case", "court_name"),
        ]
        
        for label, prop in indexes:
            try:
                await self._graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
                logger.info(f"Created range index for {label}({prop})")
            except Exception as exc:
                logger.warning(f"Index creation note for {label}({prop}): {exc}")

        # Composite index on Entity
        try:
            await self._graph.query("CREATE INDEX FOR (n:Entity) ON (n.entity_type, n.name)")
            logger.info("Created composite index for Entity(entity_type, name)")
        except Exception as exc:
            logger.warning(f"Composite index creation note: {exc}")

        # 2. Unique constraints
        unique_props = [
            ("Section", "section_id"),
            ("Act", "name"),
            ("LegalPrinciple", "principle_id"),
            ("Case", "case_id"),
            ("Court", "name"),
        ]
        for label, prop in unique_props:
            try:
                # Execute constraint command directly via GRAPH.CONSTRAINT CREATE
                await self._graph.client.execute_command(
                    "GRAPH.CONSTRAINT", "CREATE", self._graph.name, "UNIQUE", "NODE", label, "PROPERTIES", "1", prop
                )
                logger.info(f"Created unique constraint for {label}({prop})")
            except Exception as exc:
                logger.warning(f"Unique constraint creation note for {label}({prop}): {exc}")

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

                if isinstance(edges_data, dict):
                    edges_list = edges_data.get("edges", [])
                elif isinstance(edges_data, list):
                    edges_list = edges_data
                else:
                    edges_list = []

                for edge in edges_list:
                    source_id = edge.get("source", edge.get("source_id", ""))
                    target_id = edge.get("target", edge.get("target_id", ""))
                    rel_type = edge.get("relationship", edge.get("edge_type", "RELATES_TO"))
                    properties = edge.get("properties", edge.get("metadata", {}))

                    # Sanitize relationship type
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
_falkordb_client: FalkorDBClient | None = None


async def get_falkordb_client() -> FalkorDBClient:
    """Get or create the global FalkorDB client singleton."""
    global _falkordb_client
    if _falkordb_client is None:
        _falkordb_client = FalkorDBClient()
        if not await _falkordb_client.verify_connectivity():
            logger.warning("FalkorDB is not available. KG features will be disabled.")
    return _falkordb_client
