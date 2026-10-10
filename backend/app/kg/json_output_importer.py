"""JSON Output Importer for FalkorDB Knowledge Graph.
Imports all processed legal data from json_output into FalkorDB.
"""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from app.core.config import settings
from app.kg.falkordb_client import FalkorDBClient, get_falkordb_client


class JSONOutputImporter:
    """Imports json_output data into FalkorDB knowledge graph."""

    def __init__(self, json_output_root: Path | None = None):
        """Initialize importer.
        
        Args:
            json_output_root: Path to json_output directory. 
                            Defaults to project root/json_output.
        """
        self.json_output_root = json_output_root or (
            settings.PROJECT_ROOT / "json_output"
        )
        self.logger = logger

    def _load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load a JSONL file (one JSON object per line).
        
        Args:
            file_path: Path to the JSONL file
            
        Returns:
            List of parsed JSON objects
        """
        objects = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        objects.append(obj)
                    except json.JSONDecodeError as exc:
                        self.logger.warning(
                            f"Failed to parse line {line_num} in {file_path}: {exc}"
                        )
                        continue
        except Exception as exc:
            self.logger.error(f"Failed to read file {file_path}: {exc}")
        return objects

    def _safe_get_metadata(self, obj: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get a value from metadata dict.
        
        Args:
            obj: The JSON object
            key: The key to look for in metadata
            default: Default value if not found
            
        Returns:
            The value or default
        """
        metadata = obj.get("metadata", {})
        if isinstance(metadata, dict):
            val = metadata.get(key)
            return default if val is None else val
        return default

    async def import_all(self) -> Dict[str, Dict[str, int]]:
        """Import all json_output data into FalkorDB."""
        self.logger.info("Starting import of ALL json_output data into FalkorDB...")
        
        # Get FalkorDB client
        falkordb = await get_falkordb_client()
        
        results = {
            "acts_and_constitution": await self.import_acts_and_constitution(falkordb),
            "court_judgments": await self.import_court_judgments(falkordb),
            "legal_qa_pairs": await self.import_legal_qa_pairs(falkordb),
        }
        
        self.logger.info("JSON output import completed.")
        return results

    async def import_acts_and_constitution(self, falkordb: FalkorDBClient) -> Dict[str, int]:
        """Import legal acts and constitution as Section nodes.
        
        Scans: json_output/acts/*, json_output/constitution/*/
        Each JSON file contains JSONL format (one JSON object per line).
        """
        stats = {"sections": 0, "acts": 0, "errors": 0}
        
        # Define paths to scan for legal sections/documents
        section_paths = [
            self.json_output_root / "acts",
            self.json_output_root / "constitution"
        ]
        
        for base_path in section_paths:
            if not base_path.exists():
                self.logger.warning(f"Path does not exist: {base_path}")
                continue
                
            # Walk through document directories (e.g., acts/Aadhaar Act, 2019/)
            for doc_dir in base_path.iterdir():
                if not doc_dir.is_dir():
                    continue
                    
                doc_name = doc_dir.name  # e.g., "Aadhaar Act, 2019"
                data_file = doc_dir / "data.json"
                
                if not data_file.exists():
                    continue
                    
                try:
                    # Load JSONL file
                    documents_data = self._load_jsonl_file(data_file)
                    
                    # Each item in data.json represents a page/chunk of the document
                    for idx, doc_obj in enumerate(documents_data):
                        # Generate a unique section ID
                        section_id = f"json_{doc_name.replace(' ', '_').replace(',', '')}_page_{self._safe_get_metadata(doc_obj, 'page_number', idx)}"
                        
                        # Extract properties
                        metadata = doc_obj.get("metadata", {})
                        text = doc_obj.get("text", "")[:10000]  # Reasonable limit for text
                        page_number = self._safe_get_metadata(doc_obj, "page_number", 0)
                        
                        # Determine act name from metadata or directory name
                        act_name = self._safe_get_metadata(doc_obj, "act_name") or doc_name
                        if not act_name or act_name == "null":
                            act_name = doc_name
                        
                        # Create Section node
                        await falkordb.run_write(
                            """
                            MERGE (s:Section {section_id: $section_id})
                            SET s.act = $act_name,
                                s.section_number = $section_number,
                                s.title = $title,
                                s.text = $text,
                                s.page_number = $page_number,
                                s.source_type = $source_type,
                                s.document_type = $document_type
                            """,
                            {
                                "section_id": section_id,
                                "act_name": act_name,
                                "section_number": str(page_number) if page_number else str(idx),
                                "title": f"{act_name} - Page {page_number}" if page_number else f"{act_name} - Section {idx}",
                                "text": text,
                                "page_number": page_number,
                                "source_type": doc_obj.get("source_type", "unknown"),
                                "document_type": doc_obj.get("document_type", "act")
                            }
                        )
                        stats["sections"] += 1
                    
                    # Also create/update the Act node
                    await falkordb.run_write(
                        """
                        MERGE (a:Act {name: $act_name})
                        """,
                        {"act_name": act_name}
                    )
                    stats["acts"] += 1
                    
                except Exception as exc:
                    self.logger.error(f"Failed to import {data_file}: {exc}")
                    stats["errors"] += 1
        
        self.logger.info(f"Imported acts/constitution: {stats['sections']} sections, {stats['acts']} acts, {stats['errors']} errors")
        return stats

    async def import_court_judgments(self, falkordb: FalkorDBClient) -> Dict[str, int]:
        """Import court judgments as Case nodes.
        
        Scans: json_output/legal_corpus/Supreme_Court/*, json_output/legal_corpus/highcourt/*
        Each JSON file contains a single judgment object (JSONL format with one object).
        """
        stats = {"cases": 0, "errors": 0}
        
        judgment_paths = [
            self.json_output_root / "legal_corpus" / "Supreme_Court",
            self.json_output_root / "legal_corpus" / "highcourt"
        ]
        
        for base_path in judgment_paths:
            if not base_path.exists():
                self.logger.warning(f"Path does not exist: {base_path}")
                continue
                
            # Each subdirectory is a case (e.g., Supreme_Court/1001315/)
            for case_dir in base_path.iterdir():
                if not case_dir.is_dir():
                    continue
                    
                case_id = case_dir.name  # e.g., "1001315"
                data_file = case_dir / "data.json"
                
                if not data_file.exists():
                    continue
                    
                try:
                    # Load JSONL file (should contain exactly one object)
                    judgment_list = self._load_jsonl_file(data_file)
                    if not judgment_list:
                        continue
                    judgment_data = judgment_list[0]  # Take the first object
                    
                    # Extract judgment metadata
                    metadata = judgment_data.get("metadata", {})
                    case_name = metadata.get("filename", f"Case {case_id}")
                    court_name = metadata.get("court", "Unknown Court")
                    year_str = metadata.get("year", "")
                    
                    # Try to extract year from year_str or text
                    year = None
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                    else:
                        # Try to extract year from text
                        import re
                        text = judgment_data.get("text", "")
                        year_match = re.search(r'\b(19|20)\d{2}\b', text)
                        if year_match:
                            year = int(year_match.group())
                    
                    # Create Case node
                    case_node_id = f"case_{case_id}"
                    await falkordb.run_write(
                        """
                        MERGE (c:Case {case_id: $case_id})
                        SET c.case_name = $case_name,
                            c.court_name = $court_name,
                            c.year = $year,
                            c.text = $text,
                            c.source_type = $source_type,
                            c.document_type = $document_type
                        """,
                        {
                            "case_id": case_node_id,
                            "case_name": case_name,
                            "court_name": court_name,
                            "year": year,
                            "text": judgment_data.get("text", "")[:10000],  # Limit text size
                            "source_type": judgment_data.get("source_type", "unknown"),
                            "document_type": judgment_data.get("document_type", "judgment")
                        }
                    )
                    stats["cases"] += 1
                    
                except Exception as exc:
                    self.logger.error(f"Failed to import {data_file}: {exc}")
                    stats["errors"] += 1
        
        self.logger.info(f"Imported court judgments: {stats['cases']} cases, {stats['errors']} errors")
        return stats

    async def import_legal_qa_pairs(self, falkordb: FalkorDBClient) -> Dict[str, int]:
        """Import QA pairs as LegalPrinciple nodes.
        
        Scans: json_output/legal_corpus/BNS_BNSS_BSA/*/data.json
        Each JSON file contains JSONL format (one JSON object per line).
        """
        stats = {"principles": 0, "errors": 0}
        
        qa_base_path = self.json_output_root / "legal_corpus" / "BNS_BNSS_BSA"
        if not qa_base_path.exists():
            self.logger.warning(f"QA base path does not exist: {qa_base_path}")
            return stats
            
        # Process each QA category directory
        for category_dir in qa_base_path.iterdir():
            if not category_dir.is_dir():
                continue
                
            # Skip non-QA directories like assets, README, etc.
            category_name = category_dir.name
            if category_name in ["assets", "README"]:
                continue
                
            # Only process known QA directories
            if category_name not in ["bns_legal_qa", "bnss_legal_qa", "bsa_legal_qa", "bns_bnss_bsa_combined_legal_qa"]:
                continue
                
            data_file = category_dir / "data.json"
            if not data_file.exists():
                continue
                
            try:
                # Load JSONL file
                qa_data_list = self._load_jsonl_file(data_file)
                
                for qa_obj in qa_data_list:
                    principle_id = f"principle_{qa_obj.get('id', 'unknown')}"
                    
                    # Extract QA content
                    text = qa_obj.get("text", "")
                    metadata = qa_obj.get("metadata", {})
                    
                    # Safely extract metadata values, handling explicit nulls
                    act_name = self._safe_get_metadata(qa_obj, "act_name", "")
                    section_number = self._safe_get_metadata(qa_obj, "section_number", "")
                    qa_type = self._safe_get_metadata(qa_obj, "qa_type", "")
                    
                    # Handle source_type and document_type from the main object (not metadata)
                    # with explicit null checking
                    source_type_val = qa_obj.get('source_type')
                    if source_type_val is None:
                        source_type_val = 'unknown'
                    
                    document_type_val = qa_obj.get('document_type')
                    if document_type_val is None:
                        document_type_val = 'qa_pair'
                    
                    # Create LegalPrinciple node
                    await falkordb.run_write(
                        """
                        MERGE (lp:LegalPrinciple {principle_id: $principle_id})
                        SET lp.text = $text,
                            lp.act = $act_name,
                            lp.section_number = $section_number,
                            lp.qa_type = $qa_type,
                            lp.source_type = $source_type,
                            lp.document_type = $document_type
                        """,
                        {
                            "principle_id": principle_id,
                            "text": text[:5000],  # Limit size
                            "act_name": act_name,
                            "section_number": section_number,
                            "qa_type": qa_type,
                            "source_type": source_type_val,
                            "document_type": document_type_val
                        }
                    )
                    stats["principles"] += 1
                        
            except Exception as exc:
                self.logger.error(f"Failed to import {data_file}: {exc}")
                stats["errors"] += 1
        
        self.logger.info(f"Imported legal QA pairs: {stats['principles']} principles, {stats['errors']} errors")
        return stats


# Usage example:
if __name__ == "__main__":
    import json
    import asyncio
    importer = JSONOutputImporter()
    result = asyncio.run(importer.import_all())
    print(json.dumps(result, indent=2))
