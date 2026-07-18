"""GovIntel seed data importer for Neo4j knowledge graph.

Imports section nodes and edge relationships from the GovIntel dataset
into Neo4j. Handles BNS, BNSS, BSA, and IPC sections plus all four
edge types (deterministic, cross_code, judgment, autonomous).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class GovIntelSeedImporter:
    """Import GovIntel KG seed data into Neo4j.

    Reads section JSONs and edge JSONs from the GovIntel dataset directory
    and generates Cypher queries for Neo4j population.
    """

    SECTION_FILES = {
        "bns": "bns_sections.json",
        "bnss": "bnss_sections.json",
        "bsa": "bsa_sections.json",
        "ipc": "ipc_sections.json",
    }

    EDGE_FILES = {
        "deterministic": "deterministic_edges.json",
        "cross_code": "cross_code_edges.json",
        "judgment": "judgment_edges.json",
        "autonomous": "autonomous_edges.json",
    }

    def __init__(self, data_dir: str | Path | None = None) -> None:
        """Initialize the seed importer.

        Args:
            data_dir: Path to GovIntel directory. Defaults to settings.
        """
        if data_dir is None:
            data_dir = settings.PROJECT_ROOT / settings.LEGAL_CORPUS_DIR / "GovIntel"
        self.data_dir = Path(data_dir)
        self.sections_dir = self.data_dir / "sections"
        self.graph_dir = self.data_dir / "graph"

    def load_sections(self, code: str) -> list[dict[str, Any]]:
        """Load section JSON for a given legal code.

        Args:
            code: One of 'bns', 'bnss', 'bsa', 'ipc'.

        Returns:
            List of section dicts.
        """
        filename = self.SECTION_FILES.get(code)
        if not filename:
            raise ValueError(f"Unknown code: {code}. Use: {list(self.SECTION_FILES)}")

        filepath = self.sections_dir / filename
        if not filepath.exists():
            logger.warning(f"Section file not found: {filepath}")
            return []

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"Loaded {len(data)} sections from {filename}")
        return data

    def load_all_sections(self) -> dict[str, list[dict[str, Any]]]:
        """Load all section files.

        Returns:
            Dict mapping code name to list of section dicts.
        """
        result: dict[str, list[dict[str, Any]]] = {}
        for code in self.SECTION_FILES:
            sections = self.load_sections(code)
            if sections:
                result[code] = sections
        return result

    def load_edges(self, edge_type: str) -> list[dict[str, Any]]:
        """Load edge JSON for a given edge type.

        Args:
            edge_type: One of 'deterministic', 'cross_code', 'judgment', 'autonomous'.

        Returns:
            List of edge dicts.
        """
        filename = self.EDGE_FILES.get(edge_type)
        if not filename:
            raise ValueError(f"Unknown edge type: {edge_type}")

        filepath = self.graph_dir / filename
        if not filepath.exists():
            logger.warning(f"Edge file not found: {filepath}")
            return []

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # Handle wrapped format (e.g., {"metadata": {...}, "edges": [...]})
        if isinstance(data, dict) and "edges" in data:
            edges = data["edges"]
            metadata = data.get("metadata", {})
            logger.info(f"Loaded {len(edges)} {edge_type} edges (metadata: {metadata})")
            return edges

        logger.info(f"Loaded {len(data)} {edge_type} edges from {filename}")
        return data

    def load_all_edges(self) -> dict[str, list[dict[str, Any]]]:
        """Load all edge types.

        Returns:
            Dict mapping edge type to list of edge dicts.
        """
        result: dict[str, list[dict[str, Any]]] = {}
        for edge_type in self.EDGE_FILES:
            edges = self.load_edges(edge_type)
            if edges:
                result[edge_type] = edges
        return result

    def generate_section_cypher(self, sections: list[dict[str, Any]]) -> list[str]:
        """Generate Cypher CREATE/MERGE statements for section nodes.

        Args:
            sections: List of section dicts from GovIntel.

        Returns:
            List of Cypher query strings.
        """
        queries: list[str] = []

        for section in sections:
            section_id = section.get("section_id", "")
            act = section.get("act", "")
            year = section.get("year", "")
            chapter = section.get("chapter_title", "")
            section_num = section.get("section_number", "")
            title = section.get("section_title", "")
            text = section.get("section_text", "")

            # Escape single quotes in text
            safe_text = text.replace("'", "\\'").replace('"', '\\"')[:500]
            safe_title = title.replace("'", "\\'")

            query = (
                f"MERGE (s:Section {{section_id: '{section_id}'}}) "
                f"SET s.act = '{act}', "
                f"s.year = {year}, "
                f"s.chapter = '{chapter}', "
                f"s.section_number = '{section_num}', "
                f"s.title = '{safe_title}', "
                f"s.text = '{safe_text}'"
            )
            queries.append(query)

        logger.info(f"Generated {len(queries)} section Cypher statements")
        return queries

    def generate_edge_cypher(self, edges: list[dict[str, Any]], edge_category: str) -> list[str]:
        """Generate Cypher statements for edge relationships.

        Args:
            edges: List of edge dicts.
            edge_category: Category label for the edge type.

        Returns:
            List of Cypher query strings.
        """
        queries: list[str] = []

        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            edge_type = edge.get("edge_type", "RELATED_TO")
            deterministic = edge.get("deterministic", False)
            direction = edge.get("direction", "")
            reason = edge.get("reason", "")
            confidence = edge.get("confidence", "medium")

            safe_reason = reason.replace("'", "\\'") if reason else ""

            query = (
                f"MATCH (a:Section {{section_id: '{source}'}}) "
                f"MATCH (b:Section {{section_id: '{target}'}}) "
                f"MERGE (a)-[r:{edge_type}]->(b) "
                f"SET r.deterministic = {str(deterministic).lower()}, "
                f"r.direction = '{direction}', "
                f"r.category = '{edge_category}', "
                f"r.confidence = '{confidence}', "
                f"r.reason = '{safe_reason}'"
            )
            queries.append(query)

        logger.info(f"Generated {len(queries)} edge Cypher statements for {edge_category}")
        return queries

    def get_all_cypher(self) -> dict[str, list[str]]:
        """Get all Cypher statements for the complete seed import.

        Returns:
            Dict with 'sections' and edge-type keys mapping to Cypher lists.
        """
        all_cypher: dict[str, list[str]] = {}

        # Sections
        all_sections: list[dict[str, Any]] = []
        for code_data in self.load_all_sections().values():
            all_sections.extend(code_data)
        all_cypher["sections"] = self.generate_section_cypher(all_sections)

        # Edges
        all_edges = self.load_all_edges()
        for edge_type, edges in all_edges.items():
            all_cypher[f"edges_{edge_type}"] = self.generate_edge_cypher(edges, edge_type)

        total = sum(len(v) for v in all_cypher.values())
        logger.info(f"Total Cypher statements: {total}")
        return all_cypher
