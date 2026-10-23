"""Robust parsing of (possibly noisy) JSON returned by LLMs.

LLMs frequently wrap JSON in markdown code fences or surround it with prose.
This module extracts the first valid JSON value without crashing, so a
malformed model reply degrades to a safe empty container instead of raising.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$", re.MULTILINE)


def parse_structured_response(raw_text: str | None, default: Any = None) -> Any:
    """Parse the first JSON object/array embedded in ``raw_text``.

    Fallbacks, in order:
      1. ``json.loads`` of the raw text
      2. strip surrounding markdown code fences, then ``json.loads``
      3. drop trailing commas before a close brace/bracket, then ``json.loads``
      4. repair a truncated object/array cut off mid-stream
      5. regex-extract the first ``{...}`` / ``[...]`` block, then ``json.loads``
      6. balanced-brace scan with a real decoder (handles nested braces/prose)

    Returns ``default`` when nothing parses. When ``default`` is omitted the
    result is ``{}`` for object-like text and ``[]`` otherwise (never raises).
    """
    text = "" if raw_text is None else raw_text.strip()
    if not text:
        return _resolve_default(text, default)

    # 1. Direct parse.
    try:
        return json.loads(text, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Strip markdown code fences.
    clean = _FENCE_RE.sub("", text).strip()
    if clean != text:
        try:
            return json.loads(clean, strict=False)
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Drop trailing commas before a close brace/bracket. LLMs emit these
    #    often; json.loads rejects them and the balanced scan at the end would
    #    then lift an inner array (e.g. a still-complete "issues_identified"),
    #    discarding every sibling field. Normalising here keeps the object.
    decomma = _strip_trailing_commas(clean)
    if decomma != clean:
        try:
            return json.loads(decomma, strict=False)
        except (json.JSONDecodeError, ValueError):
            pass
        clean = decomma

    # 4. Repair a truncated object/array. Must run before the balanced scan:
    #    when the model hits its token limit mid-object, the scan returns the
    #    first *inner* value it can parse (e.g. the still-complete
    #    "issues_identified" array) and every sibling field is lost.
    if clean[:1] in "{[":
        repaired = _repair_truncated_json(clean)
        if repaired is not None:
            return repaired

    # 5. Regex-extract the first object/array.
    match = re.search(r"\{.*\}|\[.*\]", clean, re.DOTALL)
    if match:
        for candidate in (match.group(0), _strip_trailing_commas(match.group(0))):
            try:
                return json.loads(candidate, strict=False)
            except (json.JSONDecodeError, ValueError):
                pass

    # 6. Balanced scan: earliest '{'/'[' that a real decoder accepts. When the
    #    text is clearly an object, only try '{' so a malformed outer object
    #    cannot silently degrade into one of its inner arrays (which would drop
    #    every sibling field and read as "model returned the wrong shape").
    opener = "{" if clean[:1] == "{" else None
    decoder = json.JSONDecoder()
    for i, ch in enumerate(clean):
        if ch not in "{[":
            continue
        if opener is not None and ch != opener:
            continue
        try:
            obj, _ = decoder.raw_decode(clean[i:])
        except json.JSONDecodeError:
            continue
        return obj

    return _resolve_default(text, default)



def _strip_trailing_commas(text: str) -> str:
    """Remove commas that sit directly before a closing ``}`` or ``]``.

    String-aware, so a comma inside a JSON string value is left untouched.
    """
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _repair_truncated_json(text: str) -> Any:
    """Best-effort parse of a JSON value cut off mid-stream.

    Walks the text tracking string/bracket state. A trailing incomplete token is
    dropped (cut back to the last structurally-safe position) and any still-open
    brackets are closed, so a completion cut off by a token limit still yields
    the fields that were fully emitted. Returns ``None`` when nothing is
    salvageable or the text was already balanced (the caller handles that).
    """
    stack: list[str] = []
    kinds: list[str] = []
    in_string = False
    escape = False
    expect_value = False
    last_safe = 0
    safe_close = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
                if expect_value:
                    last_safe = i + 1
                    safe_close = "".join(reversed(stack))
            i += 1
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
            kinds.append("o" if ch == "{" else "a")
            expect_value = ch == "["
        elif ch in "}]":
            if stack:
                stack.pop()
                kinds.pop()
            expect_value = False
            last_safe = i + 1
            safe_close = "".join(reversed(stack))
        elif ch == ",":
            expect_value = bool(kinds) and kinds[-1] == "a"
            last_safe = i
            safe_close = "".join(reversed(stack))
        elif ch == ":":
            expect_value = True
        i += 1

    if not stack and not in_string:
        # Balanced: not a truncation; let the normal fallbacks handle noise.
        return None

    candidate = re.sub(r"[,\s]+$", "", text[:last_safe]) + safe_close
    try:
        return json.loads(candidate, strict=False)
    except (json.JSONDecodeError, ValueError):
        return None


def _resolve_default(text: str, default: Any) -> Any:
    if default is not None:
        return default
    return {} if text.strip().startswith("{") else []
