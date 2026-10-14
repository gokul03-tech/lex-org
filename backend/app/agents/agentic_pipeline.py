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
  * LLM calls are lightweight (default Qwen via get_qwen_provider) and run off
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

from app.llm.qwen import get_qwen_provider

AGENTIC_SYSTEM_PROMPT = (
    "You are a precise legal-document extraction agent for LexOrch-KG. "
    'Reply with STRICT JSON ONLY and nothing else: no prose, no code fences, no comments.'
)


def _get_provider(provider: Any = None) -> Any:
    """Return the injected provider or the lightweight default (Qwen)."""
    return provider if provider is not None else get_qwen_provider()


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
) -> Any:
    """Run a lightweight, deterministic JSON-producing LLM call (off thread).

    Returns the parsed JSON structure, or None if the call/parse fails.
    """
    try:
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
{text[:30000]}"""
    parsed = await _call_json(provider, prompt, max_tokens=1400)
    cleaned = (
        str(parsed.get("cleaned_text", "")).strip() if isinstance(parsed, dict) else ""
    )
    if not cleaned:
        logger.info("Noise filter produced empty output; keeping original text.")
        return text
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
    parsed = await _call_json(provider, prompt, max_tokens=700)
    if not parsed:
        return {}
    result: dict[str, str] = {}
    for item in parsed.get("resolutions", []) if isinstance(parsed, dict) else []:
        sec = str(item.get("section", "")).strip()
        act = str(item.get("act", "") or "").strip()
        if sec and act and act.lower() != "null":
            result[sec] = act
    return result


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
        _DATES_PROMPT.format(tail=text[-8000:]),
        max_tokens=700,
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
    src = (source_text or "")[:16000]
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
    parsed = await _call_json(provider, prompt, max_tokens=700)
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
async def critic_issues(issues: list[str], provider: Any = None) -> list[str]:
    """Issue Critic: truncate every issue to ONLY the legal question (an issue
    should rarely exceed 2 sentences). Reasoning/analysis is removed."""
    if not issues:
        return issues
    provider = _get_provider(provider)
    prompt = f"""Review these extracted Legal Issues.

For each issue: if it contains the court's reasoning or analysis, TRUNCATE it
to ONLY the legal question. An issue should rarely exceed 2 sentences.

Return STRICT JSON: {{"issues": ["..."]}}

ISSUES:
{chr(10).join(f"- {i}" for i in issues)}"""
    parsed = await _call_json(provider, prompt, max_tokens=800)
    if isinstance(parsed, dict):
        cleaned = [str(i).strip() for i in parsed.get("issues", []) if str(i).strip()]
        if len(cleaned) == len(issues):
            return cleaned
    return list(issues)


async def critic_strengths(
    strengths: list[str], text: str, provider: Any = None
) -> list[str]:
    """Strengths Critic: if a strength is a generic fallback ("No favorable
    findings extracted"), re-read the ANALYSIS AND REASONING section of the
    source and extract the court's actual favorable findings."""
    provider = _get_provider(provider)
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
{text[:18000]}"""
    parsed = await _call_json(provider, prompt, max_tokens=700)
    if isinstance(parsed, dict):
        recovered = [str(s).strip() for s in parsed.get("strengths", []) if str(s).strip()]
        if recovered:
            return recovered
    return [s for s in strengths if s.strip()]


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
    cleaned = await clean_text_with_llm(text, provider)
    out: dict[str, Any] = {"cleaned_text": cleaned, "raw_text": text}

    out["judgment_date"] = await classify_judgment_date(cleaned, provider)

    if sections:
        out["act_resolutions"] = await resolve_act_from_context(list(sections), cleaned, provider)
    else:
        out["act_resolutions"] = {}

    out["counsel_attribution"] = await attribute_counsel_arguments(
        list(petitioner_args or []),
        list(respondent_args or []),
        source_text=cleaned,
        provider=provider,
    )

    out["criticized"] = await critic_extraction(
        {"issues": list(issues or []), "strengths": list(strengths or [])},
        cleaned,
        provider,
    )
    return out
