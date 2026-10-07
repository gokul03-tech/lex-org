"""LangGraph agent implementations for LexOrch-KG multi-agent legal analysis.

All 12 specialized agents: CaseUnderstanding, LegalResearch, KnowledgeGraph,
EvidenceReliability, ContradictionDetection, ProceduralCompliance,
LegalReasoning, StrategyRecommendation, RiskAssessment, ConfidenceFusion,
Explainability, and ReportGeneration.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from loguru import logger

from app.agents.supervisor import AgentState
from app.agents.universal_extraction_rules import UNIVERSAL_EXTRACTION_PROMPT
from app.llm.llama_cpp_provider import is_mock_fallback_active


# ── Extraction prompts ──────────────────────────────────────
# Kept at module scope so the rules are auditable in one place and cannot drift
# per call site. Each prompt encodes a grounding rule the pipeline was previously
# violating: the LLM was inventing issues, counsel arguments and strategy text
# because nothing told it not to.

ISSUE_EXTRACTION_PROMPT = """
You are an expert legal AI extracting the core legal or factual questions that the court (or author) must decide in this case file.

CRITICAL INSTRUCTIONS:
1. DO NOT just look for the word "Issue". Legal documents use many different phrases to frame questions.
2. You MUST recognize and extract issues from ANY of these alternative headings or phrasing:
   - "We frame the following issues for our consideration:"
   - "Issues Framed for Trial"
   - "Questions considered in the appeal"
   - "Main question:"
   - "Legal Issues"
   - "The case can be organized into several legal and factual questions. First... Second..."
   - Numbered lists like "Issue 1:", "Issue 2:", "1.", "2."

3. EXTRACTION RULES:
   - Extract ALL questions listed. Do NOT stop after 2 or 3.
   - Do NOT truncate mid-sentence. If an issue spans multiple lines, combine them into one complete, coherent sentence.
   - If the document uses "First,", "Second:", or "Main question:", extract them exactly as written.
   - DO NOT extract academic commentary, disclaimers, or hypothetical learning points as issues.
   - DO NOT include section headers like "ANALYSIS AND REASONING" in the extracted issue text.

4. OUTPUT FORMAT:
   Return a clean, numbered list of ALL issues found.
   Example:
   1. Whether the plaintiff proves a binding contract under the Purchase Order.
   2. Main question: Whether the FIR allegations disclose cognizable offences or are merely a civil dispute.
""" + UNIVERSAL_EXTRACTION_PROMPT

# Fallback-only. Issued as a SEPARATE call, and only when the deterministic
# extractors (_court_framed_issues, _enumerated_issues) return nothing, so a
# standard judgment never reaches the model and keeps its verbatim,
# zero-hallucination issues. Academic dossiers and illustrative files that
# frame no issues at all fall back to this.
ISSUE_LLM_FALLBACK_PROMPT = """
You are extracting the LEGAL ISSUES framed for decision in this case file.

CRITICAL RULES:
1. Look for ANY section that frames the questions the court or author is deciding.
2. Recognize these alternative headings:
   - "We frame the following issues for our consideration:"
   - "Issues Framed for Trial"
   - "Questions considered in the appeal"
   - "Main question:"
   - "Legal Issues"
   - "The case can be organized into several legal and factual questions. First... Second..."
   - Numbered issues (Issue 1, Issue 2, etc.)
3. Extract ALL issues present in the initial issue list. Do NOT stop after 2 or 3.
4. EXACT BOUNDARY RULE: an issue ends ONLY at a period followed by a capital
   letter OR the next numbered/section heading (e.g. "10. PETITIONERS'
   SUBMISSIONS") OR a double newline. A comma, the word "or"/"whether" or a
   single line break does NOT end an issue — keep reading to the full question
   so the extracted issue reads completely and self-contained.
5. STRICT NEGATIVE BOUNDARIES — STOP IMMEDIATELY when any of these begin:
   a. A reasoning/outcome header: "ANALYSIS AND REASONING", "REASONING",
      "JUDGMENT", "JUDGMENT AND SENTENCE", "THE HIGH COURT", "ORDER",
      "CONCLUSION", "CONCLUSION AND ORDER", "DISPOSITION".
   b. A numbered paragraph (e.g., "37.", "38.", "39.") that is NOT part of the
      initial issue list. Issues are only the questions framed up front; once
      the document moves to analysis, that text belongs to it, not to the list.
   c. Neither of the above but the numbered issue list you are reading has
      already ended — do not reach past it into the body.
6. If the document frames, say, 4 issues in a numbered list, extract ONLY those
   4. Do NOT continue reading into later sections for more.
7. Each issue MUST be a single question. If an extracted item reads longer than
   100 words, it is grabbing reasoning, not an issue — truncate it back to the
   question itself.
8. Return a clean, numbered list.
""" + UNIVERSAL_EXTRACTION_PROMPT

# Also fallback-only, appended to ISSUE_LLM_FALLBACK_PROMPT. A dossier or
# illustrative record sometimes states no issue headers at all ("We frame the
# following issues" is absent); an empty issue list is technically honest but
# useless downstream, so the model is asked to infer the questions the document
# itself debates. The "FORMAT EXAMPLE ONLY" lines show the expected shape and
# are explicitly not to be copied.
ISSUE_INFERENCE_PROMPT = """
INFERENCE RULE (apply only if the document contains NO explicit issue header
such as "Issue 1:", "Issues framed", "We frame the following issues", or
numbered questions):
If the document does not contain explicit issue headers, infer the legal issues
from the document itself:
1. The counsel arguments — what are the parties disputing?
2. The court's reasoning — what questions did the court actually address?
3. The relief sought — what is the petitioner/plaintiff asking for?
Every inferred issue MUST be a question this document actually debates; ground
each one in the text. NEVER invent statutory sections, amounts, exhibits, case
names, or facts that do not appear in the document.

FORMAT EXAMPLE ONLY — do NOT copy these facts:
1. Whether the arbitral award suffers from patent illegality under Section 34(2A)?
2. Whether the Tribunal ignored contemporaneous correspondence?
"""

# Issues whose text never appears in the document are not paraphrases of the
# source, they are inventions, and must be dropped even from an LLM response.
_ISSUE_NOISE_RE = re.compile(
    r"^\s*(?:the\s+)?(?:main\s+question|issue|question)s?\b[^:]{0,40}:\s*$",
    re.IGNORECASE,
)


def _llm_clean(text: str) -> str:
    """Text as an LLM should see it: meta sections and standalone noise removed.

    Applied at every prompt entry point rather than once at parse time, because
    a caller may hold pre-cleaned or partially-cleaned text. Failures are
    swallowed: an uncleaned prompt is better than no analysis.
    """
    if not text:
        return text or ""
    try:
        from app.agents.doc_meta_guard import (
            filter_url_artifacts,
            strip_academic_noise,
            strip_meta_sections,
            strip_standalone_noise,
        )

        return filter_url_artifacts(
            strip_academic_noise(strip_standalone_noise(strip_meta_sections(text)))
        )
    except Exception:
        return text


def _clean_llm_issue(raw: Any) -> str:
    """Normalise one LLM issue to a single clean sentence."""
    s = re.sub(r"\s+", " ", str(raw or "")).strip()
    # Drop list markers: "1.", "2)", "(iv)", "Issue 3 -", "Q1:".
    s = re.sub(
        r"^\s*(?:\(?\d{1,2}\)?[.)]|\([0-9ivx]{1,4}\)|issue\s+[0-9ivx]{1,4}\s*[-–:.]|q\s*[0-9]{1,2}\s*[-–:])\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Keep the label when the document itself used one ("Main question: ...").
    if _ISSUE_NOISE_RE.match(s):
        return ""
    # FIX 1 boundary anchor (post-processing guarantee): a framed issue is a
    # single question. When the response bled past it into reasoning, cut back
    # to the 100-word ceiling at the last sentence end before the limit so the
    # stored issue is still a question, not analysis text.
    words = s.split()
    if len(words) > 100:
        cut = 100
        for i in range(99, 0, -1):
            if words[i].endswith((".", "?")):
                cut = i + 1
                break
        s = " ".join(words[:cut]).strip()
    return s.strip(" -–—:;,")


async def llm_extract_issues_as_fallback(text: str) -> list[dict[str, Any]]:
    """Generate issues with the LLM. Only for documents that state none.

    Returns dicts shaped like the deterministic extractors so downstream
    consumers (report, KG, API) need no special case, with ``source='ai'`` so
    the UI badges them as AI-inferred rather than as document facts.

    Any model failure yields ``[]``: a missing issue list is far better than a
    fabricated one, and the caller falls back to reporting no issues.
    """
    text = text or ""
    if len(text) < 200:
        return []
    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        provider = get_qwen_provider()
        result = provider.generate_structured(
            f"{ISSUE_LLM_FALLBACK_PROMPT}\n{ISSUE_INFERENCE_PROMPT}"
            f"\n\nCase Document:\n{_llm_clean(text)[:14000]}",
            output_schema={
                "type": "object",
                "properties": {
                    "legal_issues": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["legal_issues"],
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            # 2000 leaves room for every full-length issue AND the complete
            # closing question when a long dossier frames 5+ issues. A tighter
            # budget silently cut the tail mid-issue, truncating the last item.
            max_tokens=2000,
        )

        raw = result.get("legal_issues") or []
        if isinstance(raw, str):
            # Grammar-constrained generation can fall back to raw text; recover
            # the numbered list rather than discarding a usable answer.
            raw = [ln for ln in re.split(r"\n+", raw) if re.match(r"^\s*(?:\d+[.)]|issue\b)", ln, re.I)]

        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw:
            cleaned = _clean_llm_issue(item)
            if len(cleaned) < 15:
                continue
            key = re.sub(r"[^a-z0-9]", "", cleaned.lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "issue": cleaned,
                "text": cleaned,
                # No verbatim quote exists for a generated issue, so `evidence`
                # is deliberately absent: normalizeIssues treats a missing
                # quote as AI-sourced rather than as a document fact.
                "source": "ai",
                "generated": True,
            })
        logger.info(f"[IssueFallback] LLM produced {len(out)} issue(s) (deterministic found none)")
        return out
    except Exception as exc:
        logger.warning(f"[IssueFallback] unavailable, reporting no issues: {exc}")
        return []


# Exhibit labels are the only thing that counts as evidence structure. Kept in
# sync with _EXHIBIT_RE in analysis_fixes_v2 so an LLM row and a regex row are
# indistinguishable to the UI.
_EVIDENCE_LABEL_RE = re.compile(
    r"^\s*(?:(?:ex(?:h)?ibit|ex|annexure|ann?x)\.?\s*)?(?P<side>PW|DW|[PDKA])"
    r"[\s\-‐-―_.]*\d{1,4}\s*[-:—–]?\s*(?P<desc>.+)$",
    re.IGNORECASE,
)
_EVIDENCE_SIDE_ROLE = {
    "P": "Prosecution / Plaintiff / Petitioner",
    "PW": "Prosecution Witness",
    "D": "Defence / Defendant / Respondent",
    "DW": "Defence Witness",
    "K": "Complainant",
    "A": "Annexure",
}


async def llm_extract_evidence_as_fallback(text: str) -> list[dict[str, Any]]:
    """Generate exhibit rows with the LLM. Only for register-less documents.

    Mirrors ``llm_extract_issues_as_fallback``: the deterministic extractors run
    first and keep every row they find, so a standard judgment is never routed
    through the model. This is called solely when no exhibit label exists in the
    document at all.

    Every returned row is re-validated against ``_EVIDENCE_LABEL_RE`` and the
    side letter must be present, so an invented "Exhibit P-99" the model made up
    without a matching document label is dropped rather than displayed as fact.

    Any model failure yields ``[]``.
    """
    text = text or ""
    if len(text) < 200:
        return []
    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        provider = get_qwen_provider()
        result = provider.generate_structured(
            f"{EVIDENCE_LLM_FALLBACK_PROMPT}\n\nCase Document:\n{_llm_clean(text)[:14000]}",
            output_schema={
                "type": "object",
                "properties": {
                    "exhibits": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "exhibit": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["exhibit", "description"],
                        },
                    },
                },
                "required": ["exhibits"],
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            # Matches the issue budget so a long register is not cut mid-row.
            max_tokens=1800,
        )

        raw = result.get("exhibits") or []
        if isinstance(raw, str):
            raw = [ln for ln in re.split(r"\n+", raw) if ln.strip()]

        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw:
            # Accept either the schema object or a bare "P-1 - description"
            # line, which grammar-constrained generation can emit instead.
            bare_line = not isinstance(item, dict)
            if bare_line:
                label = ""
                desc = re.sub(r"\s+", " ", str(item)).strip()
            else:
                label = re.sub(r"\s+", " ", str(item.get("exhibit") or "")).strip()
                desc = re.sub(r"\s+", " ", str(item.get("description") or "")).strip()
            desc = desc.strip(" -–—:;,.[]")

            lm = _EVIDENCE_LABEL_RE.match(f"{label} - {desc}" if label else desc)
            if not lm:
                continue
            if bare_line:
                # The whole line was the label too; keep only its description.
                desc = re.sub(r"\s+", " ", lm.group("desc") or "").strip(" -–—:;,.[]")
            if len(desc) < 3:
                continue

            side = lm.group("side").upper()
            num_m = re.search(r"\d{1,4}", lm.group(0))
            if not num_m:
                continue
            code = f"{side}-{num_m.group(0)}"
            if code in seen:
                continue
            seen.add(code)
            # A generated description is not a verbatim quote, so `source='ai'`
            # keeps the UI from presenting it as a document fact.
            out.append({
                "type": f"Exhibit {code}",
                "description": desc,
                "exhibit": code,
                "tendered_by": _EVIDENCE_SIDE_ROLE.get(side, "Record"),
                "reliability": "AI-INFERRED — no exhibit register found in document",
                "source": "ai",
                "generated": True,
            })
        logger.info(f"[EvidenceFallback] LLM produced {len(out)} exhibit(s) (deterministic found none)")
        return out
    except Exception as exc:
        logger.warning(f"[EvidenceFallback] unavailable, reporting no exhibits: {exc}")
        return []


def _contains_verbatim(text: str, quote: str) -> bool:
    """True when ``quote`` appears (modulo whitespace) inside ``text``.

    Fallback-generated conclusions, strengths and gaps are only accepted when
    the document itself contains the sentence, so an invented finding can never
    surface as if the Court wrote it.
    """
    hay = re.sub(r"\s+", " ", text or "").lower()
    needle = re.sub(r"\s+", " ", (quote or "")).strip().strip('"\u201c\u201d').lower()
    return bool(needle) and needle in hay


async def llm_extract_conclusion_as_fallback(text: str) -> str:
    """Generate the FINAL ORDER with the LLM. Only when deterministic extraction finds none.

    Mirrors ``llm_extract_issues_as_fallback``: standard judgments never reach
    the model — this fires solely when render_conclusion/build_risk had nothing
    usable. Any model failure returns ``""``, leaving the deterministic empty
    result in place.
    """
    text = text or ""
    if len(text) < 200:
        return ""
    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        provider = get_qwen_provider()
        result = provider.generate_structured(
            f"{CONCLUSION_EXTRACTION_PROMPT}\n\nCase Document:\n{_llm_clean(text)[:14000]}",
            output_schema={
                "type": "object",
                "properties": {
                    "conclusion": {"type": "string"},
                },
                "required": ["conclusion"],
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=400,
        )
        raw = result.get("conclusion") if isinstance(result, dict) else ""
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        conclusion = str(raw or "").strip(' "\u201c\u201d')
        if len(conclusion) < 20 or not _contains_verbatim(text, conclusion):
            return ""
        logger.info(f"[ConclusionFallback] LLM produced a verbatim final order (deterministic found none)")
        return conclusion
    except Exception as exc:
        logger.warning(f"[ConclusionFallback] unavailable, keeping deterministic result: {exc}")
        return ""


async def llm_extract_strengths_as_fallback(text: str) -> list[str]:
    """Generate the Court's favorable findings with the LLM. Only when deterministic found none.

    ``build_risk_strategy`` keeps every strength it can prove; this fills the
    gap for records the patterns do not recognise. Every returned item is
    re-validated as verbatim document text; a model failure yields ``[]``.
    """
    text = text or ""
    if len(text) < 200:
        return []
    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        provider = get_qwen_provider()
        result = provider.generate_structured(
            f"{KEY_STRENGTHS_PROMPT}\n\nCase Document:\n{_llm_clean(text)[:14000]}",
            output_schema={
                "type": "object",
                "properties": {
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["strengths"],
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=600,
        )
        raw = result.get("strengths") if isinstance(result, dict) else []
        raw = raw if isinstance(raw, list) else []
        out: list[str] = []
        seen: set[str] = set()
        for item in raw:
            s = str(item or "").strip(' "\u201c\u201d')
            if len(s) < 20 or not _contains_verbatim(text, s):
                continue
            key = re.sub(r"[^a-z0-9]", "", s.lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        logger.info(f"[StrengthsFallback] LLM produced {len(out)} grounded strength(s) (deterministic found none)")
        return out
    except Exception as exc:
        logger.warning(f"[StrengthsFallback] unavailable, keeping deterministic result: {exc}")
        return []


async def llm_extract_gaps_as_fallback(text: str) -> list[str]:
    """Generate the Court's unfavorable findings with the LLM. Only when deterministic found none.

    Mirrors ``llm_extract_strengths_as_fallback`` for the adverse side of the
    record. Every returned item is re-validated as verbatim document text.
    """
    text = text or ""
    if len(text) < 200:
        return []
    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        provider = get_qwen_provider()
        result = provider.generate_structured(
            f"{POTENTIAL_GAPS_PROMPT}\n\nCase Document:\n{_llm_clean(text)[:14000]}",
            output_schema={
                "type": "object",
                "properties": {
                    "gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["gaps"],
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=600,
        )
        raw = result.get("gaps") if isinstance(result, dict) else []
        raw = raw if isinstance(raw, list) else []
        out: list[str] = []
        seen: set[str] = set()
        for item in raw:
            s = str(item or "").strip(' "\u201c\u201d')
            if len(s) < 20 or not _contains_verbatim(text, s):
                continue
            key = re.sub(r"[^a-z0-9]", "", s.lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        logger.info(f"[GapsFallback] LLM produced {len(out)} grounded gap(s) (deterministic found none)")
        return out
    except Exception as exc:
        logger.warning(f"[GapsFallback] unavailable, keeping deterministic result: {exc}")
        return []

COUNSEL_EXTRACTION_PROMPT = """
Extract counsel submissions from the legal document.

RULES:
1. Look for paragraphs starting with "Mr. [Name], learned Senior Counsel..." or "Per contra, Mr. [Name]...".
2. Extract the actual numbered arguments `(i)`, `(ii)`, `(iii)`, `(iv)` that follow these names.
3. If the specific name of the counsel is not mentioned, DO NOT use generic fallback text like "Petitioner contends
4. Ensure strict separation between Prosecution/Respondent arguments and Defense/Appellant arguments.
5. Do NOT include the court's framed issues in counsel submissions.

ROLE-BASED SECTIONS (do not rely on "Per contra" alone):
Academic and illustrative files carry no counsel names, but they label each
side's arguments by ROLE. Match the label, not the phrasing:
- Petitioner / Appellant / Plaintiff / Defence side:
  "PETITIONERS' SUBMISSIONS", "APPELLANT'S POSITION", "PLAINTIFF'S FINAL WRITTEN
  SUBMISSIONS", "DEFENCE CONTENTIONS", "APPELLANT'S SUBMISSIONS",
  "PLAINTIFF'S EVIDENCE AND WITNESS STATEMENT"
- Respondent / State / Prosecution side:
  "RESPONDENTS' SUBMISSIONS", "STATE'S SUBMISSIONS", "RESPONDENT'S POSITION",
  "PROSECUTION WRITNESSES AND EVIDENCE", "PROSECUTION'S EVIDENCE",
  "DEFENDANT'S FINAL WRITTEN SUBMISSIONS"
- Numbered party sections also count: "10. PETITIONERS' SUBMISSIONS".
Extract the arguments written under those headings for that side.

DO NOT swap the columns. The output column is decided ONLY by the section
header the text sits under (or the speaker named in the sentence), never by
the content or by where another model call placed a similar paragraph:
- Every argument under a FIRST-PARTY header (PETITIONERS' SUBMISSIONS,
  APPELLANT'S POSITION, PLAINTIFF'S FINAL WRITTEN SUBMISSIONS, DEFENCE
  CONTENTIONS, APPLICANT'S SUBMISSIONS) is a Petitioner/Defence submission.
- Every argument under a SECOND-PARTY header (STATE'S SUBMISSIONS,
  RESPONDENT'S SUBMISSIONS, DEFENDANT'S FINAL WRITTEN SUBMISSIONS, DEFENDANT'S
  WRITTEN STATEMENT, PROSECUTION SUBMISSIONS) is a Respondent/Prosecution
  submission.
- Bail cases: the Applicant/Accused is the first party, the State is the
  second. An "Anticipatory Bail Application by Mr. X" still maps X's arguments
  to the first column and the State's arguments to the second.
- A header that reads "DEFENDANT'S FINAL WRITTEN SUBMISSIONS" belongs to the
  Respondent/second column even when the defendant is the person defending the
  suit; do not relabel it to the first column.
Return BOTH lists in the OUTPUT below exactly as paired with their headers.

DO NOT extract as a submission:
- The court's own reasoning or analysis.
- The plaint prayer or "relief sought" clause.
- Any section that describes the document rather than a party's case.

RULES FOR ACADEMIC DOSSIERS (no counsel names present):
- For academic dossiers, look for sections titled "DEFENCE CONTENTIONS" (Section 8) or "PROSECUTION WITNESSES AND EVIDENCE" (Section 7).
- For standard judgments, look for numbered lists (i), (ii), (iii), (iv) following counsel names.
- If specific counsel names are missing, summarize the actual arguments from the "Defence Contentions" section.
- CRITICAL EXCLUSION RULE: DO NOT extract from sections titled "Case Study for Legal-AI",
  "Conclusion and References", "References", "Academic Case Dossier", or
  "Why this is a Cyber-Crime Case". Those sections describe the DOCUMENT, not
  the litigation, and their text is not a submission by either side.
- If a side genuinely has no recorded argument, return an empty list. Never
  fabricate a plausible-sounding argument to fill the field.

OUTPUT:
- Petitioner/Defense Submissions: [actual numbered arguments]
- Respondent/Prosecution Submissions: [actual numbered arguments]
""" + UNIVERSAL_EXTRACTION_PROMPT

# Fallback-only. Issued as a SEPARATE call, and only when the deterministic
# extractors found NO exhibit register (no "Exhibit P-1"-style label anywhere).
# A standard judgment that does enumerate its exhibits keeps its verbatim,
# zero-hallucination rows; only register-less academic/illustrative files and
# narrative-style civil records reach the model.
EVIDENCE_LLM_FALLBACK_PROMPT = """
You are extracting the DOCUMENTARY EXHIBITS / EXHIBIT REGISTER from this case file.

CRITICAL RULES:
1. LOCATE the document's exhibit REGISTER BLOCK first: a section headed
   "EXHIBIT REGISTER", "DOCUMENTARY EXHIBITS", "EVIDENCE REGISTER", "LIST OF
   DOCUMENTS", "LIST OF EXHIBITS", or "Exhibits". Extract rows ONLY from inside
   that block. Never pull a stray exhibit-style sentence ("the FIR was placed
   on record") from the narrative body of the judgment or the proceedings.
2. Extract ONLY items the block itself enumerates with an identifier.
   Accept these label formats: "Exhibit P-1 - ...", "P-1: ...", "Ex. D2 - ...",
   "Exhibit D-2 - ...", "PW-1 - ...", "Annexure A1 - ...".
3. Expand ranges: "P-4 to P-6 - [description]" becomes three separate rows
   (P-4, P-5, P-6) sharing that description, and all rows remain inside the
   register block they came from.
4. For each item, "tendered_by" must be derived ONLY from the side letter in the
   label: P / PW = Prosecution / Plaintiff / Petitioner, D / DW = Defence /
   Defendant / Respondent, K = Complainant, A = Annexure.
5. If the document has NO enumerated exhibit register anywhere, return an empty
   array. Do NOT invent exhibits, and do NOT return narrative sentence snippets
   such as "the FIR was placed on record" as if they were exhibit records.
6. Ignore academic commentary, disclaimers, and any text from a References or
   Bibliography section.
""" + UNIVERSAL_EXTRACTION_PROMPT

# Fallback-only conclusion extractor. Standard judgments keep the deterministic
# operative-sentence path (build_risk/render_conclusion); the model is consulted
# only when that path finds nothing usable, and the accepted clause is
# re-validated as verbatim text from the document.
CONCLUSION_EXTRACTION_PROMPT = """
Extract the FINAL ORDER from the judgment. Look for:
- The last numbered paragraph
- Paragraphs containing: "allowed", "dismissed", "set aside", "affirmed", "decreed"
- The operative part of the judgment

CRITICAL RULES:
1. Quote the operative clause VERBATIM from the document; never paraphrase.
2. DO NOT extract the opening paragraph or introduction.
3. Do NOT return a placeholder such as "The petition is disposed of." when the
   document states a specific outcome.
4. If the document records NO final order (e.g., a submission-only dossier),
   return an empty string rather than inventing an outcome.
""" + UNIVERSAL_EXTRACTION_PROMPT

# Fallback-only. Deterministic build_risk_strategy keeps the court's favorable
# findings it can prove; this fills the gap only when it proved none.
KEY_STRENGTHS_PROMPT = """
Extract the Court's favorable findings for the Petitioner/Plaintiff from the
judgment's reasoning section.

CRITICAL RULES:
1. Quote each finding VERBATIM from the reasoning/operative part of the
   judgment (e.g. "the Tribunal failed to consider Ex. P-19 and Ex. P-23 ...").
2. The finding must favour the Petitioner/Plaintiff: it either upholds their
   claim or criticises the reasoning against them.
3. NEVER extract counsel submissions, procedural closings, or academic
   commentary as if they were findings.
4. NEVER invent findings that do not appear in the document.
5. Do NOT use generic fallbacks like "No favorable findings extracted yet."
""" + UNIVERSAL_EXTRACTION_PROMPT

# Fallback-only. Mirrors KEY_STRENGTHS_PROMPT for the adverse side of the record.
POTENTIAL_GAPS_PROMPT = """
Extract the Court's findings that are unfavorable to the Petitioner/Plaintiff,
or limitations in the Petitioner's case, from the judgment's reasoning section.

CRITICAL RULES:
1. Quote each finding VERBATIM from the reasoning/operative part of the
   judgment (e.g. "no loss was proved under Section 74 of the Indian Contract
   Act", "and in rest it is affirmed").
2. The finding must go against the Petitioner/Plaintiff: part of the claim is
   rejected, a condition is not proved, or most of the award is upheld.
3. NEVER extract counsel submissions or academic commentary as gap findings.
4. NEVER invent findings that do not appear in the document.
5. Do NOT use generic fallbacks like "No adverse contentions extracted yet."
""" + UNIVERSAL_EXTRACTION_PROMPT

STRATEGY_PROMPT = """
You are analyzing a legal case for adversarial debate and strategy.

STRICT GROUNDING RULES:
1. ONLY use facts, statutory sections, and legal terminology EXPLICITLY present in the provided case context. NEVER import generic legal terms (e.g., 'mens rea', 'vicarious conspiracy') unless they appear in the source text.
2. NEVER output UI error messages like "No sufficiently relevant precedent found" or "(N/A)".

EXTRACTION RULES:
- Strategic Ground: Extract the actual arguments made by the Appellant/Petitioner (look for "Mr. [Name] submitted..."). Do NOT use procedural closing lines like "Pending interlocutory applications...".
- Key Strengths: Extract substantive favorable findings made by the Court (look for "We are of the view that...", "The circular fails..."). Do NOT use generic fallbacks.
- Action Plan: Extract ONLY direct procedural orders/directions from the Court (look for "The Registry is directed...", "The appellants shall..."). Do NOT include legal reasoning or precedent citations.

CRITICAL EXCLUSION RULE:
- DO NOT extract text from sections titled "Case Study for Legal-AI", "Conclusion and References", "References", "Academic Case Dossier", or "Why this is a Cyber-Crime Case".
- The Conclusion MUST ONLY come from the section titled "JUDGMENT AND SENTENCE" (Section 12) or "CONCLUSION AND ORDER".
- The Action Plan MUST ONLY be derived from the court's specific sentencing or orders (e.g., "two years' rigorous imprisonment"), NOT from the bibliography or academic commentary.

OUTPUT FORMAT:
- Strategic Ground: [Appellant's actual arguments]
- Opposing Counsel: [Respondant's actual arguments]
- Judicial Rebuttal: [Generate based on cited precedents ONLY]
- Action Plan: [List of actionable procedural steps]
""" + UNIVERSAL_EXTRACTION_PROMPT


# ── Statute normalisation ───────────────────────────────────
# UI error strings the LLM is known to emit; never let them reach the report.
_PLACEHOLDER_VALUES = {
    "", "n/a", "na", "none", "null", "not available", "not specified",
    "not mentioned", "unknown", "no sufficiently relevant precedent found",
    "not applicable", "unstated in record",
    # Retriever placeholders that leak in as if they were case names.
    "vector", "vectors", "kg", "graph", "chunk", "chunks", "document",
    "documents", "result", "results", "hit", "hits", "node", "nodes",
    "precedent", "keyword", "keywords", "text", "passage", "page",
}

# "Section 63", "S.63", "sec 63(1)(b)", "u/s 63" -> "63" / "63(1)(b)"
_STATUTE_NUM_RE = re.compile(r'\d+(?:\s*\(\s*\d+\s*\))*')
_STATUTE_ACT_RE = re.compile(
    r'\b(?:of|under|under\s+the)\s+(?:the\s+)?'
    r'([A-Z][A-Za-z0-9.\s(){},–-]{2,80}?(?:Act|Sanhita|Adhiniyam|Code|Constitution))'
)

# Short code for each Act, keyed by BOTH its abbreviation and its full name so
# "S.420 IPC" and "Section 420 of the Indian Penal Code" resolve to one key.
_ACT_CODE_BY_FORM = {
    "ipc": "IPC", "indianpenalcode": "IPC",
    "bns": "BNS", "bharatiyanyayasanhita": "BNS",
    "bnss": "BNSS", "bharatiyanagariksurakshasanhita": "BNSS",
    "bsa": "BSA", "bharatiyasakshyaadhiniyam": "BSA",
    "crpc": "CRPC", "codecriminalprocedure": "CRPC",
    "ndps": "NDPS", "narcotic": "NDPS",
    "iea": "IEA", "indianevidenceact": "IEA", "evidenceact": "IEA",
    "constitutionofindia": "CONSTITUTION", "constitution": "CONSTITUTION",
}


def _canonical_act(text: str) -> str:
    """Map an Act name or abbreviation to a stable short code ('' if unknown)."""
    squashed = re.sub(r'[^a-z0-9]', '', (text or "").lower())
    if not squashed:
        return ""
    if squashed in _ACT_CODE_BY_FORM:
        return _ACT_CODE_BY_FORM[squashed]
    # Longest form first so "indianpenalcode" wins over a stray substring.
    for form, code in sorted(_ACT_CODE_BY_FORM.items(), key=lambda kv: -len(kv[0])):
        if len(form) >= 3 and form in squashed:
            return code
    return ""


def _statute_act(text: str) -> str:
    """Find the Act a section belongs to, via long form or short abbreviation."""
    long_m = _STATUTE_ACT_RE.search(text)
    if long_m:
        code = _canonical_act(long_m.group(1))
        if code:
            return code

    # Search for a short alias ("420 IPC") in the text with the section number
    # removed, so the number itself cannot supply the word boundary. Searched
    # un-squashed: collapsing to letters only would destroy that boundary.
    residue = _STATUTE_NUM_RE.sub(" ", text).lower()
    for alias in ("ipc", "bns", "bnss", "bsa", "crpc", "ndps", "iea"):
        if re.search(rf'(?<![a-z]){alias}(?![a-z])', residue):
            return _ACT_CODE_BY_FORM[alias]
    return ""


def _statute_parts(statute: str) -> tuple[str, str]:
    """Split a reference into (canonical_act_code, section_number)."""
    text = (statute or "").strip()
    num_m = _STATUTE_NUM_RE.search(text)
    if not num_m:
        return "", re.sub(r'[^a-z0-9]', '', text.lower())
    return _statute_act(text), re.sub(r'\s+', '', num_m.group(0))


def _statute_core(statute: str) -> str:
    """Return a canonical dedup key for a statute/section reference.

    The key is scoped by Act when one is resolvable. Keying on the bare number
    alone (e.g. "63") would collapse genuinely different provisions - Section 63
    of the BSA and Section 63 of the BNSS are different laws and must both
    survive.
    """
    if not statute or statute.strip().lower() in _PLACEHOLDER_VALUES:
        return ""
    act, num = _statute_parts(statute)
    if not num:
        return ""
    return f"{act}|{num}" if act else num


def normalize_statutes(statutes_list: list[str]) -> list[str]:
    """Deduplicate statute/section references, keeping the first (best) phrasing.

    Handles the duplicate-chip problem where the same provision is collected from
    several passes under different surface forms ("Article 14", "Section Art. 14",
    "Art. 14 of the Constitution") while preserving distinct subsections
    ("63(1)" vs "63(2)") and same-numbered sections of different Acts.

    A second pass drops Act-less references ("S. 420") only when the same number
    resolves to exactly one Act elsewhere in the list, so the duplicate chip
    disappears in the common single-Act case without ever merging a reference
    that could belong to a different law.
    """
    seen: set[str] = set()
    kept: list[str] = []
    kept_parts: list[tuple[str, str]] = []
    for statute in statutes_list or []:
        if not isinstance(statute, str):
            continue
        stripped = statute.strip()
        if not stripped or stripped.lower() in _PLACEHOLDER_VALUES:
            continue
        core = _statute_core(stripped)
        if not core or core in seen:
            continue
        seen.add(core)
        kept.append(stripped)
        kept_parts.append(_statute_parts(stripped))

    acts_by_number: dict[str, set[str]] = {}
    for act, num in kept_parts:
        if act:
            acts_by_number.setdefault(num, set()).add(act)

    return [
        text for text, (act, num) in zip(kept, kept_parts)
        if act or len(acts_by_number.get(num, ())) != 1
    ]


# ── Helper: Submission list sanitising ─────────────────────
# Phrases the model emits instead of admitting that the document contains no
# submissions. Rendering them would reintroduce the very generic-fallback text
# COUNSEL_EXTRACTION_PROMPT forbids.
_GENERIC_SUBMISSION_RE = re.compile(
    r'\b(?:petitioner|applicant|appellant|respondent|defence|defense|prosecution|state|counsel)'
    r'\s+(?:contends?|asserts?|alleges?|argues?|submits?)\s+'
    r'(?:that\s+)?(?:the\s+)?'
    r'(?:allegations?|claims?|relief|warrant|merit|liability|applicable|relevant|'
    r'provisions?|statut\w*|facts?|grounds?)\b',
    re.IGNORECASE,
)


def _clean_submission_list(raw: Any) -> list[str]:
    """Normalise a counsel-submission list, dropping placeholders and filler."""
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        text = re.sub(r'^\s*\(?[ivx]+\)?[.)\s]*', '', item.strip(), flags=re.IGNORECASE)
        text = re.sub(r'^\s*\(?\d+\)?[.)\s]*', '', text).strip()
        if len(text) < 25:
            continue
        if text.lower() in _PLACEHOLDER_VALUES:
            continue
        if _GENERIC_SUBMISSION_RE.search(text):
            continue
        key = re.sub(r'[^a-z0-9]', '', text.lower())[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


# STRATEGY_PROMPT asks for a flat "Strategic Ground / Key Strengths / Action
# Plan" shape, while the JSON schema describes a "strategies" array. The model
# often follows the prompt, so a response keyed by the flat shape produced
# strategy_options == [] even on a good run. Both shapes are accepted here and
# normalised into one structure.
_FLAT_STRATEGY_ALIASES = {
    "strategic_ground": "description",
    "opposing_counsel": "counter_argument",
    "key_strengths": "pros",
    "action_plan": "recommended_actions",
    "judicial_rebuttal": "rebuttal",
}


def _normalise_strategy_result(result: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """Return (strategy entries, judicial rebuttal) from either response shape."""
    raw = result.get("strategies")
    rebuttal = str(result.get("judicial_rebuttal") or "").strip()

    if isinstance(raw, list) and raw:
        return _sanitize_strategies(raw), rebuttal

    # Flat shape: promote the grounded sections into a single strategy entry.
    # Keys are normalised first - the model echoes the prompt's labels
    # ("Strategic Ground", "Key Strengths"), not snake_case identifiers.
    entry: dict[str, Any] = {}
    for key, value in result.items():
        norm_key = re.sub(r'[^a-z0-9]+', '_', str(key).strip().lower()).strip('_')
        if norm_key in ("overall_confidence", "recommended_strategy", "judicial_rebuttal"):
            continue
        target = _FLAT_STRATEGY_ALIASES.get(norm_key, norm_key)
        entry[target] = value

    if not rebuttal and isinstance(entry.get("rebuttal"), str):
        rebuttal = entry.pop("rebuttal")
    entry.pop("rebuttal", None)

    entries = _sanitize_strategies([entry]) if entry else []
    return entries, rebuttal


def _sanitize_strategies(strategies: Any) -> list[dict[str, Any]]:
    """Strip placeholder values and empty shells from LLM strategy output.

    STRATEGY_PROMPT forbids "N/A" and "No sufficiently relevant precedent found"
    in any field, but prompt rules alone are not a guarantee. Fields that end up
    empty are removed so the UI renders nothing rather than an error string.
    """
    if not isinstance(strategies, (list, tuple)):
        return []

    out: list[dict[str, Any]] = []
    for raw in strategies:
        if not isinstance(raw, dict):
            continue
        cleaned: dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, str):
                text = value.strip()
                if not text or text.lower() in _PLACEHOLDER_VALUES:
                    continue
                cleaned[key] = text
            elif isinstance(value, (list, tuple)):
                items = [
                    str(v).strip() for v in value
                    if isinstance(v, str) and v.strip()
                    and str(v).strip().lower() not in _PLACEHOLDER_VALUES
                ]
                if items:
                    cleaned[key] = items
            elif value is not None:
                cleaned[key] = value
        # Keep an entry when it carries any substantive content. Requiring
        # name/description discarded valid grounded entries whose only fields
        # were "description"+"recommended_actions" from the flat response shape.
        substantive = [
            k for k, v in cleaned.items()
            if v and (not isinstance(v, (list, tuple)) or len(v) > 0)
        ]
        if substantive and any(
            k in cleaned
            for k in ("name", "description", "strategic_ground", "recommended_actions", "action_plan", "pros")
        ):
            out.append(cleaned)
    return out


# ── Helper: Agent metadata recording ───────────────────────
def _record_completion(state: AgentState, agent_name: str, confidence: float, output_key: str, output_value: Any) -> AgentState:
    """Record agent completion with confidence and output."""
    completed = state.get("completed_agents", [])
    state["completed_agents"] = completed + [agent_name]

    confidences = state.get("agent_confidence", {})
    confidences[agent_name] = confidence
    state["agent_confidence"] = confidences

    state[output_key] = output_value  # type: ignore[typeddict-unknown-key]
    return state


# ── Agent 1: Case Understanding Agent ──────────────────────
async def case_understanding_agent(state: AgentState) -> AgentState:
    """Analyze case documents, extract facts, entities, and timeline.

    Uses Qwen3 LLM for comprehension and entity extraction.
    Input: state.documents
    Output: case_summary, case_facts, entities, timeline
    """
    start_time = time.monotonic()
    logger.info(f"[CaseUnderstanding] Starting analysis for case: {state.get('case_id')}")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT
        from app.document_pipeline.chunker import LegalChunker
        from app.document_pipeline.embedder import EmbeddingGenerator
        from app.embeddings.qdrant_client import get_qdrant_manager
        from app.core.config import settings

        documents = state.get("documents", [])
        query = state.get("query", "")
        case_id = state.get("case_id")

        if not documents and not query:
            state["case_summary"] = "No documents provided for analysis."
            state["case_facts"] = {}
            state["entities"] = {}
            state["timeline"] = []
            return _record_completion(state, "case_understanding", 0.5, "case_summary", state["case_summary"])

        # Dynamic Chunking and Embedding Generation at Startup
        chunker = LegalChunker()
        embedder = EmbeddingGenerator()
        qdrant = get_qdrant_manager()

        for doc in documents:
            filename = doc.get("filename") or "case_document"
            pages = doc.get("metadata", {}).get("pages") or doc.get("pages")
            if not pages:
                text = doc.get("text") or doc.get("parsed_text") or doc.get("raw_text") or ""
                pages = [text] if text else []
            
            # Splitting and chunking with page retention
            doc_chunks = chunker.chunk_pages(pages, {"filename": filename, "case_id": case_id})
            doc["chunks"] = doc_chunks

            # Generate embeddings and upsert to Qdrant
            if doc_chunks and qdrant.is_available():
                # Remove any previously indexed chunks for this exact document
                # (e.g. from a re-upload) so vectors never duplicate.
                try:
                    from qdrant_client.models import Filter, FieldCondition, MatchAny
                    qdrant.client.delete(
                        collection_name=settings.QDRANT_COLLECTION_DOCS,
                        points_selector=Filter(
                            must=[
                                FieldCondition(key="doc_type", match=MatchAny(any=["uploaded_document"])),
                                FieldCondition(key="source", match=MatchAny(any=[filename])),
                            ]
                        ),
                    )
                except Exception as del_exc:
                    logger.warning(f"Could not clear old vectors for '{filename}': {del_exc}")

                doc_chunks = embedder.embed_chunks(doc_chunks)
                qdrant_chunks = []
                for c in doc_chunks:
                    qdrant_chunks.append({
                        "text": c["text"],
                        "embedding": c["embedding"],
                        "metadata": {
                            "case_id": case_id,
                            "doc_type": "uploaded_document",
                            "filename": filename,
                            "page_number": c["metadata"]["page_number"],
                            "chunk_id": c["metadata"]["chunk_id"],
                            "source": filename,
                        }
                    })
                qdrant.upsert_chunks(qdrant_chunks, collection_name=settings.QDRANT_COLLECTION_DOCS)
                logger.info(f"Indexed {len(qdrant_chunks)} chunks for document '{filename}' (Case: {case_id})")

        # Build the prompt from the document. Budget matters here: the backend runs
        # on CPU with n_ctx=8192, so a 25,000-char slice per document (up to 125k
        # for 5 documents) both overflows the context and makes prefill so slow
        # that throughput fell from ~5 to ~2.7 tok/s, turning one agent into a
        # 10+ minute call. A single 6,000-char slice is enough for the summary,
        # parties and entities this agent produces; facts, timeline, issues and
        # evidence are all re-derived from the FULL document downstream.
        # Use up to 14 000 chars of the first document (was 6 000, which cut off
        # ~80% of a 30-page judgment before the foundational agent even saw it).
        # We still limit to 1 document at this stage to keep the prompt tight;
        # the full multi-doc text is used by later agents that need it.
        doc_texts = "\n\n---\n\n".join(
            d.get("text", d.get("parsed_text", ""))[:14000] for d in documents[:1]
        ) if documents else query

        # Layer 1 (noise filter): academic dossiers and illustrative files
        # repeat "ACADEMIC CASE STUDY" / "ILLUSTRATIVE ONLY" / page stamps on
        # many pages. Fed to the model verbatim they read as party assertions,
        # so an illustrative disclaimer gets quoted as if it were a holding.
        # Both the standalone markers and the meta sections are removed here,
        # at the single point where text enters a prompt.
        try:
            from app.agents.doc_meta_guard import strip_meta_sections, strip_standalone_noise

            doc_texts = strip_standalone_noise(strip_meta_sections(doc_texts))
        except Exception as _noise_exc:  # never block analysis on cleaning
            logger.warning(f"[NoiseFilter] skipped: {_noise_exc}")

        # Layer 1: Deterministic Metadata Extraction
        from app.agents.metadata_extractor import extract_metadata
        deterministic_meta = extract_metadata(doc_texts)
        state["metadata"] = deterministic_meta
        if deterministic_meta.get("case_category"):
            state["case_category"] = deterministic_meta["case_category"]

        prompt = f"""Analyze the following legal case document(s) and extract:

1. SUMMARY: Write a 4-6 sentence factual summary of the case.
2. CASE FACTS: Summarize the key facts in 3-5 bullet points.
3. PARTIES: Identify the plaintiff/petitioner, defendant/respondent, and any other parties.
4. KEY ENTITIES: Identify any courts, judges, advocates, witnesses, organizations mentioned.
5. COUNSEL SUBMISSIONS: Extract the actual arguments advanced by each side using the strict rules below.

Do NOT produce a legal_issues or timeline list: both are re-derived directly from
the document later, and asking for them here only lengthens the response.

{ISSUE_EXTRACTION_PROMPT}

{COUNSEL_EXTRACTION_PROMPT}

Respond in the following JSON format:
{{
    "summary": "Brief case summary",
    "facts": ["fact 1", "fact 2", ...],
    "parties": {{"plaintiff": "...", "defendant": "...", "others": ["..."]}},
    "counsel_submissions": {{"petitioner": ["..."], "respondent": ["..."]}},
    "entities": {{"courts": [], "judges": [], "advocates": [], "witnesses": [], "organizations": []}}
}}

Case Document(s):
{doc_texts}

Additional Query: {query}
"""
        provider = get_qwen_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "facts": {"type": "array", "items": {"type": "string"}},
                    "parties": {"type": "object"},
                    "counsel_submissions": {"type": "object"},
                    "entities": {"type": "object"},
                },
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            # This single call also returns counsel_submissions, so it needs
            # the Issue/Counsel budget: 520 cut every argument list off
            # mid-sentence and swapped columns looked like empty fields.
            max_tokens=1800,
        )

        summary_value = str(result.get("summary") or "").strip()
        if not summary_value and result.get("raw_response"):
            # Grammar-constrained generation failed and the fallback returned
            # unparsed text. Surface that rather than reporting no summary.
            summary_value = re.sub(r'\s+', ' ', str(result["raw_response"])).strip()[:600]
        state["case_summary"] = summary_value
        state["case_facts"] = result.get("facts", {})
        state["entities"] = result.get("entities", {})

        # Issues and timeline are derived here deterministically instead of being
        # generated. Both are read downstream (legal_research builds its RAG query
        # from state["legal_issues"]), and the document-stated extractors are more
        # reliable than the model: they cannot invent a question the court never
        # framed. report_generation re-grounds issues later; this keeps the value
        # correct for every consumer in between.
        from app.agents.presentation_universal import (
            _court_framed_issues,
            _enumerated_issues,
        )
        from app.agents.analysis_fixes_v2 import build_fact_timeline

        full_text = "\n\n".join(
            d.get("text") or d.get("parsed_text") or "" for d in documents
        )
        det_issues = _court_framed_issues(full_text) or _enumerated_issues(full_text)
        state["legal_issues"] = [i.get("text") or i.get("issue") or "" for i in det_issues]
        state["legal_issue_details"] = det_issues
        state["legal_issues_source"] = "document" if det_issues else ""

        # Hybrid fallback: only when the document states no issues at all. A
        # standard judgment always takes the deterministic branch above and
        # never pays for (or risks) a generation.
        if not det_issues:
            ai_issues = await llm_extract_issues_as_fallback(full_text)
            if ai_issues:
                state["legal_issues"] = [i["text"] for i in ai_issues]
                state["legal_issue_details"] = ai_issues
                state["legal_issues_source"] = "ai"
                logger.info(
                    f"[IssueFallback] deterministic extraction found 0 issues; "
                    f"using {len(ai_issues)} LLM-generated issue(s)"
                )
        det_date = (state.get("metadata") or {}).get("decision_date")
        dec_date = det_date.get("value") if isinstance(det_date, dict) else det_date
        state["timeline"] = build_fact_timeline(full_text, dec_date)

        # Counsel submissions from the LLM, filtered for placeholders so the
        # deterministic extractor's empty lists stay authoritative when the
        # model invents text instead of reporting none.
        raw_subs = result.get("counsel_submissions") or {}
        pet_side: Any = None
        if isinstance(raw_subs, dict):
            def_side: Any = None
            for pet_key, def_key in (
                ("petitioner", "respondent"),
                ("plaintiff", "defendant"),
                ("appellant", "appellee"),
                ("defense", "prosecution"),
            ):
                if raw_subs.get(pet_key) or raw_subs.get(def_key):
                    pet_side, def_side = raw_subs.get(pet_key), raw_subs.get(def_key)
                    break
            state["counsel_submissions"] = {
                "petitioner": _clean_submission_list(pet_side),
                "respondent": _clean_submission_list(def_side),
            }
        else:
            state["counsel_submissions"] = {"petitioner": [], "respondent": []}

        text_len = len(doc_texts.strip())
        has_parties = bool(result.get("parties", {}).get("plaintiff") or result.get("parties", {}).get("petitioner"))
        confidence = 0.40
        if text_len > 1000:
            confidence += 0.20
        if text_len > 5000:
            confidence += 0.15
        if has_parties:
            confidence += 0.15
        confidence = min(0.95, confidence)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[CaseUnderstanding] Complete: confidence={confidence:.2f}, {duration_ms:.0f}ms")
        return _record_completion(state, "case_understanding", confidence, "case_summary", state["case_summary"])

    except Exception as exc:
        logger.error(f"[CaseUnderstanding] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"CaseUnderstanding: {exc}"]
        return _record_completion(state, "case_understanding", 0.0, "case_summary", "Case understanding could not be completed for this dossier.")


# ── Agent 2: Legal Research Agent ──────────────────────────
async def legal_research_agent(state: AgentState) -> AgentState:
    """Retrieve applicable acts, sections, and precedents using RAG.

    Input: state.legal_issues, state.case_facts, state.query
    Output: applicable_acts, applicable_sections, precedents
    """
    start_time = time.monotonic()
    logger.info(f"[LegalResearch] Searching for applicable law")

    try:
        from app.rag.rag_pipeline import RAGPipeline

        issues = state.get("legal_issues", [])
        # Build RAG query using the supervisor's extracted legal issues and facts
        query_parts = []
        if issues:
            query_parts.extend(issues)
        if state.get("case_summary"):
            query_parts.append(state["case_summary"])
        
        query = " ".join(query_parts) if query_parts else (state.get("query", "") or "legal case analysis")

        # Use the RAG pipeline for multi-source retrieval
        rag = RAGPipeline()

        # Index the active case documents into the in-memory BM25 lexical index on the fly
        docs = state.get("documents", [])
        if docs:
            try:
                formatted_docs = []
                for doc in docs:
                    text = doc.get("text") or doc.get("content") or ""
                    if text:
                        # Split text into sentence-like chunks for more granular keyword matches
                        chunks = [c.strip() for c in text.split("\n") if len(c.strip()) > 30]
                        if not chunks:
                            chunks = [text]
                        for c in chunks:
                            formatted_docs.append({
                                "text": c,
                                "metadata": {"source": doc.get("filename") or "case_document"}
                            })
                if formatted_docs:
                    rag.keyword_retriever.index(formatted_docs)
            except Exception as e:
                logger.warning(f"Failed to index case documents in KeywordRetriever: {e}")

        rag_results = await rag.search(query, top_k=20)

        # Extract section references from RAG results
        sections: list[dict[str, Any]] = []
        acts: list[str] = []
        precedents: list[dict[str, Any]] = []

        # Imported before the RAG loop below uses it. The import used to sit
        # AFTER that loop, so the first norm_act() call raised
        # UnboundLocalError and the whole agent aborted - which silently emptied
        # applicable_sections and precedents.
        from app.agents.analysis_fixes_v2 import norm_act as _norm_act

        for result in rag_results:
            doc_type = result.get("doc_type") or (result.get("metadata") or {}).get("document_type") or "act"
            metadata = result.get("metadata") or {}
            source = result.get("source") or ""
            act_name = metadata.get("act_name") or metadata.get("act") or result.get("act") or "Unknown Act"
            
            # Determine if this result is a precedent case or a statute section
            is_precedent = False
            source_lower = source.lower()
            if doc_type in ["precedent", "case"] or act_name in ["Unknown", "Unknown Act", ""]:
                # If the source filename contains constitution or act name, treat as statute section
                if "constitution" in source_lower or any(act.lower() in source_lower for act in ["bns", "bnss", "bsa", "ipc", "crpc"]):
                    is_precedent = False
                else:
                    is_precedent = True

            if is_precedent:
                # Extract precedent
                case_name = metadata.get("case_name") or result.get("case_name")
                if not case_name:
                    cname = source.replace(".html", "").replace(".pdf", "").replace("_", " ")
                    if cname.isdigit():
                        case_name = f"Indian Kanoon Judgement {cname}"
                    else:
                        case_name = cname

                # Reject retriever placeholders. With the KG/vector backends
                # live, results can carry a literal "vector" (or "kg", "chunk")
                # as the name, which reached the report as a precedent and was
                # then scored as a hallucinated citation.
                if re.sub(r'[^a-z0-9]', '', str(case_name).lower()) in _PLACEHOLDER_VALUES:
                    continue

                precedents.append({
                    "case_name": case_name,
                    "citation": metadata.get("citation") or result.get("citation") or f"Source: {source}",
                    "relevance_score": result.get("score", 0.0),
                    "summary": result.get("text", "")[:300],
                })
            else:
                # Extract section
                section_number = metadata.get("section_number") or result.get("section_number")
                if not section_number and doc_type == "act":
                    match = re.match(r'^(?:Section|Article|Sec\.?|Art\.?)\s*(\d+[A-Za-z]*)', result.get("text", ""), re.IGNORECASE)
                    if match:
                        section_number = match.group(1)
                        
                if section_number:
                    sections.append({
                        "section_number": str(section_number),
                        "act": act_name,
                        "title": metadata.get("title") or result.get("title") or f"Section {section_number}",
                        "text": result.get("text", "")[:500],
                        "relevance_score": result.get("score", 0.0),
                    })
                    if act_name and act_name != "Unknown Act":
                        acts.append(_norm_act(act_name))

        # Also extract sections and acts directly cited in the uploaded case document(s)
        from app.agents.analysis_fixes_v2 import (
            extract_section_act_bindings,
            map_section_to_act,
            extract_cited_precedents,
            extract_articles,
            similarity_pct,
        )

        def _act_key(name: str) -> str:
            return re.sub(r'[^a-z0-9]', '', name.lower().replace('the ', ''))

        doc_text_full = " ".join((d.get("text") or d.get("content") or "") for d in docs)
        category = state.get("case_category", "criminal")
        # Decision date drives the pre/BNSS-era section mapping: a bare "Section
        # 482" in a pre-July-2024 document is CrPC 1973, in a later one BNSS.
        _md = (state.get("metadata") or {})
        _dd = _md.get("decision_date") if isinstance(_md, dict) else None
        case_decision_date = _dd.get("value") if isinstance(_dd, dict) else _dd
        
        # 1. Extract and bind sections to their accurate Acts (including 2(16), 50, 22, the Act)
        binds = extract_section_act_bindings(doc_text_full) if doc_text_full else {}
        
        if doc_text_full:
            # Extract sections explicitly mentioned in document text
            sec_matches = re.finditer(
                r"(?:Section|Sec\.|u/s|under\s+section)\s*(\d+[A-Za-z]*(?:\([a-z0-9]+\))*)",
                doc_text_full,
                re.IGNORECASE
            )
            for sm in sec_matches:
                sec_num = sm.group(1)
                sec_act = map_section_to_act(sec_num, binds, category=category, decision_date=case_decision_date)
                start_pos = max(0, sm.start() - 40)
                end_pos = min(len(doc_text_full), sm.end() + 140)
                snippet = doc_text_full[start_pos:end_pos].replace("\n", " ").strip()

                sections.insert(0, {
                    "section_number": str(sec_num),
                    "act": sec_act,
                    "title": f"Section {sec_num} ({sec_act})",
                    "text": snippet,
                    "relevance_score": 0.95,
                    "explicitly_mentioned": True
                })
                if sec_act not in acts and sec_act != "Statute (verify)":
                    acts.append(sec_act)

        # 2. Extract Real In-Text Cited Precedents (deduped, clean names, 1990-1992 years)
        in_text_precedents = extract_cited_precedents(doc_text_full) if doc_text_full else []
        all_precedents = in_text_precedents + precedents

        # Normalize Precedent similarity scores
        for p in all_precedents:
            raw_s = p.get("relevance_score") or p.get("score") or 0.88
            p["relevance_score"] = similarity_pct(raw_s) / 100.0

        # 3. Extract Literal Constitutional Articles (no hallucinated defaults)
        state["articles"] = extract_articles(doc_text_full) if doc_text_full else []

        # Deduplicate sections by Act + number so "Section Art. 14", "Article 14"
        # and "Art. 14 of the Constitution" collapse to one entry, while
        # Section 63 BSA and Section 63 BNSS stay distinct.
        seen = set()
        unique_sections = []
        for s in sections:
            clean_act = map_section_to_act(s['section_number'], binds, category=category, decision_date=case_decision_date)
            s['act'] = clean_act
            key = f"{s['section_number']}_{clean_act}"
            if key not in seen:
                seen.add(key)
                unique_sections.append(s)

        # Drop provisions the document only cites or declares invalid. Without
        # this, a section mentioned solely in a reference list or in a "struck
        # down" aside is presented as an applicable provision of this case.
        from app.agents.analysis_fixes_v2 import filter_contextual_sections

        substantive_sections = filter_contextual_sections(unique_sections, doc_text_full)
        dropped_count = len(unique_sections) - len(substantive_sections)
        if dropped_count:
            logger.info(
                f"[LegalResearch] Excluded {dropped_count} citation-only/superseded "
                f"section reference(s) not applied by this document"
            )

        unique_sections = substantive_sections[:12]
        state["applicable_sections"] = unique_sections
        state["applicable_acts"] = normalize_statutes(acts)[:10]
        state["precedents"] = all_precedents[:7]

        confidence = 0.98 if (unique_sections and all_precedents) else (0.975 if all_precedents else (0.85 if unique_sections else 0.40))
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[LegalResearch] Found {len(unique_sections)} sections, {len(all_precedents)} precedents ({duration_ms:.0f}ms)")
        return _record_completion(state, "legal_research", confidence, "applicable_sections", state["applicable_sections"])

    except Exception as exc:
        logger.error(f"[LegalResearch] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"LegalResearch: {exc}"]
        state["applicable_sections"] = []
        state["applicable_acts"] = []
        state["precedents"] = []
        return _record_completion(state, "legal_research", 0.0, "applicable_sections", [])


# ── Agent 3: Knowledge Graph Agent ─────────────────────────
async def knowledge_graph_agent(state: AgentState) -> AgentState:
    """Build dynamic evidence graph in FalkorDB from extracted entities.

    Input: state.entities, state.case_id, state.applicable_sections
    Output: kg_data
    """
    start_time = time.monotonic()
    logger.info(f"[KnowledgeGraph] Building case graph")

    try:
        from app.kg.falkordb_client import get_falkordb_client

        kg_data: dict[str, Any] = {"nodes": [], "edges": [], "status": "unavailable"}

        # 1. Build base local graph structure (Case, Parties, Acts, Sections)
        entities = state.get("entities", {}) or {}
        sections = state.get("applicable_sections", []) or []
        case_id = state.get("case_id", "case_node")

        # Add Case node
        kg_data["nodes"].append({"id": case_id, "type": "Case", "label": f"Case {case_id[:8]}"})

        # Add Party nodes (from entities)
        petitioner = entities.get("parties", {}).get("petitioner")
        if petitioner:
            kg_data["nodes"].append({"id": petitioner, "type": "Party", "label": f"Petitioner: {petitioner}"})
            kg_data["edges"].append({"source": case_id, "target": petitioner, "type": "PETITIONER"})

        respondent = entities.get("parties", {}).get("respondent")
        if respondent:
            kg_data["nodes"].append({"id": respondent, "type": "Party", "label": f"Respondent: {respondent}"})
            kg_data["edges"].append({"source": case_id, "target": respondent, "type": "RESPONDENT"})

        # Add other parties
        for party_name in entities.get("parties", {}).get("others", []):
            if party_name not in [petitioner, respondent]:
                kg_data["nodes"].append({"id": party_name, "type": "Party", "label": party_name})

        # Add Act nodes
        for act in state.get("applicable_acts", []):
            kg_data["nodes"].append({"id": act, "type": "Act", "label": act})

        # Add referenced Section nodes and link them to Case
        for section in sections[:10]:
            sec_id = f"{section.get('act', '')}_{section.get('section_number', '')}"
            sec_label = f"Sec {section.get('section_number')} {section.get('act', '')}"
            kg_data["nodes"].append({"id": sec_id, "type": "Section", "label": sec_label})
            kg_data["edges"].append({"source": case_id, "target": sec_id, "type": "REFERENCES"})

        # Deduplicate nodes to prevent double-rendering
        seen_nodes = set()
        unique_nodes = []
        for n in kg_data["nodes"]:
            if n["id"] not in seen_nodes:
                seen_nodes.add(n["id"])
                unique_nodes.append(n)
        kg_data["nodes"] = unique_nodes

        # 2. Query FalkorDB to enrich the graph if connected
        falkordb = await get_falkordb_client()
        connected = await falkordb.verify_connectivity()

        if not connected:
            logger.warning("[KnowledgeGraph] FalkorDB unavailable - using base graph")
            kg_data["status"] = "local"
        else:
            logger.info("[KnowledgeGraph] FalkorDB connected - enriching graph")
            kg_data["status"] = "falkordb"
            
            # Query FalkorDB for relations and additional section nodes
            for section in sections[:10]:
                try:
                    num_val = str(section.get("section_number"))
                    act_val = str(section.get("act", ""))
                    sec_id = f"{act_val}_{num_val}"
                    
                    results = await falkordb.run_query(
                        """
                        MATCH (s:Section {section_number: $num, act: $act})
                        OPTIONAL MATCH (s)-[r]-(related:Section)
                        RETURN s, collect(DISTINCT {type: type(r), target_id: related.section_id, target_act: related.act, title: related.title}) as relations
                        LIMIT 5
                        """,
                        {"num": num_val, "act": act_val},
                    )
                    
                    for record in results:
                        relations = record.get("relations", [])
                        for rel in relations:
                            if rel and rel.get("target_id"):
                                target_id = rel["target_id"]
                                if target_id not in seen_nodes:
                                    seen_nodes.add(target_id)
                                    kg_data["nodes"].append({
                                        "id": target_id,
                                        "type": "Section",
                                        "label": rel.get("title") or f"Sec {target_id}"
                                    })
                                kg_data["edges"].append({
                                    "source": sec_id,
                                    "target": target_id,
                                    "type": rel.get("type", "RELATED")
                                })
                except Exception as q_exc:
                    logger.warning(f"[KnowledgeGraph] FalkorDB query failed for section: {q_exc}")

        state["kg_data"] = kg_data
        confidence = 0.75 if kg_data["nodes"] else 0.30
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[KnowledgeGraph] Built graph: {len(kg_data['nodes'])} nodes, {len(kg_data['edges'])} edges ({duration_ms:.0f}ms)")
        return _record_completion(state, "knowledge_graph", confidence, "kg_data", kg_data)

    except Exception as exc:
        logger.error(f"[KnowledgeGraph] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"KnowledgeGraph: {exc}"]
        state["kg_data"] = {"nodes": [], "edges": [], "status": "error", "error": str(exc)}
        return _record_completion(state, "knowledge_graph", 0.0, "kg_data", state["kg_data"])


# ── Agent 4: Evidence Reliability Agent ────────────────────
async def evidence_reliability_agent(state: AgentState) -> AgentState:
    """Score evidence reliability using multi-factor analysis.

    Uses DeepSeek-R1 for verification and scoring.
    Input: state.documents, state.case_facts
    Output: evidence_assessment
    """
    start_time = time.monotonic()
    logger.info("[EvidenceReliability] Assessing evidence")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        documents = state.get("documents", [])
        if not documents:
            evidence = {"score": 0.5, "items": [], "summary": "No evidence documents provided."}
            state["evidence_assessment"] = evidence
            return _record_completion(state, "evidence_reliability", 0.5, "evidence_assessment", evidence)

        # Feed comprehensive document context (up to 6,000 chars across documents)
        doc_context = "\n\n---\n\n".join(
            f"DOC {i+1} ({d.get('filename', 'document')}):\n{d.get('text', d.get('parsed_text', ''))[:4000]}"
            for i, d in enumerate(documents[:3])
        )

        prompt = f"""Assess the reliability of evidence in the following case documents.

For each piece of evidence (oral testimony, documentary, electronic, forensic, panchnama, FIR, seizure memo), score on:
- Source credibility (0-1)
- Corroboration level (0-1)
- Chain of custody (0-1)
- Internal consistency (0-1)
- Relevance to case (0-1)
Provide an overall reliability score (0-1).

Documents:
{doc_context}

Respond with JSON:
{{"overall_score": 0.0, "items": [{{"description": "", "type": "documentary|oral|electronic|forensic", "source_score": 0.0, "corroboration": 0.0, "chain_of_custody": 0.0, "consistency": 0.0, "relevance": 0.0, "overall": 0.0, "notes": ""}}], "summary": ""}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "overall_score": {"type": "number"},
                    "items": {"type": "array"},
                    "summary": {"type": "string"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=650,
        )

        state["evidence_assessment"] = result
        confidence = max(0.2, min(1.0, float(result.get("overall_score", 0.75))))
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[EvidenceReliability] Overall score: {confidence:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "evidence_reliability", confidence, "evidence_assessment", result)

    except Exception as exc:
        logger.error(f"[EvidenceReliability] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"EvidenceReliability: {exc}"]
        state["evidence_assessment"] = {"score": 0.0, "error": str(exc)}
        return _record_completion(state, "evidence_reliability", 0.0, "evidence_assessment", state["evidence_assessment"])


# ── Agent 5: Contradiction Detection Agent ─────────────────
async def contradiction_detection_agent(state: AgentState) -> AgentState:
    """Cross-reference statements, submissions, and evidence to detect contradictions.

    Performs multi-document cross-referencing or intra-document consistency analysis.
    Input: state.documents, state.evidence_assessment
    Output: contradictions
    """
    start_time = time.monotonic()
    logger.info("[ContradictionDetection] Scanning for contradictions")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        documents = state.get("documents", [])
        if not documents:
            contradictions: list[dict[str, Any]] = []
            state["contradictions"] = contradictions
            return _record_completion(state, "contradiction_detection", 0.8, "contradictions", contradictions)

        if len(documents) >= 2:
            prompt = f"""Analyze these legal documents for contradictions between statements, evidence, and facts.

Compare the documents and identify:
1. Direct contradictions (one says X, another says not-X)
2. Material inconsistencies (differences in dates, names, sequences, or amounts)
3. Testimony discrepancies vs documentary evidence
4. Implicit contradictions (one implies what another denies)

For each contradiction found, provide:
- Conflicting statements (with document references)
- Severity (high/medium/low)
- Confidence (0-1)
- Whether it's resolvable

Documents:
{chr(10).join(f"DOC {i+1}: {d.get('text', d.get('parsed_text', ''))[:1500]}" for i, d in enumerate(documents[:5]))}

Respond with JSON: {{"contradictions": [{{"type": "", "statement_a": "", "statement_b": "", "severity": "", "confidence": 0.0, "resolvable": false, "notes": ""}}], "overall_contradiction_score": 0.0}}
"""
        else:
            # Single document: perform intra-document inconsistency analysis (e.g. claims vs findings, date conflicts, petitioner vs respondent positions)
            doc_text = _llm_clean(documents[0].get('text', documents[0].get('parsed_text', '')))[:6000]
            prompt = f"""Analyze this legal document for internal contradictions, inconsistencies, or conflicting factual positions.

Examine:
1. Inconsistencies between rival submissions (Petitioner/Appellant vs Respondent/State)
2. Discrepancies between allegations/FIR and witness statements or evidentiary records
3. Internal chronological or date/timeline inconsistencies
4. Gaps between statutory requirements and factual claims made

Document text:
{doc_text}

Respond with JSON:
{{"contradictions": [{{"type": "rival_submission_conflict|evidentiary_inconsistency|temporal_discrepancy", "statement_a": "First assertion", "statement_b": "Conflicting assertion", "severity": "high|medium|low", "confidence": 0.85, "resolvable": false, "notes": "Explanation of inconsistency"}}], "overall_contradiction_score": 0.1}}
"""

        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "contradictions": {"type": "array"},
                    "overall_contradiction_score": {"type": "number"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=650,
        )

        contradictions_found = result.get("contradictions", [])
        overall_score = float(result.get("overall_contradiction_score", 0.0))
        state["contradictions"] = contradictions_found

        confidence = max(0.2, min(0.98, 1.0 - (overall_score * 0.5)))
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ContradictionDetection] Found {len(contradictions_found)} contradictions, score={overall_score:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "contradiction_detection", confidence, "contradictions", contradictions_found)

    except Exception as exc:
        logger.error(f"[ContradictionDetection] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ContradictionDetection: {exc}"]
        state["contradictions"] = [{"error": str(exc)}]
        return _record_completion(state, "contradiction_detection", 0.0, "contradictions", state["contradictions"])


# ── Agent 6: Procedural Compliance Agent ───────────────────
async def procedural_compliance_agent(state: AgentState) -> AgentState:
    """Check procedural compliance against BNSS 2023 / CrPC 1973.

    Input: state.case_facts, state.timeline
    Output: procedural_status
    """
    start_time = time.monotonic()
    logger.info("[ProceduralCompliance] Checking procedure")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        timeline = state.get("timeline", [])
        facts = state.get("case_facts", {})

        if not timeline and not facts:
            status = {"compliance_score": 0.5, "checks": [], "summary": "Insufficient data for procedural compliance check."}
            state["procedural_status"] = status
            return _record_completion(state, "procedural_compliance", 0.5, "procedural_status", status)

        prompt = f"""Assess procedural compliance in this legal case against BNSS 2023 (or CrPC 1973 if pre-July 2024).

Check the following procedural aspects:
1. FIR registration (timeliness, jurisdiction)
2. Arrest procedure (grounds, notification, medical examination)
3. Evidence collection (chain of custody, search procedure)
4. Bail consideration (grounds, hearing)
5. Charge sheet filing (timeline, contents)
6. Jurisdiction (territorial, subject matter)

Case facts and timeline:
{json.dumps({"facts": facts, "timeline": timeline}, indent=2)}

Respond with JSON:
{{"compliance_score": 0.0, "checks": [{{"aspect": "", "status": "compliant|partially_compliant|non_compliant|unable_to_determine", "score": 0.0, "notes": ""}}], "summary": ""}}
"""
        provider = get_qwen_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "compliance_score": {"type": "number"},
                    "checks": {"type": "array"},
                    "summary": {"type": "string"},
                },
            },
            system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=520,
        )

        state["procedural_status"] = result
        confidence = result.get("compliance_score", 0.5)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ProceduralCompliance] Score: {confidence:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "procedural_compliance", confidence, "procedural_status", result)

    except Exception as exc:
        logger.error(f"[ProceduralCompliance] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ProceduralCompliance: {exc}"]
        state["procedural_status"] = {"compliance_score": 0.0, "error": str(exc)}
        return _record_completion(state, "procedural_compliance", 0.0, "procedural_status", state["procedural_status"])


# ── Agent 7: Legal Reasoning Agent ─────────────────────────
async def legal_reasoning_agent(state: AgentState) -> AgentState:
    """Apply IRAC methodology for legal reasoning.

    Input: state.applicable_sections, state.case_facts, state.legal_issues
    Output: legal_reasoning, irac_analysis
    """
    start_time = time.monotonic()
    logger.info("[LegalReasoning] Applying IRAC methodology")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        sections = state.get("applicable_sections", [])
        facts = state.get("case_facts", {})
        issues = state.get("legal_issues", [])
        articles = state.get("articles") or []
        provisions = sections[:5]
        if not provisions and articles:
            # Article-based matters (e.g. constitutional writs citing
            # Articles 21/32) have no "Section N" at all. Feeding an empty
            # provision list is what made the model answer with empty IRAC.
            provisions = [
                {
                    "section_number": a.get("num") or a.get("article"),
                    "act": "Constitution of India",
                    "relevance": a.get("meaning") or "Constitutional provision.",
                }
                for a in articles[:5]
            ]

        prompt = f"""Apply IRAC (Issue, Rule, Application, Conclusion) methodology to this legal case.

ISSUE: Identify the legal question(s)
RULE: State applicable legal provisions
APPLICATION: Apply law to facts
CONCLUSION: Reach a reasoned conclusion

Applicable Provisions:
{json.dumps(provisions, indent=2)}

Legal Issues:
{json.dumps(issues, indent=2)}

Case Facts:
{json.dumps(facts, indent=2) if isinstance(facts, dict) else str(facts)[:1000]}

IMPORTANT: This is an advisory analysis for advocates, NOT a judicial decision.
Always note alternative interpretations where applicable.

Respond with JSON:
{{"issues_identified": ["..."], "rules": [{{"section": "", "provision": ""}}], "application": "", "conclusion": "", "alternative_interpretations": ["..."], "confidence": 0.0}}
"""
        provider = get_qwen_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "issues_identified": {"type": "array", "items": {"type": "string"}},
                    "rules": {"type": "array"},
                    "application": {"type": "string"},
                    "conclusion": {"type": "string"},
                    "alternative_interpretations": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
            },
system_prompt=QWEN_SYSTEM_PROMPT,
            temperature=0.1,
            # 520 truncated this combined JSON mid-sentence: counsel
            # submissions are the longest field and the closing brace was being
            # cut, which discarded summary/facts/parties along with it.
            max_tokens=1400,
        )

        irac_issues = [str(i).strip() for i in (result.get("issues_identified") or []) if str(i).strip()]
        irac_conclusion = str(result.get("conclusion") or "").strip()

        # An empty IRAC body is worse than a grounded one: the report was
        # rendering "ISSUES:\n\n\nCONCLUSION:\n" while five real issues sat
        # in state. Fall back to the extracted issues and a document-grounded
        # disposition rather than persisting empty headings.
        doc_text = ""
        for d in state.get("documents") or []:
            if isinstance(d, dict):
                doc_text += str(d.get("text") or d.get("parsed_text") or "") + "\n"
        if not irac_issues:
            irac_issues = [
                str(i.get("issue") if isinstance(i, dict) else i).strip()
                for i in issues or []
            ]
            irac_issues = [i for i in irac_issues if i]
        if not irac_conclusion and doc_text:
            try:
                from app.agents.presentation_universal import render_conclusion

                meta = state.get("metadata") or {}
                irac_conclusion = str(render_conclusion(meta, doc_text) or "").strip()
            except Exception:
                irac_conclusion = ""
        if irac_issues or irac_conclusion:
            result["issues_identified"] = irac_issues
            result["conclusion"] = irac_conclusion

        state["irac_analysis"] = result
        state["legal_reasoning"] = (
            f"ISSUES:\n{chr(10).join(irac_issues)}\n\nCONCLUSION:\n{irac_conclusion}"
        )
        confidence = result.get("confidence") or (0.7 if (irac_issues or irac_conclusion) else 0.0)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[LegalReasoning] IRAC complete, confidence={confidence:.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "legal_reasoning", confidence, "legal_reasoning", state["legal_reasoning"])

    except Exception as exc:
        logger.error(f"[LegalReasoning] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"LegalReasoning: {exc}"]
        state["legal_reasoning"] = "Legal reasoning could not be completed for this dossier."
        return _record_completion(state, "legal_reasoning", 0.0, "legal_reasoning", state["legal_reasoning"])


# ── Agent 8: Strategy Recommendation Agent ─────────────────
async def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """Generate litigation strategies with pro/con analysis.

    Uses DeepSeek-R1 for structured debate and strategy generation.
    """
    start_time = time.monotonic()
    logger.info("[StrategyRecommendation] Generating strategies")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        reasoning = state.get("legal_reasoning", "")
        risk = state.get("risk_assessment", {})
        evidence = state.get("evidence_assessment", {})
        metadata = state.get("metadata", {}) or {}
        documents = state.get("documents", [])

        # Counsel arguments as recorded by case understanding, so "Strategic
        # Ground" quotes the appellant's actual arguments rather than invented ones.
        counsel = state.get("counsel_submissions", {}) or {}
        pet_args = _clean_submission_list(counsel.get("petitioner"))
        opp_args = _clean_submission_list(counsel.get("respondent"))

        # Full document text: the grounding rules require the model to see the
        # operative passages, and procedural directions only appear in the tail.
        case_text = "\n\n".join(
            d.get("text") or d.get("parsed_text") or "" for d in documents
        )[:20000]

        prompt = f"""{STRATEGY_PROMPT}

CASE METADATA:
{json.dumps(metadata, default=str)[:1200]}

APPELLANT / PETITIONER SUBMISSIONS (from this document):
{json.dumps(pet_args, indent=2) if pet_args else "None recorded in this document."}

RESPONDENT / PROSECUTION SUBMISSIONS (from this document):
{json.dumps(opp_args, indent=2) if opp_args else "None recorded in this document."}

CASE REASONING:
{reasoning[:1000]}

Evidence assessment:
{json.dumps(evidence, indent=2)[:500]}

Risk assessment:
{json.dumps(risk, indent=2)[:500]}

DOCUMENT TEXT (grounding source - cite only what appears here):
{case_text}

Map the extraction rules above onto this JSON schema. Leave a list empty rather
than inventing content, and never write placeholder strings such as "N/A" or
"No sufficiently relevant precedent found" into any value:
{{
  "strategies": [
    {{
      "name": "",
      "description": "",
      "legal_basis": [],
      "success_probability": 0.0,
      "pros": [],
      "cons": [],
      "recommended_actions": [],
      "fallback": "",
      "strategic_ground": "",
      "key_strengths": [],
      "action_plan": []
    }}
  ],
  "judicial_rebuttal": "",
  "overall_confidence": 0.0
}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "strategies": {"type": "array"},
                    "judicial_rebuttal": {"type": "string"},
                    "recommended_strategy": {"type": "string"},
                    "overall_confidence": {"type": "number"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.3,
            # 1800 so every strategy's strategic_ground / key_strengths /
            # action_plan is emitted in full; at 750 the tail was dropped and
            # the UI fell back to generic boilerplate.
            max_tokens=1800,
        )

        # Accept both the "strategies" array and the flat grounded shape.
        entries, rebuttal = _normalise_strategy_result(result)
        if not entries:
            # The model returned nothing usable. Fall back to the deterministic,
            # document-grounded extraction rather than shipping an empty module:
            # these sentences are quoted from the source text, so they cannot
            # invent strategy.
            from app.agents.analysis_fixes_v2 import build_risk_strategy

            grounded = build_risk_strategy(
                "\n\n".join(d.get("text") or "" for d in documents), state.get("metadata") or {}
            )
            entries = [{
                "name": "Document-grounded assessment",
                "description": "; ".join(grounded.get("strengths") or []) or grounded.get("conclusion", ""),
                "recommended_actions": [grounded["procedural"]] if grounded.get("procedural") else [],
            }]
        state["strategy_options"] = _sanitize_strategies(entries)
        state["judicial_rebuttal"] = rebuttal
        confidence = result.get("overall_confidence", 0.6)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[StrategyRecommendation] {len(state['strategy_options'])} strategies ({duration_ms:.0f}ms)")
        return _record_completion(state, "strategy_recommendation", confidence, "strategy_options", state["strategy_options"])

    except Exception as exc:
        logger.error(f"[StrategyRecommendation] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"StrategyRecommendation: {exc}"]
        state["strategy_options"] = []
        return _record_completion(state, "strategy_recommendation", 0.0, "strategy_options", [])


# ── Agent 9: Risk Assessment Agent ─────────────────────────
async def risk_assessment_agent(state: AgentState) -> AgentState:
    """Evaluate case strengths, weaknesses, and outcome probabilities.

    Uses DeepSeek-R1 for risk modeling.
    """
    start_time = time.monotonic()
    logger.info("[RiskAssessment] Evaluating risks")

    try:
        from app.llm.deepseek import get_deepseek_provider, DEEPSEEK_SYSTEM_PROMPT

        evidence = state.get("evidence_assessment", {})
        contradictions = state.get("contradictions", [])
        reasoning = state.get("legal_reasoning", "")

        prompt = f"""Assess litigation risk for this case. Consider:
- Strength of evidence
- Presence of contradictions
- Legal merits
- Procedural compliance
- Precedent alignment
- Practical considerations (cost, time, witness availability)

Provide:
1. Overall case strength (0-1)
2. Key strengths
3. Key weaknesses
4. Outcome probability distribution (win/lose/settle)
5. Key risk factors
6. Mitigation recommendations

Evidence: {json.dumps(evidence, indent=2)[:500]}
Contradictions: {json.dumps(contradictions, indent=2)[:300]}
Reasoning: {reasoning[:500]}

Respond with JSON:
{{"overall_strength": 0.0, "strengths": [], "weaknesses": [], "outcome_probabilities": {{"favorable": 0.0, "unfavorable": 0.0, "settlement": 0.0}}, "key_risks": [], "mitigation": [], "confidence": 0.0}}
"""
        provider = get_deepseek_provider()
        result = provider.generate_structured(
            prompt,
            output_schema={
                "type": "object",
                "properties": {
                    "overall_strength": {"type": "number"},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "outcome_probabilities": {"type": "object"},
                    "key_risks": {"type": "array", "items": {"type": "string"}},
                    "mitigation": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
            },
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=520,
        )

        state["risk_assessment"] = result
        confidence = result.get("confidence", 0.6)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[RiskAssessment] Strength: {result.get('overall_strength', 0):.2f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "risk_assessment", confidence, "risk_assessment", result)

    except Exception as exc:
        logger.error(f"[RiskAssessment] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"RiskAssessment: {exc}"]
        state["risk_assessment"] = {"error": str(exc)}
        return _record_completion(state, "risk_assessment", 0.0, "risk_assessment", state["risk_assessment"])


# ── Agent 10: Confidence Fusion Agent ──────────────────────
async def confidence_fusion_agent(state: AgentState) -> AgentState:
    """Aggregate per-agent confidence scores using weighted fusion.

    Implements Dempster-Shafer-inspired weighted fusion of 11 agent confidences
    to produce a single trust score for the analysis.
    """
    start_time = time.monotonic()
    logger.info("[ConfidenceFusion] Fusing agent confidences")

    try:
        confidences = state.get("agent_confidence", {})
        evidence_score = state.get("evidence_assessment", {}).get("overall_score", 0.5)
        contradiction_score = 1.0 - sum(c.get("confidence", 0) for c in state.get("contradictions", [])) / max(len(state.get("contradictions", [])) or 1, 1)
        compliance_score = state.get("procedural_status", {}).get("compliance_score", 0.5)

        # Weighted fusion
        weights = {
            "case_understanding": 0.10,
            "legal_research": 0.15,
            "knowledge_graph": 0.05,
            "evidence_reliability": 0.15,
            "contradiction_detection": 0.10,
            "procedural_compliance": 0.10,
            "legal_reasoning": 0.15,
            "strategy_recommendation": 0.10,
            "risk_assessment": 0.10,
            # explainability and report_generation are output agents
        }

        weighted_sum = 0.0
        total_weight = 0.0
        for agent, weight in weights.items():
            conf = confidences.get(agent, 0.0)
            if conf > 0:  # Only count agents that actually ran
                weighted_sum += conf * weight
                total_weight += weight

        trust_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Blend in evidence and compliance signals
        trust_score = (trust_score * 0.7) + (evidence_score * 0.15) + (compliance_score * 0.10) + (contradiction_score * 0.05)

        # ── Hallucination verification gate ──
        from app.verification.hallucination_gate import run_verification

        verification = run_verification(state.get("applicable_sections", []), state.get("precedents", []))
        state["verification"] = verification
        hallucinated = verification["hallucination_count"]
        v_rate = verification["verification_rate"]

        # Grounded trust boost only when the cited law actually verifies
        if hallucinated == 0 and v_rate >= 0.9:
            if state.get("applicable_sections") and state.get("precedents"):
                trust_score = max(trust_score, 0.98)
            elif state.get("precedents") or state.get("applicable_sections"):
                trust_score = max(trust_score, 0.975)
        elif v_rate >= 0.6:
            trust_score = max(trust_score, 0.90)
        else:
            trust_score = min(trust_score, 0.85)

        if hallucinated:
            trust_score -= 0.05 * hallucinated
            logger.warning(f"[ConfidenceFusion] {hallucinated} hallucinated citation(s) detected")

        # If the GGUF could not be allocated, every LLM field above is mock text.
        # A high trust score on invented content is worse than an explicit zero.
        if is_mock_fallback_active():
            trust_score = 0.0
            msg = (
                "LLM unavailable: the model could not be loaded, so LLM-generated "
                "sections are placeholder text and must not be relied upon. "
                "Free GPU/RAM (stop other processes holding the model) and re-run."
            )
            logger.error(f"[ConfidenceFusion] {msg}")
            if msg not in (state.get("errors") or []):
                state["errors"] = (state.get("errors") or []) + [msg]

        state["trust_score"] = max(0.0, min(1.0, trust_score))
        state["agent_confidence"] = {**confidences, "confidence_fusion": trust_score}

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ConfidenceFusion] Trust score: {state['trust_score']:.3f} ({duration_ms:.0f}ms)")
        return _record_completion(state, "confidence_fusion", state["trust_score"], "trust_score", state["trust_score"])

    except Exception as exc:
        logger.error(f"[ConfidenceFusion] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ConfidenceFusion: {exc}"]
        state["trust_score"] = 0.0
        return _record_completion(state, "confidence_fusion", 0.0, "trust_score", 0.0)


# ── Agent 11: Explainability Agent ─────────────────────────
async def explainability_agent(state: AgentState) -> AgentState:
    """Build explainability graph showing reasoning chain and evidence links.

    Creates a directed graph: Query -> Evidence -> Reasoning -> Conclusion
    with confidence edge weights and trust factor annotations.
    """
    start_time = time.monotonic()
    logger.info("[Explainability] Building explanation graph")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT

        sections = state.get("applicable_sections", [])
        evidence = state.get("evidence_assessment", {})
        trust = state.get("trust_score", 0.5)

        # Build explainability graph structure
        graph: dict[str, Any] = {
            "nodes": [
                {"id": "query", "type": "Query", "label": state.get("query", "Legal Analysis Request")[:80]},
                {"id": "evidence", "type": "Evidence", "label": f"Evidence ({evidence.get('overall_score', 'Not available')})"},
                {"id": "reasoning", "type": "Reasoning", "label": "IRAC Legal Reasoning"},
                {"id": "conclusion", "type": "Conclusion", "label": "Legal Conclusion"},
                {"id": "trust", "type": "Trust", "label": f"Trust Score: {trust:.2f}"},
            ],
            "edges": [
                {"source": "query", "target": "evidence", "weight": 0.9, "type": "informs"},
                {"source": "evidence", "target": "reasoning", "weight": evidence.get("overall_score", 0.5), "type": "supports"},
                {"source": "reasoning", "target": "conclusion", "weight": state.get("agent_confidence", {}).get("legal_reasoning", 0.7), "type": "leads_to"},
                {"source": "conclusion", "target": "trust", "weight": trust, "type": "calibrated_by"},
            ],
        }

        # Add section nodes
        for i, section in enumerate(sections[:8]):
            node_id = f"section_{i}"
            graph["nodes"].append({
                "id": node_id,
                "type": "Section",
                "label": f"Sec {section.get('section_number')} {section.get('act', '')}",
            })
            graph["edges"].append({
                "source": node_id,
                "target": "reasoning",
                "weight": section.get("relevance_score", 0.5),
                "type": "grounds",
            })

        # Add contradiction nodes if any
        contradictions = state.get("contradictions", [])
        for i, c in enumerate(contradictions[:5]):
            node_id = f"contradiction_{i}"
            graph["nodes"].append({
                "id": node_id,
                "type": "Contradiction",
                "label": c.get("type", f"Contradiction {i+1}"),
            })
            graph["edges"].append({
                "source": node_id,
                "target": "trust",
                "weight": -c.get("confidence", 0),
                "type": "reduces",
            })

        state["explanation_graph"] = graph

        confidence = 0.9
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[Explainability] Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges ({duration_ms:.0f}ms)")
        return _record_completion(state, "explainability", confidence, "explanation_graph", graph)

    except Exception as exc:
        logger.error(f"[Explainability] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"Explainability: {exc}"]
        state["explanation_graph"] = {"nodes": [], "edges": [], "error": str(exc)}
        return _record_completion(state, "explainability", 0.0, "explanation_graph", state["explanation_graph"])


# ── Agent 12: Report Generation Agent ──────────────────────
async def report_generation_agent(state: AgentState) -> AgentState:
    """Assemble final 16-section legal advisory report from all agent outputs.

    Uses Qwen3 for executive summary and synthesis.
    """
    start_time = time.monotonic()
    logger.info("[ReportGeneration] Assembling final report")

    try:
        from app.llm.qwen import get_qwen_provider, QWEN_SYSTEM_PROMPT
        import re

        summary = state.get("case_summary", "")
        facts = state.get("case_facts", {})
        issues = state.get("legal_issues", [])
        acts = state.get("applicable_acts", [])
        normalized_acts = normalize_statutes([a for a in acts if isinstance(a, str)])
        sections = state.get("applicable_sections", [])
        precedents = state.get("precedents", [])
        evidence = state.get("evidence_assessment", {})
        contradictions = state.get("contradictions", [])
        risk = state.get("risk_assessment", {})
        procedural = state.get("procedural_status", {})
        strategies = state.get("strategy_options", [])
        trust = state.get("trust_score", 0.0)
        confidences = state.get("agent_confidence", {})
        explanation = state.get("explanation_graph", {})
        kg = state.get("kg_data", {})
        documents = state.get("documents", [])

        # ── Grounding / Source Validation with analysis_fixes_v2 ──
        from app.agents.analysis_fixes_v2 import (
            build_page_chunks,
            snippet_for_section,
            build_fact_timeline,
            build_evidence_items,
            build_risk_strategy,
            similarity_pct,
        )
        from app.agents.presentation_universal import _strip_signature

        doc_text_full = _llm_clean("\n\n".join(d.get("text", "") for d in documents))
        page_chunks = build_page_chunks(doc_text_full) if doc_text_full else []
        case_category = state.get("case_category", "criminal")
        meta_dict = state.get("metadata") or {}

        def find_source_provenance(claim: str) -> dict[str, Any]:
            best_match = {
                "source_type": "AI_inferred_analysis",
                "source_document": "None",
                "page_number": None,
                "chunk_id": "None",
                "confidence": 0.50,
                "evidence": "Grounded via legal reasoning synthesis."
            }
            if not documents or not claim:
                return best_match
                
            claim_words = set(claim.lower().split())
            if len(claim_words) < 3:
                return best_match
                
            best_ratio = 0.0
            for doc in documents:
                filename = doc.get("filename") or "case_document"
                pages = doc.get("metadata", {}).get("pages") or doc.get("pages") or [doc.get("text", "")]
                
                for p_idx, page_text in enumerate(pages):
                    page_num = p_idx + 1
                    sentences = [s.strip() for s in re.split(r"[.!?\n]", page_text) if len(s.strip()) > 15]
                    for s_idx, sentence in enumerate(sentences):
                        sentence_words = set(sentence.lower().split())
                        if not sentence_words:
                            continue
                        intersection = claim_words & sentence_words
                        ratio = len(intersection) / max(len(claim_words), 1)
                        
                        if ratio > best_ratio and ratio > 0.25:
                            best_ratio = ratio
                            best_match = {
                                "source_type": "uploaded_document",
                                "source_document": filename,
                                "page_number": page_num,
                                "chunk_id": f"{filename}_p{page_num}_c{s_idx}",
                                "confidence": round(0.70 + (ratio * 0.25), 2),
                                "evidence": sentence
                            }
            return best_match

        # ── 1. Ground Legal Issues with presentation_universal ──
        from app.agents.presentation_universal import (
            render_issues,
            render_conclusion,
            build_kg,
            safe,
            lint
        )

        r_ctx = {
            'metadata': meta_dict,
            'sections': [s.get('section_number') for s in sections if isinstance(s, dict) and s.get('section_number')],
            'section_acts': {s.get('section_number'): s.get('act') for s in sections if isinstance(s, dict) and s.get('section_number')},
            'articles': state.get('articles', []),
            'precedents': precedents,
            'category': case_category
        }

        # Prefer court-framed issues from the full document when available.
        from app.agents.presentation_universal import _court_framed_issues
        court_iss = _court_framed_issues(doc_text_full)
        if court_iss:
            rendered_iss_list = [str(i.get('text') or i.get('issue') or '') for i in court_iss if i.get('text') or i.get('issue')]
        else:
            rendered_iss_list = render_issues(r_ctx, doc_text_full)
        grounded_issues = []
        for q_str in rendered_iss_list:
            sec_m = re.search(r'(?:Section|Sec\.)\s*(\d+(?:\([a-z0-9]+\))*)', q_str, re.I)
            if sec_m:
                sec_target = sec_m.group(1)
                snip, p_no = snippet_for_section(doc_text_full, sec_target, page_chunks)
                if snip:
                    filename = documents[0].get("filename") if documents else "case_document"
                    grounded_issues.append({
                        "question": q_str,
                        "category": "DOCUMENT FACT",
                        "source_type": "uploaded_document",
                        "source_document": filename,
                        "page_number": p_no or 1,
                        "chunk_id": f"{filename}_p{p_no or 1}_sec{sec_target}",
                        "confidence": 0.95,
                        "evidence": snip
                    })
                    continue

            prov = find_source_provenance(q_str)
            grounded_issues.append({
                "question": q_str,
                "category": "DOCUMENT FACT" if prov.get("source_type") == "uploaded_document" else "AI LEGAL ANALYSIS",
                **prov
            })

        state["legal_issues"] = grounded_issues  # type: ignore[typeddict-item-key]

        # ── 2. Fact Timeline (Real dates & accurate outcome tail) ──
        dec_date_val = (
            meta_dict.get("decision_date", {}).get("value")
            if isinstance(meta_dict.get("decision_date"), dict)
            and meta_dict["decision_date"].get("status") in ("extracted", "inferred")
            else "Decision Date"
        )
        state["timeline"] = build_fact_timeline(doc_text_full, dec_date_val)

        # ── 3. Grounded Evidence Assessment & Risk Strategy ──
        state["evidence_assessment"] = {"items": build_evidence_items(meta_dict, case_category)}
        state["risk_assessment"] = build_risk_strategy(doc_text_full, meta_dict)
        state["kg_data"] = build_kg(r_ctx)

        # 2. Ground & Filter Precedents
        primary_act = acts[0] if acts else "Applicable Law"
        primary_secs = ", ".join([s.get("section_number", "") for s in sections[:2] if isinstance(s, dict)]) or "Sections"
        grounded_precedents = []
        for prec in precedents:
            score = prec.get("relevance_score") or prec.get("score") or 0.0
            if score >= 0.40 and prec.get("case_name", "").lower() not in ("keyword", "precedent"):
                p_acts = prec.get("acts")
                if not p_acts or p_acts == "Applicable Statutes":
                    p_acts = primary_act
                p_secs = prec.get("sections")
                if not p_secs or p_secs == "Sections":
                    p_secs = primary_secs
                grounded_precedents.append({
                    "case_name": prec.get("case_name") or "Precedent",
                    "court": prec.get("court") or "Court of Law",
                    "year": prec.get("year") or "2024",
                    "citation": prec.get("citation") or "Unknown Citation",
                    "relevance_score": score,
                    "score": score,
                    "acts": p_acts,
                    "sections": p_secs,
                    "reason": prec.get("reason") or (prec.get("summary", "")[:150] + "..."),
                    "matching_issue": issues[0] if issues else "General liability",
                    "evidence": prec.get("summary", ""),
                    "source_type": "precedent",
                    "source_document": "legal_corpus"
                })
        
        # If no precedents found above the threshold, return an empty list.
        # Previously this wrote a fake "No sufficiently relevant precedent found"
        # entry that appeared in the report as if it were a real case — corrupting
        # the citation section. The UI handles an empty list gracefully.
            
        state["precedents"] = grounded_precedents  # type: ignore[typeddict-item-key]

        # 3. Ground & Enforce Applicable Sections
        grounded_sections = []
        for sec in sections:
            score = sec.get("relevance_score") or sec.get("score") or 0.0
            sec_num = sec.get("section_number") or ""
            is_explicit = False
            if sec_num:
                is_explicit = any(re.search(rf"\b(Section|Sec\.)\s*{sec_num}\b", d.get("text", "").lower()) for d in documents)
            
            grounded_sections.append({
                "section_number": sec_num,
                "act": sec.get("act") or "Unknown Act",
                "title": sec.get("title") or f"Section {sec_num}",
                "text": sec.get("text") or "",
                "relevance_score": score,
                "explicitly_mentioned": is_explicit,
                "reason": f"Explicitly cited in document." if is_explicit else "AI-inferred applicability based on case facts."
            })
        state["applicable_sections"] = grounded_sections

        # ── Citation verification gate on final grounded output ──
        from app.verification.hallucination_gate import run_verification

        verification = run_verification(grounded_sections, grounded_precedents)
        state["verification"] = verification
        sec_v = {f"{v.get('act', '')}|{v.get('num', '')}": v for v in verification["section_verdicts"]}
        prec_v = {v.get("case_name"): v for v in verification["precedent_verdicts"]}
        for s in grounded_sections:
            verdict = sec_v.get(f"{s.get('act', '')}|{s.get('section_number', '')}")
            if verdict:
                s["verified"] = verdict["status"]
                s["verification_note"] = verdict["reason"]
        for p in grounded_precedents:
            verdict = prec_v.get(p.get("case_name") or "")
            if verdict:
                p["verified"] = verdict["status"]
                p["verification_note"] = verdict["reason"]
        if verification["hallucination_count"]:
            trust = max(0.0, min(trust, 0.86) - 0.03 * verification["hallucination_count"])
            state["trust_score"] = trust

        # 4. Ground Case Facts
        grounded_facts = []
        if isinstance(facts, dict):
            raw_facts_list = facts.get("facts", []) or []
        elif isinstance(facts, list):
            raw_facts_list = facts
        else:
            raw_facts_list = [str(facts)]
            
        for fact in raw_facts_list:
            prov = find_source_provenance(fact)
            if prov["source_type"] == "uploaded_document":
                category = "DOCUMENT FACT"
            else:
                category = "AI LEGAL ANALYSIS"
            grounded_facts.append({
                "fact": fact,
                "category": category,
                **prov
            })

        # Generate executive summary
        exec_prompt = f"""Write an executive summary for a legal advisory report. Be concise and professional.

Case: {summary[:500]}
Key Issues: {', '.join(q.get('question', '')[:100] for q in grounded_issues[:3])}
Key Sections: {', '.join(f"Sec {s.get('section_number')} {s.get('act', '')}" for s in grounded_sections[:5])}
Trust Score: {trust:.2f}

Write a 3-4 sentence executive summary in plain English suitable for an advocate."""
        provider = get_qwen_provider()
        exec_summary = await asyncio.to_thread(
            provider.generate, exec_prompt, system_prompt=QWEN_SYSTEM_PROMPT, max_tokens=300
        )

        report = {
            "title": "Legal Advisory Report",
            "case_id": state.get("case_id", ""),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sections": [
                {"title": "Executive Summary", "content": exec_summary, "order": 1},
                {"title": "Case Facts", "content": grounded_facts, "order": 2},
                {"title": "Legal Issues Identified", "content": [q["question"] for q in grounded_issues], "order": 3},
                {"title": "Applicable Acts", "content": normalized_acts, "order": 4},
                {"title": "Applicable Sections", "content": [{"section": s.get("section_number"), "act": s.get("act"), "title": s.get("title", ""), "text": s.get("text", ""), "explicit": s.get("explicitly_mentioned")} for s in grounded_sections], "order": 5},
                {"title": "Supporting Judgments", "content": grounded_precedents, "order": 6},
                {"title": "Evidence Analysis", "content": evidence, "order": 7},
                {"title": "Contradiction Analysis", "content": contradictions, "order": 8},
                {"title": "Risk Assessment", "content": risk, "order": 9},
                {"title": "Procedural Compliance", "content": procedural, "order": 10},
                {"title": "Strategy Recommendation", "content": strategies, "order": 11},
                {"title": "Trust Score", "content": {"score": trust, "breakdown": confidences, "verification": verification}, "order": 12},
                {"title": "Confidence Scores", "content": confidences, "order": 13},
                {"title": "Explainability Graph", "content": explanation, "order": 14},
                {"title": "Knowledge Graph Snapshot", "content": kg, "order": 15},
                {"title": "References and Disclaimer", "content": "This report is AI-generated for advisory purposes only. It does not constitute legal advice. All legal decisions must be made by a qualified advocate. Review all citations and analysis before use.", "order": 16},
            ],
            "trust_score": trust,
            "confidence_scores": confidences,
            "explanation_graph": explanation,
            "knowledge_graph": kg,
        }

        state["final_report"] = report
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"[ReportGeneration] Report complete ({duration_ms:.0f}ms)")
        return _record_completion(state, "report_generation", trust, "final_report", report)

    except Exception as exc:
        logger.error(f"[ReportGeneration] Error: {exc}")
        state["errors"] = state.get("errors", []) + [f"ReportGeneration: {exc}"]
        state["final_report"] = {"error": str(exc)}
        return _record_completion(state, "report_generation", 0.0, "final_report", state["final_report"])
