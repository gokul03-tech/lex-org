"""Regression tests for robust LLM JSON parsing."""

from __future__ import annotations

from app.llm.json_utils import parse_structured_response


def test_parses_plain_and_fenced_objects():
    assert parse_structured_response('{"a": 1}') == {"a": 1}
    assert parse_structured_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_structured_response('prose {"a": 1} trailing') == {"a": 1}


def test_truncated_object_keeps_completed_siblings():
    # The model hit its token limit mid-object. The balanced-scan fallback used
    # to return the inner "issues_identified" array and lose "rules" with it.
    raw = (
        '{"issues_identified": ["A?", "B"], '
        '"rules": [{"section": "482", "provision": "x"}], '
        '"application": "long'
    )
    assert parse_structured_response(raw) == {
        "issues_identified": ["A?", "B"],
        "rules": [{"section": "482", "provision": "x"}],
    }


def test_truncated_nested_object_drops_dangling_element():
    raw = '{"rules": [{"section": "482"}, {"section": "120B'
    assert parse_structured_response(raw) == {"rules": [{"section": "482"}]}


def test_truncated_value_is_dropped_not_guessed():
    assert parse_structured_response('{"a": 1, "b": "hello wor') == {"a": 1}
    assert parse_structured_response('{"a": 1, "confidence": 0.7') == {"a": 1}
    assert parse_structured_response('{"a": 1, "b"') == {"a": 1}


def test_truncated_arrays_are_closed():
    assert parse_structured_response('[{"a": 1}, {"b": ') == [{"a": 1}]
    assert parse_structured_response("[1, 2, 3") == [1, 2]


def test_balanced_text_is_not_repaired():
    # A complete object followed by prose stays governed by the normal
    # fallbacks (first valid object wins), not the truncation repair.
    assert parse_structured_response('{"a": 1} and {"b": 2}') == {"a": 1}


def test_trailing_comma_keeps_outer_object():
    # A trailing comma before a closing brace used to make the balanced scan
    # return an inner array, dropping every sibling field.
    raw = (
        '{"issues_identified": ["A?", "B"], '
        '"rules": [{"section": "482", "provision": "x"}],}'
    )
    assert parse_structured_response(raw) == {
        "issues_identified": ["A?", "B"],
        "rules": [{"section": "482", "provision": "x"}],
    }


def test_trailing_comma_with_surrounding_prose():
    raw = 'prose {"a": [1, 2,], "b": 3,} trailing'
    assert parse_structured_response(raw) == {"a": [1, 2], "b": 3}


def test_literal_control_characters_in_strings_are_tolerated():
    # Long IRAC text is emitted with literal newlines/tabs inside the JSON
    # string. json.loads(strict=True) rejects it and the balanced scan used to
    # return the inner "issues_identified" array, dropping all sibling fields.
    raw = (
        '{"issues_identified": ["A?", "B"], '
        '"application": "The Court held:\\n1. one\\n\\t2. two", '
        '"conclusion": "Bail granted", "confidence": 0.7}'
    ).replace("\\n", "\n").replace("\\t", "\t")
    assert parse_structured_response(raw) == {
        "issues_identified": ["A?", "B"],
        "application": "The Court held:\n1. one\n\t2. two",
        "conclusion": "Bail granted",
        "confidence": 0.7,
    }


def test_truncated_object_with_control_characters():
    raw = '{"issues_identified": ["A", "B"], "application": "line1\nline2\nline3'
    assert parse_structured_response(raw) == {"issues_identified": ["A", "B"]}


def test_empty_input_returns_default_container():
    assert parse_structured_response("") == []
    assert parse_structured_response(None) == []
    assert parse_structured_response("no json here") == []
    assert parse_structured_response("no json here", default="x") == "x"
