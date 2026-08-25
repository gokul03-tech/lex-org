"""GOLD ground-truth dataset for the LexOrch-KG evaluation suites.

Four hand-verified judgments spanning four categories. Field values were
confirmed against the source PDFs in backend/test_data/. ``GOLD`` is the
single source of truth for E1 (extraction), E2 (retrieval qrels),
E3/E4 (grounding + reasoning) and E5 (human eval pack).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DATA_DIR = BACKEND_DIR / "test_data"

GOLD: dict[str, dict] = {
    "vikram": {
        "file": "01_Cybercrime_Bail_Vikram_Dev.pdf",
        "category": "criminal_bail",
        "court": "High Court of Judicature at Bombay",
        "petitioner": "Vikram Dev",
        "respondent": "The State Of Maharashtra",
        "decision_date": "14 March 2024",
        "case_number": "C.R. No. 102 of 2024",
        "judges": ["Revati Mohite Dere", "Gauri Godse"],
        "citations": ["(2024) 2 Bom CR 412", "2024 Cri LJ 1580"],
        "sections": {"482": "BNSS", "111": "BNS", "66D": "Information Technology Act", "63": "BSA"},
        "articles": [],
        "precedents": {
            "Sanjay Chandra v. Central Bureau of Investigation": "(2011) 1 SCC 694",
            "Anvar P.V. v. P.K. Basheer": "(2014) 10 SCC 473",
        },
        "outcome": "allowed",
        "timeline": ["15-01-2024", "22-01-2024", "25-01-2024", "05-03-2024"],
    },
    "ananya": {
        "file": "03_Constitutional_Writ_Ananya_Sharma.pdf",
        "category": "writ",
        "court": "Supreme Court of India",
        "petitioner": "Dr. Ananya Sharma",
        "respondent": "Union Of India & Ors",
        "decision_date": "5 May 2023",
        "case_number": None,
        "judges": ["D.Y. Chandrachud", "P.S. Narasimha"],
        "citations": ["[2023] 4 SCR 710", "(2023) 6 SCC 301"],
        "sections": {},
        "articles": ["32", "21", "19(1)(a)", "14", "19(2)"],
        "precedents": {
            "Justice K.S. Puttaswamy v. Union of India": "(2017) 10 SCC 1",
            "Anuradha Bhasin v. Union of India": "(2020) 3 SCC 637",
        },
        "outcome": "disposed of",
        "timeline": [],
    },
    "apex": {
        "file": "02_Commercial_Arbitration_Apex_Infra.pdf",
        "category": "arbitration",
        "court": "High Court of Delhi at New Delhi",
        "petitioner": "Apex Infrastructure Pvt. Ltd.",
        "respondent": "National Highways Authority of India",
        "decision_date": "18 January 2023",
        "case_number": None,
        "judges": ["Prathiba M. Singh"],
        "citations": ["AIR 2023 DEL 145", "(2023) 1 DLT 89"],
        "sections": {
            "34": "Arbitration and Conciliation Act",
            "34(2A)": "Arbitration and Conciliation Act",
            "73": "Indian Contract Act",
            "74": "Indian Contract Act",
        },
        "articles": [],
        "precedents": {
            "Associate Builders v. Delhi Development Authority": "(2015) 3 SCC 49",
            "Ssangyong Engineering & Construction Co. Ltd. v. National Highways Authority of India":
                "(2019) 15 SCC 131",
        },
        "outcome": "partly allowed",
        "timeline": ["14-08-2022", "12-05-2018", "20-11-2019", "15-02-2020"],
    },
    "mehta": {
        "file": "04_Civil_Property_Specific_Performance.pdf",
        "category": "civil",
        "court": "Supreme Court of India",
        "petitioner": "Mehta Realty Projects",
        "respondent": "Shanti Devi & Ors",
        "decision_date": "11 November 2023",
        "case_number": None,
        "judges": ["B.R. Gavai", "Vikram Nath"],
        "citations": ["(2023) 5 ALD 210", "AIR 2024 SC 189"],
        "sections": {
            "16(c)": "Specific Relief Act",
            "74": "Indian Contract Act",
            "O.39 R.1-2": "Code of Civil Procedure",
        },
        "articles": [],
        "precedents": {
            "Chand Rani v. Kamal Rani": "(1993) 1 SCC 519",
            "Sughar Singh v. Hari Singh": "(2020) 13 SCC 285",
        },
        "outcome": "allowed",
        "timeline": [],
    },
}

OUTCOME_VERBS = ("allowed", "partly allowed", "disposed of", "dismissed")


@dataclass
class GoldDoc:
    """Typed view over one GOLD entry plus its resolved source path."""

    key: str
    data: dict
    path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.path = TEST_DATA_DIR / self.data["file"]

    def __getattr__(self, name: str):
        try:
            return self.data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def gold_docs() -> list[GoldDoc]:
    """All GOLD entries as typed records with resolved paths."""
    return [GoldDoc(key=k, data=v) for k, v in GOLD.items()]


def gold_markers(doc: GoldDoc) -> list[str]:
    """Distinctive strings whose presence marks a chunk relevant to this doc."""
    markers: list[str] = []
    for num, act in (doc.data.get("sections") or {}).items():
        markers.append(f"Section {num}")
        base = act.split(",")[0].split("(")[0].strip()
        if len(base) > 3:
            markers.append(base)
    for name, cite in (doc.data.get("precedents") or {}).items():
        markers.append(name)
        markers.append(cite)
    return sorted({m for m in markers if m})
