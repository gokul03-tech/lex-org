"""Hallucination gate: verifies cited statutes and precedents against real law.

Replaces blind self-consistency trust with evidence that each cited
act+section exists and each precedent citation matches a canonical record.
Verdicts: verified | invalid | procedural | unverifiable | skip.
"""

from __future__ import annotations

import re
from typing import Any

# ── Statute catalog: canonical act -> aliases, max section, penal provisions ─
STATUTES: dict[str, dict[str, Any]] = {
    "ndps": {
        "aliases": ("narcotic drugs and psychotropic substances act", "ndps act", "ndps"),
        "max": 83,
        "penal": set(range(15, 32)) | {"27A"},
    },
    "bns": {
        "aliases": ("bharatiya nyaya sanhita", "bharatiya nyaya sanhita (bns)", "nyaya sanhita", "bns"),
        "max": 358,
        "penal": None,
    },
    "bnss": {
        "aliases": ("bharatiya nagarik suraksha sanhita", "bharatiya nagarik suraksha sanhita (bnss)", "bnss"),
        "max": 533,
        "penal": None,
    },
    "bsa": {
        "aliases": ("bharatiya sakshya adhiniyam", "bharatiya sakshya adhiniyam (bsa)", "bsa", "bs act"),
        "max": 175,
        "penal": None,
    },
    "ipc": {
        "aliases": ("indian penal code", "ipc"),
        "max": 511,
        "penal": None,
    },
    "crpc": {
        "aliases": ("code of criminal procedure", "criminal procedure code", "crpc"),
        "max": 484,
        "penal": None,
    },
    "evidence": {
        "aliases": ("indian evidence act", "evidence act", "indian evidence act, 1872"),
        "max": 167,
        "penal": None,
    },
    "contract": {
        "aliases": ("indian contract act", "contract act", "indian contract act, 1872", "contract act, 1872"),
        "max": 238,
        "penal": None,
    },
    "specific_relief": {
        "aliases": ("specific relief act", "specific relief act, 1963"),
        "max": 42,
        "penal": None,
    },
    "arbitration": {
        "aliases": ("arbitration and conciliation act", "arbitration and conciliation act, 1996", "a&c act"),
        "max": 87,
        "penal": None,
    },
    "companies": {
        "aliases": ("companies act", "companies act, 2013"),
        "max": 470,
        "penal": None,
    },
    "ibc": {
        "aliases": ("insolvency and bankruptcy code", "insolvency and bankruptcy code, 2016", "ibc"),
        "max": 255,
        "penal": None,
    },
    "ni": {
        "aliases": ("negotiable instruments act", "negotiable instruments act, 1881", "ni act"),
        "max": 147,
        "penal": None,
    },
    "it": {
        "aliases": ("information technology act", "information technology act, 2000", "it act"),
        "max": 90,
        "penal": None,
    },
    "cpc": {
        "aliases": ("code of civil procedure", "civil procedure code", "cpc"),
        "max": 158,
        "penal": None,
    },
    "motor_vehicles": {
        "aliases": ("motor vehicles act", "motor vehicles act, 1988"),
        "max": 217,
        "penal": None,
    },
    "dowry": {
        "aliases": ("dowry prohibition act", "dowry prohibition act, 1961"),
        "max": 9,
        "penal": set(range(1, 9)),
    },
    "pc_amendment": {
        "aliases": ("protection of children from sexual offences act", "pocso act", "pocso"),
        "max": 47,
        "penal": None,
    },
    "sc_st": {
        "aliases": ("scheduled castes and the scheduled tribes (prevention of atrocities) act", "sc/st act", "sc st act"),
        "max": 23,
        "penal": None,
    },
}

_SECTION_NUM_RE = re.compile(r"^\s*(\d+)\s*(?:[A-Za-z]|\(\d+[A-Za-z]?\)|\([A-Za-z]\))*\s*$")


def _normalize_act(name: str | None) -> str:
    if not name:
        return ""
    s = re.sub(r"[^a-z0-9\s]", "", name.lower())
    candidates: list[tuple[str, str]] = []
    for key, spec in STATUTES.items():
        for alias in spec["aliases"]:
            alias_n = re.sub(r"[^a-z0-9\s]", "", alias.lower())
            candidates.append((key, alias_n))
    candidates.sort(key=lambda t: len(t[1]), reverse=True)
    for key, alias_n in candidates:
        if len(alias_n) < 6:
            if re.search(r"\b" + re.escape(alias_n) + r"\b", s):
                return key
        elif alias_n in s:
            return key
    return ""


def _section_number(num: str | None) -> str:
    if not num:
        return ""
    m = _SECTION_NUM_RE.match(str(num).strip())
    return m.group(1) if m else ""


# ── Canonical precedents: verified case name -> correct record ─────────────
VERIFIED_CASES: dict[str, dict[str, Any]] = {
    "sughar singh v hari singh": {"citation": "2021 SCC OnLine SC 975", "year": 2021, "court": "Supreme Court of India"},
    "state of punjab v balbir singh": {"citation": "(1994) 3 SCC 299", "year": 1994, "court": "Supreme Court of India"},
    "balbir singh v state": {"citation": "(1994) 3 SCC 299", "year": 1994, "court": "Supreme Court of India"},
    "ssangyong engineering construction v nhai": {"citation": "(2019) 15 SCC 131", "year": 2019, "court": "Supreme Court of India"},
    "delhi airport metro express v dmrc": {"citation": "(2022) 1 SCC 131", "year": 2022, "court": "Supreme Court of India"},
    "delhi airport metro express v dmrc": {"citation": "(2022) 1 SCC 131", "year": 2022, "court": "Supreme Court of India"},
    "chand rani v kamal rani": {"citation": "(1993) 1 SCC 519", "year": 1993, "court": "Supreme Court of India"},
    "sanjay chandra v cbi": {"citation": "(2012) 1 SCC 40", "year": 2012, "court": "Supreme Court of India"},
    "arnesh kumar v state of bihar": {"citation": "(2014) 8 SCC 273", "year": 2014, "court": "Supreme Court of India"},
    "anvar p v v p k basheer": {"citation": "(2014) 10 SCC 473", "year": 2014, "court": "Supreme Court of India"},
    "state of punjab v baldev singh": {"citation": "(1999) 6 SCC 172", "year": 1999, "court": "Supreme Court of India"},
    "maneka gandhi v union of india": {"citation": "(1978) 1 SCC 248", "year": 1978, "court": "Supreme Court of India"},
    "kesavananda bharati v state of kerala": {"citation": "(1973) 4 SCC 225", "year": 1973, "court": "Supreme Court of India"},
    "vishaka v state of rajasthan": {"citation": "(1997) 6 SCC 241", "year": 1997, "court": "Supreme Court of India"},
}

_SCC_CITE_RE = re.compile(r"^\s*\((\d{4})\)\s*(\d{1,3})\s*SCC(?:|[\s:,-]+(\d{1,4}(?:-\d{1,4})?))?\s*$")
_ONLINE_CITE_RE = re.compile(r"^\s*(\d{4})\s*SCC\s*OnLine\s+(SC|HC\s+[A-Za-z\s]+|Del|Bom|Cal|Mad|All|P&H|Kar|Guj|Tel)\s+(\d+)\s*$")
_AIR_CITE_RE = re.compile(r"^\s*AIR\s+(\d{4})\s+(SC|AP|Del|Bom|Cal|Mad|All|Ker|Kar|Guj|Ori|Raj|MP|HP)\s+(\d+)\s*$")

_PLACEHOLDER_NAMES = ("keyword", "precedent", "precedent citation", "n/a", "na",
                      "unknown citation", "no sufficiently")


def _norm_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9]", "", name.lower())
    s = re.sub(r"dead|lrs?|ors?|others|thr|ltd|limited|pvt|private|co|the|and|of|c", "", s)
    return s


def _lookup_case(name: str) -> dict[str, Any] | None:
    n = _norm_name(name)
    for key, record in VERIFIED_CASES.items():
        if _norm_name(key) in n or n in _norm_name(key):
            return record
    return None


def _scc_year_plausible(year: int, volume: int) -> bool:
    if not (1900 <= year <= 2100):
        return False
    cap = 2 if year < 1980 else (4 if year < 1999 else (9 if year < 2010 else 20))
    return 1 <= volume <= cap


def validate_section(act_name: str | None, section_num: str | None) -> dict[str, Any]:
    key = _normalize_act(act_name)
    num = _section_number(section_num)
    if not key:
        return {"status": "unverifiable", "reason": "Act not in verification catalog; manually confirm the citation."}
    spec = STATUTES[key]
    if not num:
        return {"status": "invalid", "reason": f"Unparseable section number under {act_name}."}
    num_int = int(num)
    if not (1 <= num_int <= spec["max"]):
        return {"status": "invalid", "reason": f"{act_name} has no Section {num}; it only runs to Section {spec['max']}."}
    if spec["penal"] is not None:
        raw = str(section_num or "").strip()
        if re.search(r"[A-Za-z]", raw):
            is_penal = str(raw.upper()) in spec["penal"]
        else:
            is_penal = num_int in {p for p in spec["penal"] if isinstance(p, int)}
        if not is_penal:
            return {"status": "procedural", "reason": f"Section {num} of {act_name} exists but is a procedural/enforcement provision, not a substantive offence."}
    return {"status": "verified", "reason": f"Section {num} of {act_name} exists in statute."}


def validate_precedent(prec: dict[str, Any]) -> dict[str, Any]:
    name = (prec.get("case_name") or "").strip()
    citation = (prec.get("citation") or "").strip()
    year = str(prec.get("year") or "").strip()

    if not name or name.lower() in _PLACEHOLDER_NAMES or name.lower().startswith("no sufficiently"):
        return {"status": "skip", "reason": "Placeholder entry; not a real precedent."}

    record = _lookup_case(name)
    if record:
        if citation and record["citation"] in citation:
            return {"status": "verified", "reason": f"Matches canonical citation {record['citation']}."}
        if record.get("year"):
            try:
                if year and int(re.sub(r"\D", "", year)) != record["year"]:
                    return {"status": "invalid", "reason": f"Fabricated year for {name}: real case is from {record['year']} ({record['citation']})."}
            except ValueError:
                pass
        return {"status": "invalid", "reason": f"Fabricated citation for {name}: correct record is {record['citation']}."}

    m = _SCC_CITE_RE.match(citation)
    if m:
        c_year, volume = int(m.group(1)), int(m.group(2))
        if not _scc_year_plausible(c_year, volume):
            return {"status": "invalid", "reason": f"Implausible SCC citation '{citation}' (year/volume mismatch)."}
        return {"status": "unverifiable", "reason": "Plausible SCC citation; could not cross-check against a known record."}

    if _ONLINE_CITE_RE.match(citation) or _AIR_CITE_RE.match(citation):
        return {"status": "unverifiable", "reason": "Plausible citation format; could not cross-check against a known record."}

    if citation and citation.lower() not in ("unknown citation", "unknown", "n/a", "na", "source:"):
        return {"status": "invalid", "reason": f"Unrecognized or malformed citation '{citation}'."}

    return {"status": "unverifiable", "reason": "No citation provided; could not verify."}


def run_verification(
    applicable_sections: list[dict[str, Any]] | None,
    precedents: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    import json as _json

    if isinstance(applicable_sections, str):
        try:
            applicable_sections = _json.loads(applicable_sections)
        except Exception:
            applicable_sections = []
    if isinstance(precedents, str):
        try:
            precedents = _json.loads(precedents)
        except Exception:
            precedents = []

    sections = applicable_sections or []
    precs = precedents or []

    section_verdicts: list[dict[str, Any]] = []
    precedent_verdicts: list[dict[str, Any]] = []

    for s in sections:
        if not isinstance(s, dict):
            continue
        act = s.get("act") or s.get("act_name") or ""
        num = s.get("section_number") or s.get("num") or ""
        verdict = validate_section(act, num)
        verdict.update({"act": act, "num": num})
        section_verdicts.append(verdict)

    for p in precs:
        if not isinstance(p, dict):
            continue
        verdict = validate_precedent(p)
        verdict.update({"case_name": (p.get("case_name") or "").strip()[:80]})
        precedent_verdicts.append(verdict)

    counted = [v for v in section_verdicts + precedent_verdicts if v["status"] != "skip"]
    verified = sum(1 for v in counted if v["status"] == "verified")
    invalid = sum(1 for v in counted if v["status"] == "invalid")
    procedural = sum(1 for v in counted if v["status"] == "procedural")

    attempts = len(counted)
    verification_rate = verified / attempts if attempts else 1.0

    return {
        "section_verdicts": section_verdicts,
        "precedent_verdicts": precedent_verdicts,
        "checked_items": attempts,
        "verified_count": verified,
        "hallucination_count": invalid,
        "procedural_warnings": procedural,
        "verification_rate": round(verification_rate, 3),
    }