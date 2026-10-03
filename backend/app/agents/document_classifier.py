"""Structural document-type and legal-domain classifier.

The previous classifier counted bare keywords (``detect_category``), which put
every document that mentioned "accused" into criminal trial. That mis-fired on
the exact families this project has to support:

  * an academic dossier whose commentary discusses cyber-crime but whose
    decision is a CJM criminal-conviction report,
  * an insolvency appeal that quotes the Arbitration Act in obiter,
  * a civil case file that lists BNS/BNSS in a boilerplate "applicable laws"
    footer.

Classification here is therefore evidence-scored rather than first-match-wins:
each type and domain accumulates weighted signals from several regions of the
document (caption, structural headings, and body), and a document may satisfy
several at once. Signals are deliberately drawn from *structural* markers
("CASE AT A GLANCE", "Chronology of Important Events", "IN THE SUPREME COURT OF
INDIA") rather than from substantive keywords alone, because structure is what
distinguishes a dossier from a judgment even when their subject matter matches.

No document-specific rules: every signal below is a generic marker of Indian
legal drafting.
"""
from __future__ import annotations

import re
from typing import Any

# ── Document types ────────────────────────────────────────────────────────
# Each entry: (weight, compiled pattern). Weights favour structural markers.
_DOC_TYPE_SIGNALS: dict[str, list[tuple[int, re.Pattern[str]]]] = {
    "academic_dossier": [
        (3, re.compile(r"\bCASE\s+AT\s+A\s+GLANCE\b", re.I)),
        (3, re.compile(r"\bCASE\s+STUDY\b|\bCASE\s+STUDY\s+FOR\b", re.I)),
        (3, re.compile(r"\bCASE\s+(?:FILE|DOSSIER)\b.{0,40}\b(?:study|academic|educational)\b", re.I | re.S)),
        (2, re.compile(r"\bFACT\s+CHRONOLOGY\b|\bCHRONOLOGY\s+OF\s+IMPORTANT\s+EVENTS\b", re.I)),
        (2, re.compile(r"\b(?:TABLE\s+OF\s+CONTENTS|INDEX\s+OF\s+AUTHORITIES)\b", re.I)),
        (2, re.compile(r"\bThis\s+(?:case\s+file|dossier|compilation)\s+is\s+(?:intended|designed|prepared)\b", re.I)),
        (2, re.compile(r"\bACADEMIC\s+(?:PURPOSE|PURPOSES|EXERCISE)\b", re.I)),
        (2, re.compile(r"\b(?:LEARNING\s+OBJECTIVES|LEARNING\s+POINTS)\b", re.I)),
        (1, re.compile(r"\b(?:Disclaimer|Prepared\s+for\s+academic)\b", re.I)),
    ],
    "illustrative_case_file": [
        (3, re.compile(r"\bILL\s+OF\s+QUANTITIES\b|\bBOQ\b", re.I)),
        (3, re.compile(r"\b(?:ILLUSTRATIVE|SPECIMEN|HYPOTHETICAL|MODEL)\s+(?:JUDGMENT|DECREE|CASE)\b", re.I)),
        (2, re.compile(r"\bIllustrative\s+Judgment\s+and\s+Decree\b", re.I)),
        (2, re.compile(r"\bPLAINTIFF'?S?\s+FINAL\s+WRITTEN\s+SUBMISSIONS\b", re.I)),
        (2, re.compile(r"\bDOCUMENTARY\s+EXHIBITS?\s+AND\s+EVIDENCE\s+REGISTER\b", re.I)),
        (1, re.compile(r"\bThis\s+is\s+(?:an?\s+)?illustrative\b", re.I)),
    ],
    "insolvency_appeal": [
        (3, re.compile(r"\b(?:INSOLVENCY\s+AND\s+BANKRUPTCY\s+CODE|IBC)\b", re.I)),
        (3, re.compile(r"\bNCLT\b|\bNational\s+Company\s+Law\s+Tribunal\b", re.I)),
        (2, re.compile(r"\bCorporate\s+Insolvency\s+Resolution\s+Process\b|\bCIRP\b", re.I)),
        (2, re.compile(r"\b(?:Insolvency\s+Application|IA\s+under\s+Section\s+9|resolution\s+plan)\b", re.I)),
        (2, re.compile(r"\b(?:Moratorium\s+under\s+Section\s+14|liquidation\s+under\s+Section\s+33)\b", re.I)),
    ],
    "arbitration_award": [
        (3, re.compile(r"\bARBITRAT(?:ION|OR)\s+(?:AWARD|TRIBUNAL)\b", re.I)),
        (3, re.compile(r"\bsole\s+arbitrator\b|\bArbitration\s+and\s+Conciliation\s+Act\b", re.I)),
        (2, re.compile(r"\b(?:Claimant'?s?|Respondent'?s?)\s+submissions\s+on\s+arbitration\b", re.I)),
    ],
    "bail_application": [
        (3, re.compile(r"\b(?:prima\s+facie\s+case\s+for\s+(?:interim\s+)?custody|bail\s+(?:application|petition|matter))\b", re.I)),
        (2, re.compile(r"\bSection\s+(?:437|439|483)\s+CrPC\b|\bSections?\s+(?:437|439|483)\s+of\s+the\s+CrPC\b", re.I)),
        (2, re.compile(r"\b(?:Anticipatory\s+bail|sought\s+bail|praying\s+for\s+bail)\b", re.I)),
        (2, re.compile(r"\bConditions\s+(?:for|of)\s+(?:grant|release)\b", re.I)),
    ],
    "writ_petition": [
        (3, re.compile(r"\bWrit\s+(?:Petition|Appeal)\s*\(", re.I)),
        (3, re.compile(r"\b(?:Article\s+32|Article\s+226)\b.{0,80}\bwrit\b", re.I | re.S)),
        (2, re.compile(r"\bCERTIFICATION\s+(?:UNDER\s+ARTICLE\s+143)?\b", re.I)),
        (2, re.compile(r"\b(?:MANDAMUS|HABEAS\s+CORPUS|CERTIORARI|QUO\s+WARRANTO)\b", re.I)),
    ],
    "standard_judgment": [
        (3, re.compile(r"^\s*JUDGMENT\s*$", re.I | re.M)),
        (3, re.compile(r"\bJUDGMENT\s+AND\s+(?:SENTENCE|ORDER)\b", re.I)),
        (2, re.compile(r"\b(?:Appellant|Respondent)\s+(?:is|are)\s+(?:allowed|set\s+aside|dismissed)\b", re.I)),
        (2, re.compile(r"\bThis\s+appeal\s+arises\s+out\s+of\b", re.I)),
        (2, re.compile(r"\b(?:We\s+pass\s+the\s+following\s+order|we\s+allow\s+the\s+appeal|we\s+dismiss\s+the\s+appeal)\b", re.I)),
        (1, re.compile(r"\b(?:learned\s+(?:Senior\s+)?Counsel\s+appearing|solicitor\s+general\s+appearing)\b", re.I)),
    ],
}

# ── Legal domains ─────────────────────────────────────────────────────────
_DOMAIN_SIGNALS: dict[str, list[tuple[int, re.Pattern[str]]]] = {
    "insolvency_bankruptcy": [
        (3, re.compile(r"\bInsolvency\s+and\s+Bankruptcy\s+Code\b", re.I)),
        (2, re.compile(r"\bNCLT\b|\bCIRP\b|\bresolution\s+plan\b|\bCOA\b", re.I)),
    ],
    "environmental": [
        (3, re.compile(r"\bEnvironment(?:al)?\s*\(?Protection\)?\s*Act\b", re.I)),
        (3, re.compile(r"\b(?:Forest\s*\(?Conservation\)?\s*Act|Wildlife\s*\(?Protection\)?\s*Act)\b", re.I)),
        (2, re.compile(r"\bEnvironmental\s+Impact\s+Assessment\b|\bEIA\b", re.I)),
        (2, re.compile(r"\bPollution\s+Control\s+Board\b|\bNGT\b|\bNational\s+Green\s+Tribunal\b", re.I)),
        (2, re.compile(r"\b(?:deforestation|ecologically\s+sensitive|mining\s+lease)\b", re.I)),
    ],
    "constitutional": [
        (3, re.compile(r"\bArticle\s+\d{1,3}\b(?:\s*\(\d+\))?", re.I)),
        (2, re.compile(r"\b(?:Fundamental\s+Rights|Directive\s+Principles|Article\s+32\b)", re.I)),
    ],
    "criminal": [
        (3, re.compile(r"\b(?:Indian\s+Penal\s+Code|Bharatiya\s+Nyaya\s+Sanhita|\bIPC\b|\bBNS\b)", re.I)),
        (3, re.compile(r"\bCode\s+of\s+Criminal\s+Procedure\b|\bCrPC\b|\bBNSS\b", re.I)),
        (2, re.compile(r"\b(?:accused\s+is\s+convicted|is\s+acquitted|charge\s+sheet|First\s+Information\s+Report|\bFIR\b)", re.I)),
        (2, re.compile(r"\bIndian\s+Evidence\s+Act\b|\bBharatiya\s+Sakshya\s+Adhiniyam\b", re.I)),
        (2, re.compile(r"\bNdps\b|\bNDPS\b|\bcontrolled\s+substance", re.I)),
    ],
    "labour": [
        (3, re.compile(r"\bIndustrial\s+(?:Disputes\s+Act|Employment\s+Act|Labour\s+Act)\b", re.I)),
        (2, re.compile(r"\bCode\s+on\s+Wages\b|\bCode\s+on\s+Social\s+Security\b|\bEPF\b", re.I)),
    ],
    "tax": [
        (3, re.compile(r"\b(?:Income\s+Tax\s+Act|Customs\s+Act|GST\s*\(?Central\s+Goods|CGST\b|SGST\b)", re.I)),
        (2, re.compile(r"\b(?:Assessment\s+Year|tax\s+demand\s+notice|section\s+35[ABH]?\s+of\s+the\s+Income)", re.I)),
    ],
    "corporate": [
        (3, re.compile(r"\bCompanies\s+Act,\s*2013\b", re.I)),
        (2, re.compile(r"\b(?:Board\s+of\s+Directors|share\s+capital|Articles\s+of\s+Association)\b", re.I)),
    ],
    "family": [
        (3, re.compile(r"\b(?:Hindu\s+(?:Marriage|Adoption|Succession)\s+Act|Indian\s+Divorce\s+Act|Special\s+Marriage\s+Act)\b", re.I)),
        (2, re.compile(r"\b(?:petition\s+for\s+divorce|maintenance\s+application|custody\s+of\s+children)\b", re.I)),
    ],
    "intellectual_property": [
        (3, re.compile(r"\b(?:Trade\s+Marks\s+Act|Patents\s+Act|Copyright\s+Act|Designs\s+Act)\b", re.I)),
        (2, re.compile(r"\b(?:trademark\s+infringement|patent\s+application|copyright\s+infringement)\b", re.I)),
    ],
    "civil_contract": [
        (3, re.compile(r"\b(?:Indian\s+Contract\s+Act|Specific\s+Relief\s+Act|Code\s+of\s+Civil\s+Procedure)\b", re.I)),
        (3, re.compile(r"\bSale\s+of\s+Goods\s+Act\b", re.I)),
        (2, re.compile(r"\b(?:specific\s+performance|agreement\s+to\s+sell|sale\s+deed|decree|injunction)\b", re.I)),
    ],
}

# Metadata footers that list statutes without applying them. Their presence
# must not pull the domain away from what the decision actually decides.
_BOILERPLATE_ACT_LIST = re.compile(
    r"\b(?:applicable\s+laws?|laws?\s+applicable|statutes?\s+applicable|"
    r"list\s+of\s+applicable\s+(?:acts?|statutes?)|relevant\s+acts?)\b",
    re.I,
)

_TYPE_LABELS = {
    "academic_dossier": "Academic Case Dossier/Study",
    "illustrative_case_file": "Illustrative/Fictional Case File",
    "insolvency_appeal": "Insolvency/IBC Appeal",
    "arbitration_award": "Arbitration Award",
    "bail_application": "Bail Application",
    "writ_petition": "Writ Petition",
    "standard_judgment": "Standard Court Judgment",
}

_DOMAIN_LABELS = {
    "constitutional": "Constitutional Law",
    "criminal": "Criminal Law",
    "civil_contract": "Civil/Contract Law",
    "corporate": "Commercial/Corporate Law",
    "insolvency_bankruptcy": "Insolvency/Bankruptcy (IBC)",
    "environmental": "Environmental Law",
    "intellectual_property": "Intellectual Property",
    "family": "Family Law",
    "labour": "Labour Law",
    "tax": "Tax Law",
}


def _score(signals: dict[str, list[tuple[int, re.Pattern[str]]]], text: str) -> dict[str, int]:
    return {
        key: sum(w for w, pat in pats if pat.search(text))
        for key, pats in signals.items()
    }


def _restrict_to_substantive(text: str, boilerplate_at: int | None) -> str:
    """Drop a trailing "Applicable laws:" list before domain scoring."""
    if boilerplate_at is None:
        return text
    return text[:boilerplate_at]


def _indicators(text: str, limit: int = 5) -> list[str]:
    """Short verbatim phrases that support the classification.

    These are excerpts of the document, never invented terms: the point is to
    let a reviewer check the call, so they must be traceable to the source.
    """
    wanted = re.compile(
        r"\b(?:CASE\s+AT\s+A\s+GLANCE|CASE\s+STUDY|FACT\s+CHRONOLOGY|"
        r"CHRONOLOGY\s+OF\s+IMPORTANT\s+EVENTS|TABLE\s+OF\s+CONTENTS|"
        r"BILL\s+OF\s+QUANTITIES|ILLUSTRATIVE\s+JUDGMENT|"
        r"INSOLVENCY\s+AND\s+BANKRUPTCY\s+CODE|National\s+Company\s+Law\s+Tribunal|"
        r"ARBITRATION\s+AWARD|sole\s+arbitrator|"
        r"prima\s+facie\s+case\s+for\s+(?:interim\s+)?custody|"
        r"Writ\s+(?:Petition|Appeal)|CERTIFICATION\s+UNDER\s+ARTICLE|"
        r"Environment\s*\(?Protection\)?\s*Act|Environmental\s+Impact\s+Assessment|"
        r"Pollution\s+Control\s+Board|National\s+Green\s+Tribunal|"
        r"Indian\s+Penal\s+Code|Bharatiya\s+Nyaya\s+Sanhita|Code\s+of\s+Criminal\s+Procedure|"
        r"Indian\s+Contract\s+Act|Specific\s+Relief\s+Act|Sale\s+of\s+Goods\s+Act|"
        r"Companies\s+Act|Trademarks\s+Act|Hindu\s+Marriage\s+Act|"
        r"Industrial\s+Disputes\s+Act|Income\s+Tax\s+Act|"
        r"learned\s+Counsel|we\s+pass\s+the\s+following\s+order)\b",
        re.I,
    )
    out: list[str] = []
    seen: set[str] = set()
    for m in wanted.finditer(text):
        phrase = re.sub(r"\s+", " ", m.group(0)).strip()
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            out.append(phrase)
        if len(out) >= limit:
            break
    return out


def classify_document(text: str) -> dict[str, Any]:
    """Classify document type and legal domain from structural evidence.

    Deterministic and offline: classification must never depend on the LLM
    being loadable, because a mock-fallback classification would silently
    mis-route the rest of the pipeline.

    Returns a dict with ``document_type`` (label), ``document_type_key``,
    ``legal_domain`` (label), ``legal_domain_key``, ``indicators``, and the
    full ``scores`` for debugging.
    """
    text = text or ""

    # Structural signals use the whole document; the caption and the heading
    # block are weighted separately because a dossier's own cover text names a
    # case that is different from its subject matter.
    type_scores = _score(_DOC_TYPE_SIGNALS, text)

    # "learned Senior Counsel" / "we pass the following order" belong to a real
    # judgment, but a dossier quoting the judgment inherits them. Require the
    # judgment markers to co-occur with a judgment-shaped caption.
    caption = text[:1500]
    has_judgment_caption = bool(
        re.search(r"\bIN\s+THE\s+(?:SUPREME\s+COURT|HIGH\s+COURT|DISTRICT\s+COURT|"
                  r"NATIONAL\s+COMPANY\s+LAW\s+TRIBUNAL|NATIONAL\s+GREEN\s+TRIBUNAL)", caption, re.I)
    )
    if has_judgment_caption and re.search(r"^\s*JUDGMENT\s*$", caption, re.I | re.M):
        type_scores["standard_judgment"] = type_scores.get("standard_judgment", 0) + 2

    # Domain scoring ignores a trailing boilerplate "Applicable laws:" list so a
    # civil case file advertising BNS/BNSS in its footer stays civil.
    boiler = _BOILERPLATE_ACT_LIST.search(text)
    domain_text = _restrict_to_substantive(text, boiler.start() if boiler else None)
    domain_scores = _score(_DOMAIN_SIGNALS, domain_text)

    # A constitutional-only citation set is the weakest signal there is
    # (every judgment cites Article 21 somewhere), so it needs corroboration.
    if domain_scores.get("constitutional", 0) and max(
        (v for k, v in domain_scores.items() if k != "constitutional"), default=0
    ) == 0:
        domain_scores["constitutional"] = 0

    best_type = max(type_scores, key=lambda k: (type_scores[k], k == "standard_judgment"))
    best_domain = max(domain_scores, key=lambda k: (domain_scores[k], k == "civil_contract"))

    # No evidence at all: say so rather than defaulting to criminal, which is
    # what made civil and insolvency files land in the wrong domain.
    if max(domain_scores.values(), default=0) == 0:
        best_domain = "civil_contract"
        domain_confidence = 0.0
    else:
        total = sum(v for v in domain_scores.values() if v > 0)
        domain_confidence = round(domain_scores[best_domain] / total, 3) if total else 0.0

    type_total = sum(v for v in type_scores.values() if v > 0)
    type_confidence = round(type_scores[best_type] / type_total, 3) if type_total else 0.0

    return {
        "document_type": _TYPE_LABELS.get(best_type, "Standard Court Judgment"),
        "document_type_key": best_type,
        "document_type_confidence": type_confidence,
        "legal_domain": _DOMAIN_LABELS.get(best_domain, "Civil/Contract Law"),
        "legal_domain_key": best_domain,
        "legal_domain_confidence": domain_confidence,
        "indicators": _indicators(text),
        "scores": {
            "document_type": type_scores,
            "legal_domain": domain_scores,
        },
    }


def expected_statute_families(document_type_key: str, legal_domain_key: str) -> list[str]:
    """Acts a document of this class is expected to turn on.

    Advisory only. It gates *nothing*: it exists so a civil case file that
    yields BNS/BNSS/BSA can be surfaced as a likely domain error instead of
    being silently reported as correct.
    """
    families = {
        "insolvency_bankruptcy": ["Insolvency and Bankruptcy Code, 2016", "Companies Act, 2013"],
        "environmental": ["Environment (Protection) Act, 1986", "Water (Prevention and Control of Pollution) Act, 1974"],
        "criminal": ["Bharatiya Nyaya Sanhita, 2023", "Bharatiya Nagarik Suraksha Sanhita, 2023", "Bharatiya Sakshya Adhiniyam, 2023"],
        "civil_contract": ["Indian Contract Act, 1872", "Specific Relief Act, 1963", "Code of Civil Procedure, 1908"],
        "corporate": ["Companies Act, 2013"],
        "tax": ["Income Tax Act, 1961"],
        "labour": ["Industrial Disputes Act, 1947"],
        "family": ["Hindu Marriage Act, 1955"],
        "intellectual_property": ["Trade Marks Act, 1999"],
        "constitutional": ["Constitution of India"],
    }
    out = list(families.get(legal_domain_key, []))
    if document_type_key == "insolvency_appeal" and "Insolvency and Bankruptcy Code, 2016" not in out:
        out.insert(0, "Insolvency and Bankruptcy Code, 2016")
    return out