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
        "aliases": ("scheduled castes and scheduled tribes (prevention of atrocities) act", "sc/st act", "sc st act", "prevention of atrocities act"),
        "max": 23,
        "penal": None,
    },
    "pmla": {
        "aliases": ("prevention of money laundering act", "prevention of money laundering act, 2002", "pmla"),
        "max": 75,
        "penal": set(range(3, 10)),
    },
    "pca": {
        "aliases": ("prevention of corruption act", "prevention of corruption act, 1988", "pc act"),
        "max": 31,
        "penal": set(range(7, 16)),
    },
    "sarfaesi": {
        "aliases": ("securitisation and reconstruction of financial assets and enforcement of security interest act", "sarfaesi act", "sarfaesi"),
        "max": 42,
        "penal": None,
    },
    "consumer_protection": {
        "aliases": ("consumer protection act", "consumer protection act, 2019", "copra"),
        "max": 107,
        "penal": None,
    },
    "tpa": {
        "aliases": ("transfer of property act", "transfer of property act, 1882", "tpa"),
        "max": 137,
        "penal": None,
    },
    "limitation": {
        "aliases": ("limitation act", "limitation act, 1963"),
        "max": 32,
        "penal": None,
    },
    "commercial_courts": {
        "aliases": ("commercial courts act", "commercial courts act, 2015", "commercial courts, commercial division and commercial appellate division of high courts act"),
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
    # Criminal & Bail Jurisprudence
    "sanjay chandra v cbi": {"citation": "(2012) 1 SCC 40", "year": 2012, "court": "Supreme Court of India"},
    "arnesh kumar v state of bihar": {"citation": "(2014) 8 SCC 273", "year": 2014, "court": "Supreme Court of India"},
    "satender kumar antil v cbi": {"citation": "(2022) 10 SCC 51", "year": 2022, "court": "Supreme Court of India"},
    "gurbaksh singh sibbia v state of punjab": {"citation": "(1980) 2 SCC 565", "year": 1980, "court": "Supreme Court of India"},
    "sushila aggarwal v state nct of delhi": {"citation": "(2020) 5 SCC 1", "year": 2020, "court": "Supreme Court of India"},
    "d k basu v state of west bengal": {"citation": "(1997) 1 SCC 416", "year": 1997, "court": "Supreme Court of India"},
    "lalita kumari v govt of up": {"citation": "(2014) 2 SCC 1", "year": 2014, "court": "Supreme Court of India"},
    "p chidambaram v directorate of enforcement": {"citation": "(2020) 13 SCC 791", "year": 2020, "court": "Supreme Court of India"},
    "vijay madanlal choudhary v union of india": {"citation": "2022 SCC OnLine SC 929", "year": 2022, "court": "Supreme Court of India"},
    "manish sisodia v directorate of enforcement": {"citation": "2024 SCC OnLine SC 1920", "year": 2024, "court": "Supreme Court of India"},
    "state of haryana v bhajan lal": {"citation": "1992 Supp (1) SCC 335", "year": 1992, "court": "Supreme Court of India"},
    "neeharika infrastructure v state of maharashtra": {"citation": "(2021) 19 SCC 401", "year": 2021, "court": "Supreme Court of India"},
    "sharad birdhichand sarda v state of maharashtra": {"citation": "(1984) 4 SCC 116", "year": 1984, "court": "Supreme Court of India"},
    "babu singh v state of up": {"citation": "(1978) 1 SCC 579", "year": 1978, "court": "Supreme Court of India"},
    "kalyan chandra sarkar v rajesh ranjan": {"citation": "(2004) 7 SCC 528", "year": 2004, "court": "Supreme Court of India"},
    "chhotu ram v state of haryana": {"citation": "(2013) 4 SCC 401", "year": 2013, "court": "Supreme Court of India"},

    # NDPS Jurisprudence
    "state of punjab v balbir singh": {"citation": "(1994) 3 SCC 299", "year": 1994, "court": "Supreme Court of India"},
    "balbir singh v state": {"citation": "(1994) 3 SCC 299", "year": 1994, "court": "Supreme Court of India"},
    "state of punjab v baldev singh": {"citation": "(1999) 6 SCC 172", "year": 1999, "court": "Supreme Court of India"},
    "vijaysinh chandubha jadeja v state of gujarat": {"citation": "(2011) 1 SCC 609", "year": 2011, "court": "Supreme Court of India"},
    "mohan lal v state of punjab": {"citation": "(2018) 17 SCC 627", "year": 2018, "court": "Supreme Court of India"},
    "tofan singh v state of tamil nadu": {"citation": "(2021) 4 SCC 1", "year": 2021, "court": "Supreme Court of India"},
    "union of india v mohd nawaz khan": {"citation": "(2021) 10 SCC 100", "year": 2021, "court": "Supreme Court of India"},
    "arif khan v state of uttarakhand": {"citation": "(2018) 18 SCC 380", "year": 2018, "court": "Supreme Court of India"},

    # Electronic Evidence & Procedure
    "anvar p v v p k basheer": {"citation": "(2014) 10 SCC 473", "year": 2014, "court": "Supreme Court of India"},
    "arjun panditrao khotkar v kailash kushanrao gorantyal": {"citation": "(2020) 7 SCC 1", "year": 2020, "court": "Supreme Court of India"},
    "shafhi mohammad v state of hp": {"citation": "(2018) 2 SCC 801", "year": 2018, "court": "Supreme Court of India"},
    "selvi v state of karnataka": {"citation": "(2010) 7 SCC 263", "year": 2010, "court": "Supreme Court of India"},

    # Constitutional Jurisprudence
    "maneka gandhi v union of india": {"citation": "(1978) 1 SCC 248", "year": 1978, "court": "Supreme Court of India"},
    "kesavananda bharati v state of kerala": {"citation": "(1973) 4 SCC 225", "year": 1973, "court": "Supreme Court of India"},
    "k s puttaswamy v union of india": {"citation": "(2017) 10 SCC 1", "year": 2017, "court": "Supreme Court of India"},
    "navtej singh johar v union of india": {"citation": "(2018) 10 SCC 1", "year": 2018, "court": "Supreme Court of India"},
    "joseph shine v union of india": {"citation": "(2019) 3 SCC 39", "year": 2019, "court": "Supreme Court of India"},
    "shreya singhal v union of india": {"citation": "(2015) 5 SCC 1", "year": 2015, "court": "Supreme Court of India"},
    "anuradha bhasin v union of india": {"citation": "(2020) 3 SCC 637", "year": 2020, "court": "Supreme Court of India"},
    "indira nehru gandhi v raj narain": {"citation": "1975 Supp SCC 1", "year": 1975, "court": "Supreme Court of India"},

    # Arbitration & Commercial Jurisprudence
    "ssangyong engineering construction v nhai": {"citation": "(2019) 15 SCC 131", "year": 2019, "court": "Supreme Court of India"},
    "delhi airport metro express v dmrc": {"citation": "(2022) 1 SCC 131", "year": 2022, "court": "Supreme Court of India"},
    "associates builders v dda": {"citation": "(2015) 3 SCC 49", "year": 2015, "court": "Supreme Court of India"},
    "vidya drolia v durga trading corp": {"citation": "(2021) 2 SCC 1", "year": 2021, "court": "Supreme Court of India"},
    "in re interplay between arbitration agreements and stamp act": {"citation": "2023 SCC OnLine SC 1666", "year": 2023, "court": "Supreme Court of India"},
    "perkins eastman architects v hscc": {"citation": "(2020) 20 SCC 760", "year": 2020, "court": "Supreme Court of India"},
    "duro felguera sa v gangavaram port ltd": {"citation": "(2017) 9 SCC 729", "year": 2017, "court": "Supreme Court of India"},
    "oil and natural gas corp v saw pipes ltd": {"citation": "(2003) 5 SCC 705", "year": 2003, "court": "Supreme Court of India"},

    # Civil, Contracts & Specific Relief
    "sughar singh v hari singh": {"citation": "2021 SCC OnLine SC 975", "year": 2021, "court": "Supreme Court of India"},
    "chand rani v kamal rani": {"citation": "(1993) 1 SCC 519", "year": 1993, "court": "Supreme Court of India"},
    "kamal kumar v prema": {"citation": "(2019) 14 SCC 304", "year": 2019, "court": "Supreme Court of India"},
    "satyabrata ghose v mugneeram bangur": {"citation": "1954 SCR 310", "year": 1954, "court": "Supreme Court of India"},
    "kailash nath associates v dda": {"citation": "(2015) 4 SCC 136", "year": 2015, "court": "Supreme Court of India"},

    # Insolvency & Bankruptcy (IBC)
    "innoventive industries ltd v icici bank": {"citation": "(2018) 1 SCC 407", "year": 2018, "court": "Supreme Court of India"},
    "swiss ribbons pvt ltd v union of india": {"citation": "(2019) 4 SCC 17", "year": 2019, "court": "Supreme Court of India"},
    "committee of creditors of essar steel v satish kumar gupta": {"citation": "(2020) 8 SCC 531", "year": 2020, "court": "Supreme Court of India"},
    "arcelormittal india pvt ltd v satish kumar gupta": {"citation": "(2019) 2 SCC 1", "year": 2019, "court": "Supreme Court of India"},

    # Cheque Bounce / Negotiable Instruments (NI Act S.138)
    "rangappa v sri mohan": {"citation": "(2010) 11 SCC 441", "year": 2010, "court": "Supreme Court of India"},
    "dashrath roopsingh rathod v state of maharashtra": {"citation": "(2014) 9 SCC 129", "year": 2014, "court": "Supreme Court of India"},
    "bir singh v mukesh kumar": {"citation": "(2019) 4 SCC 197", "year": 2019, "court": "Supreme Court of India"},
    "triyambak s hegde v sripad": {"citation": "(2022) 1 SCC 742", "year": 2022, "court": "Supreme Court of India"},

    # Women's Rights & POCSO
    "vishaka v state of rajasthan": {"citation": "(1997) 6 SCC 241", "year": 1997, "court": "Supreme Court of India"},
    "independent thought v union of india": {"citation": "(2017) 10 SCC 800", "year": 2017, "court": "Supreme Court of India"},
    "aparna bhat v state of madhya pradesh": {"citation": "2021 SCC OnLine SC 230", "year": 2021, "court": "Supreme Court of India"},
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
        correction = {
            "canonical_year": record.get("year"),
            "canonical_citation": record.get("citation"),
            "canonical_court": record.get("court"),
        }
        if citation and record["citation"] in citation:
            verdict = {"status": "verified", "reason": f"Matches canonical citation {record['citation']}."}
            verdict.update(correction)
            return verdict
        if record.get("year"):
            try:
                if year and int(re.sub(r"\D", "", year)) != record["year"]:
                    verdict = {"status": "invalid", "reason": f"Fabricated year for {name}: real case is from {record['year']} ({record['citation']})."}
                    verdict.update(correction)
                    return verdict
            except ValueError:
                pass
        verdict = {"status": "invalid", "reason": f"Fabricated citation for {name}: correct record is {record['citation']}."}
        verdict.update(correction)
        return verdict

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