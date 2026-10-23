"""Tests for the Agentic Self-Correcting Extraction Pipeline.

Uses an offline FakeProvider so the tests are deterministic and require no GPU
or network. Every agent must return strict JSON semantics and degrade to the
caller-supplied fallback when the LLM misbehaves.
"""

import pytest

from app.agents.agentic_pipeline import (
    _extract_json,
    _looks_like_ocr_noise,
    attribute_counsel_arguments,
    classify_header_blocks,
    classify_judgment_date,
    clean_document_text,
    clean_issues_deterministic,
    clean_ocr_text_with_llm,
    clean_text_with_llm,
    critic_extraction,
    critic_issues,
    critic_strengths,
    critic_strengths_and_gaps,
    recover_from_ocr,
    resolve_act_from_context,
    resolve_act_from_snippet,
    resolve_acts_detailed,
    run_agentic_pipeline,
    validate_understanding_query,
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


class StructuredFakeProvider(FakeProvider):
    """Provider double that verifies the structured JSON path is used."""

    def __init__(self):
        super().__init__()
        self.structured_calls = []

    def generate_structured(self, prompt="", output_schema=None, **kwargs):
        self.structured_calls.append((prompt, output_schema, kwargs))
        return {"cleaned_text": "cleaned legal text"}


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
async def test_clean_document_text_uses_public_agent_one_entry_point():
    provider = StructuredFakeProvider()

    cleaned = await clean_document_text("raw legal text", provider)

    assert cleaned == "cleaned legal text"
    assert provider.structured_calls
    assert provider.structured_calls[0][2]["max_tokens"] >= 1500


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


def test_clean_issues_deterministic_strips_judicial_reasoning():
    issues = [
        "Whether the seizure was lawful? We hold that the search was valid.",
        "Whether bail was denied? In the result the petition is dismissed.",
    ]
    assert clean_issues_deterministic(issues) == [
        "Whether the seizure was lawful?",
        "Whether bail was denied?",
    ]


def test_clean_issues_deterministic_truncates_overlong_issue():
    overlong = "Whether the order is sustainable? " + ("word " * 120)
    assert clean_issues_deterministic([overlong]) == ["Whether the order is sustainable?"]


def test_clean_issues_deterministic_drops_blanks():
    assert clean_issues_deterministic(["  ", "Valid issue?"]) == ["Valid issue?"]


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
async def test_critic_strengths_and_gaps_fallback_on_invalid_json(fake):
    bad = FakeProvider(responder=lambda _p: "not-json")

    corrected = await critic_strengths_and_gaps(
        ["No favorable findings extracted yet."],
        ["No potential gaps extracted yet."],
        "analysis text",
        bad,
    )

    assert corrected["key_strengths"] == ["No favorable findings extracted yet."]
    assert corrected["potential_gaps"] == ["No potential gaps extracted yet."]


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
        gaps=["No potential gaps extracted yet."],
        petitioner_args=["Learned counsel for the petitioner submits X."],
        respondent_args=["The State argues Y."],
        provider=fake,
    )
    assert "IN THE HIGH COURT" in out["cleaned_text"]
    assert out["act_resolutions"] == {"482": "Code of Criminal Procedure, 1973"}
    assert out["act_details"] == {"482": {"act_name": "Code of Criminal Procedure", "year": "1973"}}
    assert out["legal_content_blocks"]
    assert out["judgment_date"] == "18 November 2023"
    assert out["counsel_attribution"]["petitioner_args"]
    assert out["counsel_attribution"]["respondent_args"]
    assert out["criticized"]["issues"] == ["Whether the arrest was lawful?"]
    assert "The Court held that the arrest was unlawful." in out["criticized"]["strengths"]
    assert "strengths_and_gaps" in out["criticized"]


def test_validate_understanding_query_gate():
    assert validate_understanding_query("") is False
    assert validate_understanding_query("Client: .") is False
    assert validate_understanding_query("legal case analysis") is False
    assert validate_understanding_query(
        "Whether the bail petition under Section 439 is maintainable"
    ) is True


@pytest.mark.asyncio
async def test_recover_from_ocr_reads_header_and_footer():
    provider = FakeProvider(
        responder=lambda _p: (
            '{"case_name": "A v. B", "judgment_date": "1 May 2024",'
            ' "final_order": "Bail granted"}'
        )
    )
    out = await recover_from_ocr("garbled body text", provider)
    assert out == {
        "case_name": "A v. B",
        "judgment_date": "1 May 2024",
        "final_order": "Bail granted",
    }


@pytest.mark.asyncio
async def test_recover_from_ocr_handles_bad_json(fake):
    out = await recover_from_ocr("garbled body text", fake)
    assert out == {"case_name": "", "judgment_date": "", "final_order": ""}


# ── OCR repair pre-pass ────────────────────────────────────
def test_looks_like_ocr_noise_flags_fused_text_but_not_prose():
    assert _looks_like_ocr_noise("224of " * 120) is True
    assert _looks_like_ocr_noise("The petition is allowed.") is False


@pytest.mark.asyncio
async def test_clean_ocr_text_skips_clean_document_without_calling_llm():
    provider = FakeProvider(responder=lambda p: "SHOULD NOT BE CALLED")
    out = await clean_ocr_text_with_llm("The petition is allowed.", provider)
    assert out == "The petition is allowed."
    assert provider.calls == []


@pytest.mark.asyncio
async def test_clean_ocr_text_repairs_noisy_document():
    garbled = "224of " * 120
    provider = FakeProvider(
        responder=lambda _p: '{"cleaned_text": "' + ("clean text " * 100) + '"}'
    )
    out = await clean_ocr_text_with_llm(garbled, provider)
    assert out != garbled
    assert "clean text" in out
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_clean_ocr_text_keeps_original_when_output_shrinks():
    garbled = "224of " * 120
    provider = FakeProvider(responder=lambda _p: '{"cleaned_text": "tiny"}')
    out = await clean_ocr_text_with_llm(garbled, provider)
    assert out == garbled


@pytest.mark.asyncio
async def test_clean_ocr_text_repairs_long_document_in_windows():
    garbled = "224of " * 600
    provider = FakeProvider(
        responder=lambda _p: '{"cleaned_text": "' + ("clean text " * 100) + '"}'
    )
    out = await clean_ocr_text_with_llm(garbled, provider, force=True, chunk_size=800)
    assert len(provider.calls) > 1
    assert "224of" not in out


@pytest.mark.asyncio
async def test_clean_ocr_text_caps_repair_to_leading_chars():
    head = "X" * 100
    tail = "TAILMARKER " + ("y " * 50)
    provider = FakeProvider(
        responder=lambda _p: '{"cleaned_text": "CLEANHEAD' + ("z" * 200) + '"}'
    )
    out = await clean_ocr_text_with_llm(head + tail, provider, force=True, max_chars=100)
    assert len(provider.calls) == 1
    assert out.startswith("CLEANHEAD")
    assert "TAILMARKER" in out  # untouched tail is re-appended


# ── Statute resolution (section -> act_name, year) ─────────
@pytest.mark.asyncio
async def test_resolve_act_from_snippet_returns_name_and_year():
    provider = FakeProvider(
        responder=lambda _p: (
            '{"section": "528", "act_name": "Indian Penal Code", "year": "1860"}'
        )
    )
    out = await resolve_act_from_snippet(
        "528", "as defined in the Indian Penal Code 1860", provider
    )
    assert out == {"section": "528", "act_name": "Indian Penal Code", "year": "1860"}


@pytest.mark.asyncio
async def test_resolve_act_from_snippet_empty_on_failure():
    provider = FakeProvider(responder=lambda _p: "junk")
    out = await resolve_act_from_snippet("528", "no act named here", provider)
    assert out == {"section": "528", "act_name": "", "year": ""}


@pytest.mark.asyncio
async def test_resolve_acts_detailed_splits_combined_act_string(fake):
    out = await resolve_acts_detailed(["482"], "Section 482 of the Code cited here.", fake)
    assert out == {"482": {"act_name": "Code of Criminal Procedure", "year": "1973"}}


# ── Header block classifier ────────────────────────────────
@pytest.mark.asyncio
async def test_classify_header_blocks_keeps_only_legal_content():
    text = (
        "Reporter is granted permission to report this judgment.\n\n"
        "The petitioner was arrested on 12 January 2018.\n\n"
        "The argument of the State is that the arrest was lawful."
    )
    provider = FakeProvider(responder=lambda _p: '{"legal_content": [1, 2]}')
    out = await classify_header_blocks(text, provider)
    assert out == [
        "The petitioner was arrested on 12 January 2018.",
        "The argument of the State is that the arrest was lawful.",
    ]


@pytest.mark.asyncio
async def test_classify_header_blocks_falls_back_to_all_on_bad_json():
    text = "Block one.\n\nBlock two."
    out = await classify_header_blocks(text, FakeProvider(responder=lambda _p: "not-json"))
    assert out == ["Block one.", "Block two."]
