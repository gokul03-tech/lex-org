"""Synthetic test case generator for evaluation.

Generates test cases with known ground truth for:
- Contradiction detection evaluation
- Section matching evaluation
- Evidence reliability scoring
- Temporal routing (IPC vs BNS)
"""

from __future__ import annotations

import json
import random
from typing import Any

from loguru import logger


class TestSuiteGenerator:
    """Generate synthetic test cases for controlled evaluation.

    Creates test cases with known properties so evaluation
    metrics can be computed against definitive ground truth.
    """

    # Template legal texts for synthetic case generation
    CASE_TEMPLATES = {
        "theft_case": {
            "title": "State vs. Accused - Theft Case",
            "description": "Allegation of theft under BNS Section 303 (previously IPC 378)",
            "sections": [
                {"section_number": "303", "act": "Bharatiya Nyaya Sanhita"},
                {"section_number": "378", "act": "Indian Penal Code"},
            ],
            "contradictions": [
                {
                    "type": "timeline",
                    "statement_a": "The accused was at the location at 3:00 PM",
                    "statement_b": "CCTV shows the accused left at 2:45 PM",
                    "severity": "high",
                },
            ],
            "evidence_items": [
                {"type": "CCTV footage", "reliability": 0.9},
                {"type": "Witness testimony", "reliability": 0.7},
            ],
            "temporal": "post_july_2024",
            "expected_act": "BNS",
        },
        "assault_case": {
            "title": "Victim vs. Accused - Assault Case",
            "description": "Allegation of assault causing grievous hurt",
            "sections": [
                {"section_number": "115", "act": "Bharatiya Nyaya Sanhita"},
                {"section_number": "320", "act": "Indian Penal Code"},
            ],
            "contradictions": [
                {
                    "type": "medical",
                    "statement_a": "Injury occurred at 2:00 PM per medical report",
                    "statement_b": "FIR states incident at 12:30 PM",
                    "severity": "medium",
                },
            ],
            "evidence_items": [
                {"type": "Medical report", "reliability": 0.95},
                {"type": "FIR copy", "reliability": 0.8},
            ],
            "temporal": "pre_july_2024",
            "expected_act": "IPC",
        },
        "procedure_case": {
            "title": "Review Petition - Procedural Challenge",
            "description": "Challenge to arrest procedure under BNSS",
            "sections": [
                {"section_number": "35", "act": "Bharatiya Nagarik Suraksha Sanhita"},
                {"section_number": "176", "act": "Bharatiya Nagarik Suraksha Sanhita"},
            ],
            "contradictions": [
                {
                    "type": "procedure",
                    "statement_a": "Arrest memo served at time of arrest per police",
                    "statement_b": "Petitioner claims no memo received for 48 hours",
                    "severity": "high",
                },
            ],
            "evidence_items": [
                {"type": "Arrest memo", "reliability": 0.6},
                {"type": "Petitioner affidavit", "reliability": 0.75},
            ],
            "temporal": "post_july_2024",
            "expected_act": "BNSS",
        },
    }

    def __init__(self, seed: int = 42) -> None:
        """Initialize the test suite generator.

        Args:
            seed: Random seed for reproducibility.
        """
        self.seed = seed
        random.seed(seed)

    def generate_contradiction_test_cases(
        self,
        n_cases: int = 10,
    ) -> list[dict[str, Any]]:
        """Generate synthetic test cases for contradiction detection.

        Args:
            n_cases: Number of test cases to generate.

        Returns:
            List of test case dicts with ground truth contradictions.
        """
        test_cases: list[dict[str, Any]] = []

        for i in range(n_cases):
            template = self.CASE_TEMPLATES.get(
                list(self.CASE_TEMPLATES)[i % len(self.CASE_TEMPLATES)],
                self.CASE_TEMPLATES["theft_case"],
            )

            test_case = {
                "case_id": f"test_contra_{i:03d}",
                "title": template["title"],
                "description": template["description"],
                "documents": [
                    {
                        "text": self._generate_document_text(template, i),
                        "filename": f"doc_{i}_a.txt",
                    },
                    {
                        "text": self._generate_document_text(template, i + 100),
                        "filename": f"doc_{i}_b.txt",
                    },
                ],
                "ground_truth": {
                    "contradictions": template["contradictions"],
                    "sections": template["sections"],
                    "evidence_items": template["evidence_items"],
                },
            }
            test_cases.append(test_case)

        logger.info(f"Generated {len(test_cases)} contradiction test cases")
        return test_cases

    def generate_section_matching_test_cases(
        self,
        n_cases: int = 20,
    ) -> list[dict[str, Any]]:
        """Generate test cases for section matching evaluation.

        Args:
            n_cases: Number of test cases.

        Returns:
            List of test cases with ground truth sections.
        """
        test_cases: list[dict[str, Any]] = []

        for i in range(n_cases):
            template = self.CASE_TEMPLATES.get(
                list(self.CASE_TEMPLATES)[i % len(self.CASE_TEMPLATES)],
                self.CASE_TEMPLATES["theft_case"],
            )

            test_case = {
                "case_id": f"test_sec_{i:03d}",
                "query": f"What are the applicable sections for {template['description'].lower()}?",
                "ground_truth": {
                    "sections": template["sections"],
                    "expected_act": template["expected_act"],
                },
                "temporal": template["temporal"],
            }
            test_cases.append(test_case)

        logger.info(f"Generated {len(test_cases)} section matching test cases")
        return test_cases

    def generate_temporal_routing_test_cases(
        self,
        n_cases: int = 20,
    ) -> list[dict[str, Any]]:
        """Generate test cases for IPC vs BNS temporal routing.

        Args:
            n_cases: Number of test cases.

        Returns:
            List of test cases with expected act routing.
        """
        old_acts = ["IPC", "CrPC", "IEA"]
        new_acts = ["BNS", "BNSS", "BSA"]

        test_cases: list[dict[str, Any]] = []
        for i in range(n_cases):
            is_new = i >= n_cases // 2  # Half new, half old
            expected = random.choice(new_acts if is_new else old_acts)

            test_case = {
                "case_id": f"test_temp_{i:03d}",
                "query": self._generate_temporal_query(expected),
                "temporal_context": "post_july_2024" if is_new else "pre_july_2024",
                "ground_truth": {
                    "expected_act": expected,
                    "is_new_code": is_new,
                },
            }
            test_cases.append(test_case)

        logger.info(f"Generated {len(test_cases)} temporal routing test cases")
        return test_cases

    def generate_full_eval_dataset(
        self,
        n_cases: int = 20,
    ) -> dict[str, Any]:
        """Generate a complete evaluation dataset.

        Args:
            n_cases: Number of cases per test type.

        Returns:
            Dict with all test case categories.
        """
        return {
            "contradiction_tests": self.generate_contradiction_test_cases(n_cases),
            "section_matching_tests": self.generate_section_matching_test_cases(n_cases),
            "temporal_routing_tests": self.generate_temporal_routing_test_cases(n_cases),
            "metadata": {
                "total_cases": n_cases * 3,
                "generator_seed": self.seed,
                "templates_used": list(self.CASE_TEMPLATES),
            },
        }

    def save_to_file(self, filepath: str, n_cases: int = 20) -> None:
        """Generate and save eval dataset to a JSON file.

        Args:
            filepath: Output file path.
            n_cases: Number of cases per type.
        """
        dataset = self.generate_full_eval_dataset(n_cases)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, default=str)
        logger.info(f"Saved eval dataset to {filepath}")

    # ── Helper Methods ────────────────────────────────────────
    def _generate_document_text(self, template: dict[str, Any], variant: int) -> str:
        """Generate synthetic legal document text from template."""
        # Vary the text slightly based on variant
        variants = [
            f"On {self._random_date()}, the incident occurred at approximately {random.choice(['12:30', '14:00', '15:30', '10:45'])} hours. "
            f"The complainant alleges that the accused committed {template['description'].lower()}. "
            f"Key witnesses include PW-1 (neighbor) and PW-2 (shopkeeper nearby).",
            f"According to the FIR No. {random.randint(100, 999)}/{random.randint(2023, 2024)}, registered at PS {random.choice(['City', 'Rural', 'Metro'])}, "
            f"the incident pertains to {template['description'].lower()}. "
            f"The investigating officer visited the scene on {self._random_date()}.",
        ]
        return random.choice(variants) + f"\n\nRelevant provisions: {', '.join(s['act'] + ' Section ' + s['section_number'] for s in template['sections'])}."

    def _generate_temporal_query(self, act: str) -> str:
        """Generate a query referencing a specific act."""
        queries = {
            "IPC": [
                "What is the punishment under IPC Section 302?",
                "Explain IPC Section 378 regarding theft",
                "Is IPC still applicable after July 2024?",
            ],
            "BNS": [
                "What is the punishment under BNS Section 101?",
                "Explain BNS Section 303 regarding theft",
                "How does BNS define criminal conspiracy?",
            ],
            "BNSS": [
                "What is the procedure for arrest under BNSS?",
                "Explain BNSS Section 35 regarding arrest",
                "How does BNSS differ from CrPC?",
            ],
            "CrPC": [
                "What is the procedure under CrPC Section 154?",
                "How was arrest procedure under CrPC?",
                "Is CrPC still applicable?",
            ],
            "BSA": [
                "What does BSA say about electronic evidence?",
                "Explain BSA Section 120",
                "How does BSA differ from IEA?",
            ],
            "IEA": [
                "What does Indian Evidence Act say about confessions?",
                "Explain Section 65B of Indian Evidence Act",
                "Is Indian Evidence Act still applicable?",
            ],
        }
        return random.choice(queries.get(act, queries["BNS"]))

    @staticmethod
    def _random_date() -> str:
        """Generate a random date string."""
        day = random.randint(1, 28)
        month = random.randint(1, 12)
        year = random.choice([2023, 2024])
        return f"{day:02d}/{month:02d}/{year}"
