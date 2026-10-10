"""Tests for the Agentic Self-Correcting Extraction Pipeline.

Uses an offline FakeProvider so the tests are deterministic and require no GPU
or network. Every agent must return strict JSON semantics and degrade to the
caller-supplied fallback when the LLM misbehaves.
"""

import pytest

from app.agents.agentic_pipeline import (
    _extract_json,
    attribute_counsel_arguments,
    classify_judgment_date,
    clean_text_with_llm,
    critic_extraction,
    critic_issues,
    critic_strengths,
    resolve_act_from_context,
    run_agentic_pipeline,
)


class FakeProvider:
    """Scripted LLM provider: returns a JSON string chosen by prompt keyword.

    A callable responder may be passed to force failures (raise / bad JSON).
    """

    def __init__(self, responder=None):
        self.responder = responder
        self.calls = []

    def generate(self, prompt="", **_kwargs):
        self.calls.append(prompt)
        resp = self.responder(prompt) if self.responder else self._default(prompt)
        if isinstance(resp, Exception):
            raise resp
        return resp

    def _default(self, prompt: str) -> str:
        low = prompt.lower()
        if "cleaned_text" in low:
            return (
                '{"cleaned_text": "IN THE HIGH COURT ... Section 482 of the Code'
                ' ... The said bail petition is allowed."}'
            )
        if "resolutions" in low:
            return (
                '{"resolutions": ['
                '{"section": "482", "act": "Code of Criminal Procedure, 1973",'
                ' "in_context": true}]}'
            )
        if '"dates"' in low:
            return (
                '{"dates": ['
                '{"date": "12 January 2018", "sentence": "Incorporation.", "role": "EVENT"}, '
                '{"date": "18 November 2023", "sentence": "Judgment signed.", "role": "JUDGMENT"}]}'
            )
        if "petitioner_args" in low and "respondent_args" in low:
            return '{"petitioner_args": ["[0]"], "respondent_args": ["[1001]"]}'
        if "issue" in low and "truncate" in low:
            return '{"issues": ["Whether the arrest was lawful?"]}'
        if "analysis and reasoning" in low:
            return '{"strengths": ["The Court held that the arrest was unlawful."]}'
        return '{}'


@pytest.fixture
def fake():
    return FakeProvider()


def test_extract_json_handles_fences_and_prose():
    assert _extract_json('Here: ```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('{"a": [1, 2]}') == {"a": [1, 2]}
    assert _extract_json("no json here") is None
    assert _extract_json("") is None
    assert _extract_json('prefix [1, 2, 3] suffix') == [1, 2, 3]


@pytest.mark.asyncio
async def test_clean_text_with_llm_returns_cleaned_text(fake):
    cleaned = await clean_text_with_llm("Page 1 of 3 ACADEMIC CASE STUDY ... bail allowed.", fake)
    assert "IN THE HIGH COURT" in cleaned
    assert "bail petition is allowed" in cleaned


@pytest.mark.asyncio
async def test_clean_returns_raw_on_llm_failure():
    failing = FakeProvider(responder=lambda _p: RuntimeError("model down"))
    raw = "core legal text that must survive"
    assert await clean_text_with_llm(raw, failing) == raw


@pytest.mark.asyncio
async def test_clean_returns_raw_on_bad_json():
    bad = FakeProvider(responder=lambda _p: "not json at all")
    raw = "plain text"
    assert await clean_text_with_llm(raw, bad) == raw


@pytest.mark.asyncio
async def test_resolve_act_from_context(fake):
    mapping = await resolve_act_from_context(["482"], "Section 482 of the Code cited below.", fake)
    assert mapping == {"482": "Code of Criminal Procedure, 1973"}


@pytest.mark.asyncio
async def test_resolve_act_empty_on_sections_not_in_text(fake):
    assert await resolve_act_from_context([], "no sections", fake) == {}


@pytest.mark.asyncio
async def test_classify_judgment_date_prefers_judgment_role(fake):
    date = await classify_judgment_date(
        "Incorporated 12 January 2018. Signed 18 November 2023.", fake
    )
    assert date == "18 November 2023"


@pytest.mark.asyncio
async def test_classify_judgment_date_none_without_judgment_role():
    no_judgment = FakeProvider(
        responder=lambda _p: '{"dates": [{"date": "12 Jan 2018", "role": "EVENT"}]}'
    )
    assert await classify_judgment_date("some text", no_judgment) is None


@pytest.mark.asyncio
async def test_attribute_counsel_arguments_never_swaps(fake):
    pet = ["Learned counsel for the petitioner submits the arrest is unlawful."]
    resp = ["The State argues the arrest was lawful."]
    out = await attribute_counsel_arguments(pet, resp, source_text="case", provider=fake)
    assert out["petitioner_args"] == pet
    assert out["respondent_args"] == resp


@pytest.mark.asyncio
async def test_attribute_falls_back_on_partial_split():
    partial = FakeProvider(
        responder=lambda _p: '{"petitioner_args": ["[0]"], "respondent_args": []}'
    )
    pet = ["pet arg"]
    resp = ["resp arg"]
    out = await attribute_counsel_arguments(pet, resp, provider=partial)
    # Do not trust a split that dropped an argument - keep the raw extraction.
    assert out["petitioner_args"] == pet
    assert out["respondent_args"] == resp


@pytest.mark.asyncio
async def test_critic_issues_truncate_to_question(fake):
    long_issue = [
        "Whether the arrest was lawful? The Court below then analysed the "
        "custodial timeline at length before concluding that the arrest had "
        "been made without authority, which analysis does not belong here."
    ]
    corrected = await critic_issues(long_issue, fake)
    assert corrected == ["Whether the arrest was lawful?"]


@pytest.mark.asyncio
async def test_critic_strengths_recovers_real_findings(fake):
    generic = ["No favorable findings extracted yet."]
    recovered = await critic_strengths(generic, "the ANALYSIS AND REASONING section", fake)
    assert "The Court held that the arrest was unlawful." in recovered


@pytest.mark.asyncio
async def test_critic_strengths_keeps_grounded_list(fake):
    strong = ["The Court held the arrest unlawful - verbatim from source."]
    assert await critic_strengths(strong, "text", fake) == strong


@pytest.mark.asyncio
async def test_critic_extraction_returns_original_on_failure():
    failing = FakeProvider(responder=lambda _p: RuntimeError("critic down"))
    result = {"issues": ["original issue?"], "strengths": ["original strength"]}
    corrected = await critic_extraction(result, "text", failing)
    assert corrected == result


@pytest.mark.asyncio
async def test_run_agentic_pipeline_orchestrates(fake):
    out = await run_agentic_pipeline(
        "Page 1 of 2 ACADEMIC CASE STUDY. Section 482 of the Code. Signed 18 November 2023.",
        sections=["482"],
        issues=["Whether the arrest was lawful? plus reasoning that bleeds"],
        strengths=["No favorable findings extracted yet."],
        petitioner_args=["Learned counsel for the petitioner submits X."],
        respondent_args=["The State argues Y."],
        provider=fake,
    )
    assert "IN THE HIGH COURT" in out["cleaned_text"]
    assert out["act_resolutions"] == {"482": "Code of Criminal Procedure, 1973"}
    assert out["judgment_date"] == "18 November 2023"
    assert out["counsel_attribution"]["petitioner_args"]
    assert out["counsel_attribution"]["respondent_args"]
    assert out["criticized"]["issues"] == ["Whether the arrest was lawful?"]
    assert "The Court held that the arrest was unlawful." in out["criticized"]["strengths"]
