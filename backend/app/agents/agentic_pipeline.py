"""Agentic Self-Correcting Extraction Pipeline (LexOrch-KG).

Four lightweight LLM agents replace brittle regex / dictionary decision rules:

    AGENT 1  Noise Filter        clean_text_with_llm()
    AGENT 2  Context Resolver    resolve_act_from_context(), classify_judgment_date()
    AGENT 3  Speaker Attribution attribute_counsel_arguments()
    AGENT 4  Critic              critic_extraction()

Guarantees implemented here:
  * Every agent emits STRICT JSON (validated by a balanced-brace parser, not a
    heurist regex) or returns a pre-agreed fallback.
  * Every agent is wrapped in try/except; on any failure the caller falls back
    to the raw/deterministic extraction (nothing is fabricated).
  * LLM calls are lightweight (fast model for agents 1-3, strong model for the
    Critic) and run off
    the event loop with asyncio.to_thread.
  * provider= may be injected for testing (a fake provider keeps tests
    deterministic and offline).
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from loguru import logger

from app.llm.routing import get_fast_provider, get_strong_provider

AGENTIC_SYSTEM_PROMPT = (
    "You are a precise legal-document extraction agent for LexOrch-KG. "
    'Reply with STRICT JSON ONLY and nothing else: no prose, no code fences, no comments.'
)


def _fit_context(text: str, limit: int) -> str:
    """Keep an agent prompt within the local model's context budget."""
    if len(text) <= limit:
        return text
    head = limit // 2
    return f"{text[:head]}\n...[context truncated]...\n{text[-(limit - head):]}"


def _get_provider(provider: Any = None) -> Any:
    """Return the injected provider or the fast default (simple agents)."""
    return provider if provider is not None else get_fast_provider()


def _get_strong_provider(provider: Any = None) -> Any:
    """Return the injected provider or the strong default (Critic agent)."""
    return provider if provider is not None else get_strong_provider()


def _extract_json(text: str) -> Any:
    """Robustly parse the first JSON object/array from an LLM reply.

    Handles markdown fences and leading/trailing prose by scanning each '{'/'['
    candidate with a real JSON decoder (balanced-brace aware) rather than a
    fragile regex. Returns None when no valid JSON exists.
    """
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch not in "{[":
            continue
        try:
            obj, _ = decoder.raw_decode(t[i:])
        except json.JSONDecodeError:
            continue
        return obj
    return None


async def _call_json(
    provider: Any,
    prompt: str,
    system_prompt: str = AGENTIC_SYSTEM_PROMPT,
    max_tokens: int = 600,
    temperature: float = 0.0,
    output_schema: dict[str, Any] | None = None,
) -> Any:
    """Run a lightweight, deterministic JSON-producing LLM call (off thread).

    Returns the parsed JSON structure, or None if the call/parse fails.
    """
    try:
        if hasattr(provider, "generate_structured"):
            return await asyncio.to_thread(
                provider.generate_structured,
                prompt=prompt,
                output_schema=output_schema or {"type": "object"},
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        response = await asyncio.to_thread(
            provider.generate,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return _extract_json(response)
    except Exception as exc:  # noqa: BLE001 - every agent must degrade gracefully
        logger.warning(f"Agentic pipeline LLM call failed: {exc}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — NOISE FILTER
# ══════════════════════════════════════════════════════════════════════════════
async def clean_text_with_llm(text: str, provider: Any = None) -> str:
    """Strip academic/fictional scaffolding and return the core legal record.

    The LLM removes disclaimers ("ACADEMIC CASE STUDY", "ILLUSTRATIVE ONLY",
    "fictional case file", "not an official court record"), "Page X of Y"
    furniture, and educational checklists ("End note...", "Checklist for an
    authentic case record", "Key learning points"). Never paraphrases.

    On any failure, returns the original text unchanged (fallback never drops
    legal content).
    """
    if not text:
        return text or ""
    provider = _get_provider(provider)
    prompt = f"""Clean the following legal document for extraction.

Remove ONLY these editorial/scholarly fixtures:
- Academic/fictional disclaimers such as "ACADEMIC CASE STUDY", "ILLUSTRATIVE
  ONLY", "fictional case file", "not an official court record".
- Page furniture such as "Page X of Y".
- End-of-document notes like "End note: This is an expanded educational case
  study..." and "Checklist for an authentic case record...".
- Educational recap sections like "Key learning points...".

Keep EVERYTHING else verbatim - parties, sections, dates, reasoning, orders,
exhibits, signatures. Do not paraphrase, summarize, reorder, or invent.

Return STRICT JSON: {{"cleaned_text": "the cleaned document"}}

DOCUMENT:
{_fit_context(text, 50000)}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {"cleaned_text": {"type": "string"}},
            "required": ["cleaned_text"],
        },
    )
    cleaned = (
        str(parsed.get("cleaned_text", "")).strip() if isinstance(parsed, dict) else ""
    )
    if not cleaned:
        logger.info("Noise filter produced empty output; keeping original text.")
        return text
    return cleaned


async def clean_document_text(text: str, provider: Any = None) -> str:
    """Public Agent 1 entry point used by ingestion and tests."""
    return await clean_text_with_llm(text, provider)


# ══════════════════════════════════════════════════════════════════════════════
# OCR REPAIR (pre-processing, runs before case_understanding)
# ══════════════════════════════════════════════════════════════════════════════
_OCR_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")
# Characters fused with the wrong neighbour are the clearest scan fingerprint:
# "224of", "2017can", "thecourt". Legal text otherwise keeps digits and words
# apart (the "Section 482" case), so a small rate of fusion means real damage.
_OCR_FUSION_RE = re.compile(r"\b\d+[a-z]{2,}\b|\b[a-z]{2,}\d+\b")
_OCR_ACRONYM_RE = re.compile(r"^[A-Z]{2,6}$")


def _looks_like_ocr_noise(text: str) -> bool:
    """Cheap heuristic: did scanning mangle this text badly enough to repair?

    Avoids paying an LLM round-trip for the common case of a clean digital
    judgment. Triggers on replacement/mojibake characters, on a meaningful rate
    of digit-letter fusion, or on vowel-less "words" that prose never produces.
    """
    sample = (text or "")[:6000]
    if not sample:
        return False
    if "\ufffd" in sample or "Ã" in sample:
        return True
    words = _OCR_WORD_RE.findall(sample)
    if len(words) < 100:
        return False
    if len(_OCR_FUSION_RE.findall(sample.lower())) / len(words) >= 0.02:
        return True
    vowel_less = sum(
        1
        for w in words
        if len(w) >= 5 and not _OCR_ACRONYM_RE.match(w) and not re.search(r"[aeiou]", w.lower())
    )
    return vowel_less / len(words) >= 0.03


def _split_for_repair(text: str, chunk_size: int) -> list[str]:
    """Split on line boundaries so a window never cuts a word in half."""
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            nl = text.rfind("\n", start + chunk_size // 2, end)
            if nl != -1:
                end = nl + 1
        parts.append(text[start:end])
        start = end
    return parts


async def _repair_ocr_chunk(chunk: str, provider: Any) -> str:
    prompt = f"""You are an expert legal document cleaner for Indian court
judgments. The text below was scanned and then OCR'd, so it contains severe
character-recognition errors.

Correct the damage using legal context. Typical cases:
- Section numbers misread as letters: "52g" or "52S" -> "528"; "1o5" -> "105".
- Missing spaces between words: "224of" -> "224 of", "thecourt" -> "the court".
- Confused characters: "CrounOs" -> "Grounds", "Hioh" -> "High", "cou(" ->
  "Court", "opvoi" -> "copy", "copplsl" -> "complex", "rn" -> "m".
- Broken words: "pro_ceJdings" -> "proceedings", "tu'oda-ys" -> "two days".

Rules:
1. Fix all spelling, OCR and spacing errors using the legal context.
2. Do NOT change the legal meaning, facts, dates, section numbers or case names.
3. Never paraphrase, summarise, translate, reorder, or add commentary.

Return STRICT JSON ONLY: {{"cleaned_text": "the repaired text"}}

SCANNED TEXT:
{chunk}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=max(600, len(chunk) // 2),
        output_schema={
            "type": "object",
            "properties": {"cleaned_text": {"type": "string"}},
            "required": ["cleaned_text"],
        },
    )
    cleaned = str(parsed.get("cleaned_text", "")).strip() if isinstance(parsed, dict) else ""
    # Content-loss guard: a window that comes back at under half its size was
    # summarised or truncated, which is worse than the OCR noise it fixed.
    if not cleaned or len(cleaned) < 0.5 * len(chunk):
        return chunk
    return cleaned


async def clean_ocr_text_with_llm(
    text: str,
    provider: Any = None,
    force: bool = False,
    chunk_size: int = 6000,
    max_chars: int | None = None,
) -> str:
    """Repair severe OCR damage before the analysis agents read the document.

    A badly scanned PDF poisons every downstream extractor, so this pre-pass
    translates garbled text back into clean text. It fires only when the text
    actually looks damaged (unless ``force``); clean documents are returned
    untouched. The document is repaired in bounded windows so one long judgment
    never depends on a single truncation-prone completion, and any window that
    fails or shrinks suspiciously falls back to its original text.

    ``max_chars`` caps how much of the document is sent to the model (0/None =
    the whole document). When a cap is set only the leading ``max_chars`` are
    repaired and the untouched tail is re-appended, so the caption/issues band
    (which drives downstream extraction) is fixed without paying to repair the
    full body.
    """
    if not text:
        return text or ""
    if not force and not _looks_like_ocr_noise(text):
        return text
    provider = _get_provider(provider)
    head, tail = text, ""
    if max_chars and 0 < max_chars < len(text):
        head, tail = text[:max_chars], text[max_chars:]
    parts = _split_for_repair(head, chunk_size)
    repaired = [await _repair_ocr_chunk(part, provider) for part in parts]
    cleaned = "\n".join(repaired) + tail
    if cleaned == text:
        return text
    logger.info(
        f"[OCRRepair] repaired scanned text: {len(text)} -> {len(cleaned)} chars "
        f"(head {len(head)})"
    )
    return cleaned



# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — CONTEXT RESOLVER (statutes & dates)
# ══════════════════════════════════════════════════════════════════════════════
def _context_window(text: str, sec: str, words: int = 50) -> str:
    """Return ±words words surrounding the first "Section <sec>" mention,
    or an empty string when the section is not found in the document."""
    needle = f"section {sec}"
    idx = text.lower().find(needle)
    if idx == -1:
        return ""
    start = max(0, idx - words * 6)
    end = min(len(text), idx + len(needle) + words * 6)
    return text[start:end].replace("\n", " ").strip()


async def resolve_act_from_context(
    sections: list[str], text: str, provider: Any = None
) -> dict[str, str]:
    """Resolve each section number to its full Act name + year using only the
    surrounding ~50 words of context. One batched, lightweight LLM call.

    Returns {section: "Full Act, YYYY"}. A section whose context names no Act
    is simply absent (never coerced to a placeholder). """
    if not sections:
        return {}
    provider = _get_provider(provider)
    lines = []
    for sec in sections:
        ctx = _context_window(text, str(sec))
        if ctx:
            lines.append(f"- SECTION: {sec}\n  CONTEXT: {ctx}")
    if not lines:
        return {}
    prompt = (
        "For each SECTION below, identify the FULL NAME AND YEAR of the Act it "
        "belongs to.\n"
        "Based STRICTLY on the provided CONTEXT for that section. Do not "
        "hallucinate: if the context does not name an Act, set the act to null.\n"
        "Return STRICT JSON: {\"resolutions\": [{\"section\": \"...\", "
        "\"act\": \"Full Act Name, Year\" or null, \"in_context\": true}]}\n\n"
        + "\n".join(lines)
    )
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {
                "resolutions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string"},
                            "act": {"type": ["string", "null"]},
                        },
                        "required": ["section", "act"],
                    },
                }
            },
            "required": ["resolutions"],
        },
    )
    if not parsed:
        return {}
    result: dict[str, str] = {}
    for item in parsed.get("resolutions", []) if isinstance(parsed, dict) else []:
        sec = str(item.get("section", "")).strip()
        act = str(item.get("act", "") or "").strip()
        if sec and act and act.lower() != "null":
            result[sec] = act
    return result


_YEAR_RE = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")


def _split_act_and_year(act: str) -> tuple[str, str]:
    """Split "Code of Criminal Procedure, 1973" into ("Code of Criminal
    Procedure", "1973"). An Act with no year returns an empty year."""
    match = re.search(r"\b(1[6-9]\d{2}|20\d{2})\b", act)
    if not match:
        return act.strip(" ,"), ""
    return act[: m.start()].strip(" ,") if (m := match) else act, m.group(1)


async def resolve_act_from_snippet(
    section: str, context: str, provider: Any = None
) -> dict[str, str]:
    """Identify the Act a section belongs to from its number and context snippet.

    Given the section number and the ~50 words surrounding it, return the full
    Act name and year. Never guesses an Act the context does not name - empty
    strings are returned instead.
    """
    provider = _get_provider(provider)
    prompt = f"""I am extracting a legal statute. Here is the section number and
the 50 words of text surrounding it:

SECTION: {section}
CONTEXT: {context}

Based STRICTLY on this context, what is the full name and year of the Act this
section belongs to? If the context does not name the Act, leave act_name and
year empty - never guess.

Return STRICT JSON ONLY:
{{"section": "...", "act_name": "...", "year": "..."}}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=300,
        output_schema={
            "type": "object",
            "properties": {
                "section": {"type": "string"},
                "act_name": {"type": "string"},
                "year": {"type": "string"},
            },
            "required": ["section", "act_name", "year"],
        },
    )
    if not isinstance(parsed, dict):
        return {"section": str(section), "act_name": "", "year": ""}
    return {
        "section": str(parsed.get("section", section) or section).strip(),
        "act_name": str(parsed.get("act_name", "") or "").strip(),
        "year": str(parsed.get("year", "") or "").strip(),
    }


async def resolve_acts_detailed(
    sections: list[str], text: str, provider: Any = None
) -> dict[str, dict[str, str]]:
    """Batched form of :func:`resolve_act_from_snippet`.

    Returns {section: {"act_name": ..., "year": ...}}. A section whose context
    names no Act is absent. An Act returned as one string ("Code of Criminal
    Procedure, 1973") is split into name and trailing four-digit year.
    """
    if not sections:
        return {}
    provider = _get_provider(provider)
    lines = []
    for sec in sections:
        ctx = _context_window(text, str(sec))
        if ctx:
            lines.append(f"SECTION: {sec}\nCONTEXT: {ctx}")
    if not lines:
        return {}
    block = "\n\n".join(lines)
    prompt = f"""I am extracting legal statutes. For each section below you are
given its number and the 50 words of text surrounding it.

Based STRICTLY on that context, give the full name and year of the Act the
section belongs to. If the context does not name an Act, leave act_name and year
empty - never guess.

Return STRICT JSON ONLY:
{{"resolutions": [{{"section": "...", "act_name": "...", "year": "..."}}]}}

SECTIONS:
{block}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=800,
        output_schema={
            "type": "object",
            "properties": {
                "resolutions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string"},
                            "act_name": {"type": "string"},
                            "year": {"type": "string"},
                        },
                        "required": ["section", "act_name"],
                    },
                }
            },
            "required": ["resolutions"],
        },
    )
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for item in parsed.get("resolutions", []):
        sec = str(item.get("section", "")).strip()
        name = str(item.get("act_name", "") or "").strip()
        year = str(item.get("year", "") or "").strip()
        if not name:
            act = str(item.get("act", "") or "").strip()
            if act and act.lower() != "null":
                match = re.search(r"\b(1[6-9]\d{2}|20\d{2})\b", act)
                if match:
                    year = year or match.group(1)
                    name = act[: match.start()].strip(" ,")
                else:
                    name = act
        if sec and name:
            result[sec] = {"act_name": name, "year": year}
    return result


# ══════════════════════════════════════════════════════════════════════════════
# HEADER BLOCK CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════
def _split_header_blocks(text: str, max_blocks: int, head_chars: int = 8000) -> list[str]:
    """Split the top of a judgment into paragraphs (falling back to lines)."""
    head = (text or "")[:head_chars]
    blocks = [b.strip() for b in re.split(r"\n\s*\n", head) if b.strip()]
    if len(blocks) <= 1:
        blocks = [ln.strip() for ln in head.splitlines() if ln.strip()]
    return blocks[:max_blocks]


async def classify_header_blocks(
    text: str, provider: Any = None, max_blocks: int = 25
) -> list[str]:
    """Keep only the Legal Content blocks at the top of a judgment.

    Reporter permissions, fair copy requests, circulation notes and copyright
    boilerplate sit above the real judgment but break label-anchored extraction.
    Each block is classified as "Administrative Metadata" or "Legal Content" and
    only the legal blocks are returned. On any failure every block is returned,
    so content is never dropped because the LLM misbehaved.
    """
    blocks = _split_header_blocks(text, max_blocks)
    if len(blocks) <= 1:
        return blocks
    provider = _get_provider(provider)
    listing = "\n".join(f"[{i}] {b}" for i, b in enumerate(blocks))
    prompt = f"""Read the following text blocks from the top of a legal judgment.
Classify each block as either "Administrative Metadata" (e.g. reporter
permissions, fair copy requests, circulation notes, copyright notices) or
"Legal Content" (e.g. facts, arguments, issues, orders).

Return STRICT JSON ONLY: {{"legal_content": [<indices of Legal Content blocks>]}}

BLOCKS:
{listing}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=400,
        output_schema={
            "type": "object",
            "properties": {"legal_content": {"type": "array", "items": {"type": "integer"}}},
            "required": ["legal_content"],
        },
    )
    if not isinstance(parsed, dict) or "legal_content" not in parsed:
        return blocks
    keep: list[str] = []
    for idx in parsed.get("legal_content", []):
        try:
            i = int(idx)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(blocks):
            keep.append(blocks[i])
    return keep or blocks


_DATES_PROMPT = """Extract EVERY date present in the document below.

For each date, also capture the surrounding sentence (the sentence it belongs to).
Classify each date's ROLE from one of: FIR | INCIDENT | EVENT | JUDGMENT
(e.g. an FIR registration date is FIR; the operative/decision date is JUDGMENT).

Return STRICT JSON:
{{"dates": [{{"date": "...", "sentence": "...", "role": "FIR|INCIDENT|EVENT|JUDGMENT"}}]}}

If the document has no dates, return {{"dates": []}}.

DOCUMENT TAIL (signature/operative region preferred):
{tail}"""


async def classify_judgment_date(text: str, provider: Any = None) -> str | None:
    """Classify all dates in the document by role and return the JUDGMENT date.

    Only one date is returned (the decision date). Returns None when no date is
    classified as JUDGMENT, letting the caller keep its deterministic value.
    """
    if not text:
        return None
    provider = _get_provider(provider)
    parsed = await _call_json(
        provider,
        _DATES_PROMPT.format(tail=_fit_context(text[-40000:], 40000)),
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {
                "dates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "sentence": {"type": "string"},
                            "role": {"type": "string"},
                        },
                        "required": ["date", "sentence", "role"],
                    },
                }
            },
            "required": ["dates"],
        },
    )
    if not isinstance(parsed, dict):
        return None
    judgment_dates = [
        d.get("date", "").strip()
        for d in parsed.get("dates", [])
        if isinstance(d, dict) and str(d.get("role", "")).upper() == "JUDGMENT"
    ]
    if not judgment_dates:
        return None
    return judgment_dates[-1]


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — SPEAKER ATTRIBUTION (counsel submissions)
# ══════════════════════════════════════════════════════════════════════════════
async def attribute_counsel_arguments(
    petitioner_args: list[str],
    respondent_args: list[str],
    source_text: str | None = None,
    provider: Any = None,
) -> dict[str, list[str]]:
    """Assign every argument to the correct column using textual speaker cues
    (e.g. "Learned counsel for the petitioner", "The State argues") - not section
    headers alone.

    Each argument is tagged with an id so the LLM can never swap two columns by
    reordering. Returns {'petitioner_args': [...], 'respondent_args': [...]}.
    On failure, returns the inputs unchanged (raw extraction).
    """
    provider = _get_provider(provider)
    entries: list[tuple[int, str]] = []
    for pid, arg in enumerate(petitioner_args):
        entries.append((pid, arg))
    for rid, arg in enumerate(respondent_args):
        entries.append((1000 + rid, arg))  # ids keeps columns distinct
    if not entries:
        return {"petitioner_args": list(petitioner_args), "respondent_args": list(respondent_args)}

    arg_lines = "\n".join(f"[{aid}] {a}" for aid, a in entries)
    src = _fit_context(source_text or "", 35000)
    prompt = f"""You are assigning counsel arguments to columns. NEVER swap them.

Each argument is prefixed as "[id] text". Assign by SPEAKER/SECTION cue ONLY:
- Arguments favouring or spoken for the Petitioner/Plaintiff/Appellant (e.g.
  "Learned counsel for the petitioner submits", "Mr. X for the Petitioner",
  "Petitioner's Submissions") go to petitioner.
- Arguments favouring or spoken for the Respondent/State/Defence (e.g. "The
  State argues", "Learned counsel for the respondent", "Respondent's
  Submissions") go to respondent.
- When a cue is ambiguous, prefer the party the argument supports.

Return STRICT JSON: {{"petitioner_args": [ids...], "respondent_args": [ids...]}}

SOURCE TEXT (for context):
{src}

ARGUMENTS:
{arg_lines}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {
                "petitioner_args": {"type": "array", "items": {"type": "integer"}},
                "respondent_args": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["petitioner_args", "respondent_args"],
        },
    )
    if not isinstance(parsed, dict):
        # Fallback: keep the raw extraction exactly as received.
        return {"petitioner_args": list(petitioner_args), "respondent_args": list(respondent_args)}

    arg_by_id = {aid: a for aid, a in entries}

    def _resolve(ids: Any) -> list[str]:
        out: list[str] = []
        if isinstance(ids, list):
            for raw in ids:
                aid = int(str(raw).strip("[] ")) if str(raw).strip("[] ").isdigit() else -1
                if aid in arg_by_id and arg_by_id[aid] not in out:
                    out.append(arg_by_id[aid])
        return out

    pet = _resolve(parsed.get("petitioner_args"))
    resp = _resolve(parsed.get("respondent_args"))
    # Only trust the LLM split when every argument landed somewhere; otherwise
    # keep the original (a dropped argument is worse than an unattributed one).
    if len(pet) + len(resp) != len(entries):
        return {"petitioner_args": list(petitioner_args), "respondent_args": list(respondent_args)}
    return {"petitioner_args": pet, "respondent_args": resp}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — CRITIC (self-correction / reflexion)
# ══════════════════════════════════════════════════════════════════════════════
# The court's own dispositive/reasoning language. An "issue" is the legal
# question; once a phrase like "We hold" bleeds in, the extractor has captured
# the judgment instead. Matched case-insensitively.
JUDICIAL_REASONING_PHRASES = (
    "we hold",
    "the court finds",
    "therefore, the petition is allowed",
    "in the result",
)


def clean_issues_deterministic(issues: list[str]) -> list[str]:
    """Rule-based issue cleanup that needs no LLM.

    An issue is the legal question; anything long or carrying the court's own
    reasoning is a judgment, not an issue. Over-long issues are truncated at the
    first question mark, and an issue that trails into judicial reasoning is cut
    back to its last question mark. Blank entries are dropped, and the standard
    administrative reporting heads ("Whether Reporters of Local Papers may be
    allowed to see the judgment?") are dropped because they are not legal issues.
    """
    from app.agents.presentation_universal import _ADMIN_QUESTION_RE

    cleaned: list[str] = []
    for raw in issues:
        issue = str(raw).strip()
        if not issue:
            continue
        if _ADMIN_QUESTION_RE.search(issue):
            continue
        if len(issue.split()) > 100 and "?" in issue:
            issue = issue.split("?")[0].strip() + "?"
        low = issue.lower()
        if any(phrase in low for phrase in JUDICIAL_REASONING_PHRASES) and "?" in issue:
            issue = issue[: issue.rfind("?") + 1].strip()
        cleaned.append(issue)
    return cleaned


# A meaningful legal query must name an area of law; a blank or boilerplate
# query ("Client: .") carries none and starves the RAG pipeline of a signal.
_LEGAL_QUERY_KEYWORDS = ("petition", "appeal", "bail", "quash", "section", "act")


def validate_understanding_query(query: str) -> bool:
    """Quality gate for a case-understanding query.

    Returns False for empty/too-short strings, or ones that name no legal
    keyword - the two failure modes that leave the RAG pipeline with nothing to
    retrieve and collapse the trust score.
    """
    q = (query or "").strip().lower()
    return len(q) >= 20 and any(word in q for word in _LEGAL_QUERY_KEYWORDS)


async def recover_from_ocr(text: str, provider: Any = None) -> dict[str, str]:
    """Header/footer-only recovery for badly OCR'd documents.

    When the body is garbled a full read fails, but the caption band (top) and
    the final order (bottom) usually survive OCR intact. This asks for just
    those, so a degraded document still yields a usable case name, date and
    outcome instead of a blank understanding.
    """
    provider = _get_provider(provider)
    head = text[:1500]
    tail = text[-1500:] if len(text) > 1500 else text
    prompt = f"""The document text appears to have severe OCR errors or formatting
issues. Ignore the garbled body. Look ONLY at the header (top) and the Final
Order (bottom) of the document below.

Extract:
- case_name: the case caption ("X v. Y" or "X vs Y")
- judgment_date: the judgment/decision date
- final_order: the final order, e.g. "Bail granted", "Petition allowed"

Return STRICT JSON: {{"case_name": "...", "judgment_date": "...", "final_order": "..."}}

HEADER:
{head}

FINAL ORDER:
{tail}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=600,
        output_schema={
            "type": "object",
            "properties": {
                "case_name": {"type": "string"},
                "judgment_date": {"type": "string"},
                "final_order": {"type": "string"},
            },
        },
    )
    if not isinstance(parsed, dict):
        return {"case_name": "", "judgment_date": "", "final_order": ""}
    return {
        "case_name": str(parsed.get("case_name") or "").strip(),
        "judgment_date": str(parsed.get("judgment_date") or "").strip(),
        "final_order": str(parsed.get("final_order") or "").strip(),
    }


async def critic_issues(issues: list[str], provider: Any = None) -> list[str]:
    """Issue Critic: truncate every issue to ONLY the legal question (an issue
    should rarely exceed 2 sentences). Reasoning/analysis is removed."""
    if not issues:
        return issues
    # Deterministic pre-pass: strip obvious judicial-reasoning bleed reliably,
    # even if the LLM call below fails or returns an unusable shape.
    pre_cleaned = clean_issues_deterministic(issues)
    provider = _get_strong_provider(provider)
    prompt = f"""Review these extracted Legal Issues.

For each issue: if it contains the court's reasoning or analysis, TRUNCATE it
to ONLY the legal question. An issue should rarely exceed 2 sentences.

Return STRICT JSON: {{"issues": ["..."]}}

ISSUES:
{chr(10).join(f"- {i}" for i in pre_cleaned)}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {"issues": {"type": "array", "items": {"type": "string"}}},
            "required": ["issues"],
        },
    )
    if isinstance(parsed, dict):
        cleaned = [str(i).strip() for i in parsed.get("issues", []) if str(i).strip()]
        if len(cleaned) == len(pre_cleaned):
            return cleaned
    return pre_cleaned


async def critic_strengths(
    strengths: list[str], text: str, provider: Any = None
) -> list[str]:
    """Strengths Critic: if a strength is a generic fallback ("No favorable
    findings extracted"), re-read the ANALYSIS AND REASONING section of the
    source and extract the court's actual favorable findings."""
    provider = _get_strong_provider(provider)
    has_placeholder = any(
        not s.strip() or "no " in s.lower()[:40] or s.lower().startswith("none")
        for s in strengths
    )
    # A non-empty, grounded strengths list needs no re-read.
    if strengths and not has_placeholder:
        return strengths
    prompt = f"""Read the "ANALYSIS AND REASONING" section of the document below and
extract the Court's actual favorable findings for the Petitioner/Plaintiff.

RULES:
- Extract findings VERBATIM or as close summaries as the text allows.
- Only findings that favour the Petitioner/Plaintiff. Never invent content.
- If there are no favorable findings, return {{"strengths": []}} (an empty list,
  never a placeholder).

Return STRICT JSON: {{"strengths": ["..."]}}

DOCUMENT:
{_fit_context(text, 50000)}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {"strengths": {"type": "array", "items": {"type": "string"}}},
            "required": ["strengths"],
        },
    )
    if isinstance(parsed, dict):
        recovered = [str(s).strip() for s in parsed.get("strengths", []) if str(s).strip()]
        if recovered:
            return recovered
    return [s for s in strengths if s.strip()]


async def critic_strengths_and_gaps(
    strengths: list[str],
    gaps: list[str],
    text: str,
    provider: Any = None,
) -> dict[str, list[str]]:
    """Critic pass for both party strengths and potential gaps."""
    provider = _get_strong_provider(provider)
    prompt = f"""Review the Analysis and Reasoning section below.

Extract only document-grounded findings:
- key_strengths: findings favorable to the petitioner/applicant
- potential_gaps: weaknesses, risks, or adverse findings affecting that party
- Never return generic fallback text.
- Return empty arrays when the source contains no supported finding.

Return STRICT JSON:
{{"key_strengths": ["..."], "potential_gaps": ["..."]}}

CURRENT STRENGTHS:
{json.dumps(strengths)}

CURRENT GAPS:
{json.dumps(gaps)}

SOURCE:
{_fit_context(text, 50000)}"""
    parsed = await _call_json(
        provider,
        prompt,
        max_tokens=1500,
        output_schema={
            "type": "object",
            "properties": {
                "key_strengths": {"type": "array", "items": {"type": "string"}},
                "potential_gaps": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["key_strengths", "potential_gaps"],
        },
    )
    if not isinstance(parsed, dict):
        return {"key_strengths": list(strengths), "potential_gaps": list(gaps)}
    return {
        "key_strengths": [
            str(item).strip() for item in parsed.get("key_strengths", []) if str(item).strip()
        ],
        "potential_gaps": [
            str(item).strip() for item in parsed.get("potential_gaps", []) if str(item).strip()
        ],
    }


async def critic_extraction(
    result: dict[str, Any], text: str, provider: Any = None
) -> dict[str, Any]:
    """Run the Critic over a partial extraction (issues + strengths + gaps).
    Returns the corrected copy; the original is unchanged if any critic fails."""
    corrected = dict(result)
    try:
        issues = result.get("issues") or []
        if issues:
            corrected["issues"] = await critic_issues([str(i) for i in issues], provider)
        strengths = result.get("strengths") or []
        if isinstance(strengths, list):
            corrected["strengths"] = await critic_strengths(
                [str(s) for s in strengths], text, provider
            )
    except Exception as exc:  # noqa: BLE001 - critic must never break the pipeline
        logger.warning(f"Critic failed, keeping original extraction: {exc}")
        return dict(result)
    return corrected


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
async def run_agentic_pipeline(
    text: str,
    sections: list[str] | None = None,
    issues: list[str] | None = None,
    strengths: list[str] | None = None,
    gaps: list[str] | None = None,
    petitioner_args: list[str] | None = None,
    respondent_args: list[str] | None = None,
    provider: Any = None,
) -> dict[str, Any]:
    """Run the four-agent self-correcting pipeline end to end.

    Args:
        text: Raw document text (noise-filtered first by AGENT 1).
        sections: Section numbers to resolve via context (AGENT 2).
        issues: Pre-extracted issues to criticise (AGENT 4).
        strengths: Pre-extracted strengths to criticise (AGENT 4).
        petitioner_args / respondent_args: Pre-extracted submissions for
            speaker attribution (AGENT 3).
        provider: Optional injected LLM provider (tests).

    Returns:
        Dict with every agent's output. Any agent that fails degrades to the
        caller-supplied value (never fabricated).
    """
    repaired = await clean_ocr_text_with_llm(text, provider)
    cleaned = await clean_text_with_llm(repaired, provider)
    out: dict[str, Any] = {"cleaned_text": cleaned, "raw_text": text}

    out["legal_content_blocks"] = await classify_header_blocks(cleaned, provider)

    out["judgment_date"] = await classify_judgment_date(cleaned, provider)

    if sections:
        out["act_resolutions"] = await resolve_act_from_context(list(sections), cleaned, provider)
        out["act_details"] = await resolve_acts_detailed(list(sections), cleaned, provider)
    else:
        out["act_resolutions"] = {}
        out["act_details"] = {}

    out["counsel_attribution"] = await attribute_counsel_arguments(
        list(petitioner_args or []),
        list(respondent_args or []),
        source_text=cleaned,
        provider=provider,
    )

    out["criticized"] = await critic_extraction(
        {
            "issues": list(issues or []),
            "strengths": list(strengths or []),
            "gaps": list(gaps or []),
        },
        cleaned,
        provider,
    )
    out["criticized"]["strengths_and_gaps"] = await critic_strengths_and_gaps(
        list(strengths or []),
        list(gaps or []),
        cleaned,
        provider,
    )
    return out
