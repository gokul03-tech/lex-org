"""Unit tests for LLM providers.

Tests the mock provider, OpenAI-compatible provider (using mocks), and
Transformers provider (mocking dependency imports).
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from app.llm.json_utils import parse_structured_response
from app.llm.mock_provider import MockProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider
from app.llm.provider import get_llm_provider
from app.llm.routing import get_fast_provider, get_strong_provider
from app.llm.transformers_provider import TransformersProvider


def test_mock_provider_generate() -> None:
    """Test that MockProvider generates legal-sounding mock responses."""
    provider = MockProvider(model_name="qwen-mock")
    response = provider.generate("Explain Section 420 of BNS.")
    assert "Section 420" in response
    assert "Bharatiya Nyaya Sanhita 2023" in response

    summary_response = provider.generate("Summarize the case facts.")
    assert "CASE SUMMARY:" in summary_response


def test_mock_provider_generate_structured() -> None:
    """Test MockProvider generate_structured returns standard mock dict."""
    provider = MockProvider(model_name="qwen-mock")
    schema = {
        "type": "object",
        "properties": {
            "analysis": {"type": "string"},
            "confidence": {"type": "number"},
        },
    }
    result = provider.generate_structured("Explain it", schema)
    assert isinstance(result, dict)
    assert "confidence" in result
    assert result["confidence"] == 0.85


def test_openai_compatible_provider_generate() -> None:
    """Test OpenAICompatibleProvider generate method with a mocked HTTP response."""
    provider = OpenAICompatibleProvider(
        model_name="qwen-api",
        api_base="http://localhost:8000/v1",
        api_key="test-key",
        model_id="Qwen/Qwen3-8B-AWQ",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a mock OpenAI-compatible response.",
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        response = provider.generate("Test prompt", system_prompt="Test system")
        assert response == "This is a mock OpenAI-compatible response."
        mock_post.assert_called_once()
        # Verify payload structure
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "Qwen/Qwen3-8B-AWQ"
        assert len(call_kwargs["json"]["messages"]) == 2
        assert call_kwargs["json"]["messages"][0]["role"] == "system"
        assert call_kwargs["json"]["messages"][1]["role"] == "user"


def test_openai_compatible_provider_generate_structured() -> None:
    """Test OpenAICompatibleProvider generate_structured parses JSON correctly."""
    provider = OpenAICompatibleProvider(
        model_name="qwen-api",
        api_base="http://localhost:8000/v1",
        api_key="",
        model_id="Qwen/Qwen3-8B-AWQ",
    )

    schema = {"type": "object", "properties": {"valid": {"type": "boolean"}}}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '```json\n{"valid": true}\n```',
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = provider.generate_structured("Prompt", schema)
        assert isinstance(result, dict)
        assert result.get("valid") is True


def test_openai_compatible_provider_sends_bearer_and_output_limit() -> None:
    provider = OpenAICompatibleProvider(
        model_name="groq",
        api_base="https://api.groq.com/openai/v1",
        api_key="test-key",
        model_id="llama-3.1-70b-versatile",
    )
    response = MagicMock()
    response.status_code = 200
    response.is_error = False
    response.json.return_value = {
        "choices": [{"message": {"content": '{"ok": true}'}}]
    }

    with patch("httpx.Client.post", return_value=response) as mock_post:
        result = provider.generate_structured(
            "Prompt",
            {"type": "object", "properties": {"ok": {"type": "boolean"}}},
            max_tokens=1500,
        )

    assert result == {"ok": True}
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert mock_post.call_args.kwargs["json"]["max_tokens"] == 1500


def test_openai_compatible_provider_stream() -> None:
    """Test OpenAICompatibleProvider stream_generate method yielding text chunks."""
    provider = OpenAICompatibleProvider(
        model_name="qwen-api",
        api_base="http://localhost:8000/v1",
        api_key="",
        model_id="Qwen/Qwen3-8B-AWQ",
    )

    mock_stream_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Simulate API response lines
    mock_response.iter_lines.return_value = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        "data: [DONE]",
    ]
    mock_stream_ctx.__enter__.return_value = mock_response

    with patch("httpx.stream", return_value=mock_stream_ctx):
        chunks = list(provider.stream_generate("Prompt"))
        assert "".join(chunks) == "Hello world"


def test_transformers_provider_missing_dependencies_fallback() -> None:
    """Test that TransformersProvider falls back to MockProvider when HF libs are missing."""
    provider = TransformersProvider(
        model_name="qwen-transformers",
        model_id="Qwen/Qwen3-8B-AWQ",
    )

    import sys
    # Force ImportError on import of torch/transformers using sys.modules patching
    with patch.dict(sys.modules, {"torch": None, "transformers": None}):
        response = provider.generate("Explain Section 420.")
        # Output should be generated by MockProvider fallback
        assert "Section 420" in response
        assert "Bharatiya Nyaya Sanhita 2023" in response


def test_get_llm_provider_factory() -> None:
    """Test that get_llm_provider correctly resolves provider instantiation based on config."""
    with patch("app.core.config.settings.LLM_BACKEND", "mock"):
        provider = get_llm_provider("qwen")
        assert isinstance(provider, MockProvider)
        assert provider.model_name == "qwen-mock"

    with patch("app.core.config.settings.LLM_BACKEND", "openai_compatible"):
        with patch("app.core.config.settings.LLM_API_BASE", "http://localhost:9999/v1"):
            with patch("app.core.config.settings.QWEN_MODEL_NAME", "some-model"):
                provider = get_llm_provider("qwen")
                assert isinstance(provider, OpenAICompatibleProvider)
                assert provider.api_base == "http://localhost:9999/v1"
                assert provider.model_id == "some-model"

    with patch("app.core.config.settings.LLM_BACKEND", "transformers"):
        with patch("app.core.config.settings.QWEN_HF_MODEL_ID", "hf-qwen-model"):
            provider = get_llm_provider("qwen")
            assert isinstance(provider, TransformersProvider)
            assert provider.model_id == "hf-qwen-model"


def test_parse_structured_response_variants() -> None:
    """The robust parser handles fences, prose, nesting and junk."""
    assert parse_structured_response('{"a": 1}') == {"a": 1}
    assert parse_structured_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_structured_response('Sure: {"a": [1, 2]} done') == {"a": [1, 2]}
    assert parse_structured_response("prefix [1, 2, 3] suffix") == [1, 2, 3]
    assert parse_structured_response("no json here") == []
    assert parse_structured_response("{not valid json}") == {}
    assert parse_structured_response(None) == []
    assert parse_structured_response("garbage", default={"x": 1}) == {"x": 1}


def test_provider_routes_fast_and_strong_models() -> None:
    """Fast/strong roles select FAST_MODEL_NAME / STRONG_MODEL_NAME."""
    with (
        patch("app.core.config.settings.LLM_BACKEND", "openai_compatible"),
        patch("app.core.config.settings.LLM_API_BASE", "http://localhost:9999/v1"),
        patch("app.core.config.settings.FAST_MODEL_NAME", "fast-model"),
        patch("app.core.config.settings.STRONG_MODEL_NAME", "strong-model"),
    ):
        fast = get_fast_provider()
        strong = get_strong_provider()
        fast_direct = get_llm_provider("fast")
        strong_direct = get_llm_provider("strong")

    assert isinstance(fast, OpenAICompatibleProvider)
    assert isinstance(strong, OpenAICompatibleProvider)
    assert fast.model_id == "fast-model"
    assert strong.model_id == "strong-model"
    assert fast_direct.model_id == "fast-model"
    assert strong_direct.model_id == "strong-model"


def _http_response(status_code: int, payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.json.return_value = payload
    return response


def test_generate_structured_retries_on_rate_limit() -> None:
    """A 429 is retried with backoff; the following 200 succeeds."""
    provider = OpenAICompatibleProvider(
        model_name="openrouter",
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model_id="meta-llama/llama-3.3-70b-instruct",
    )
    throttled = _http_response(429, {"error": {"message": "rate limited"}})
    ok = _http_response(200, {"choices": [{"message": {"content": '{"valid": true}'}}]})

    with (
        patch("httpx.Client.post", side_effect=[throttled, ok]) as mock_post,
        patch("time.sleep") as mock_sleep,
    ):
        result = provider.generate_structured("Prompt", {"type": "object"})

    assert result == {"valid": True}
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


def test_generate_structured_does_not_retry_client_errors() -> None:
    """Non-retryable 4xx (e.g. 404 unknown model) fails fast, no retries."""
    provider = OpenAICompatibleProvider(
        model_name="openrouter",
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model_id="meta-llama/does-not-exist",
    )
    not_found = _http_response(404, {"error": {"message": "model not found"}})

    with (
        patch("httpx.Client.post", return_value=not_found) as mock_post,
        patch("time.sleep") as mock_sleep,
    ):
        result = provider.generate_structured("Prompt", {"type": "object"})

    assert result.get("parse_error") is True
    assert mock_post.call_count == 1
    mock_sleep.assert_not_called()


def test_model_name_env_aliases(monkeypatch) -> None:
    """GROQ_MODEL_* env names win; FAST/STRONG_MODEL_NAME is the fallback."""
    from app.core.config import Settings

    monkeypatch.delenv("GROQ_MODEL_FAST", raising=False)
    monkeypatch.delenv("GROQ_MODEL_REASONING", raising=False)
    monkeypatch.setenv("GROQ_MODEL_FAST", "alias-fast")
    monkeypatch.setenv("GROQ_MODEL_REASONING", "alias-strong")
    monkeypatch.setenv("FAST_MODEL_NAME", "fallback-fast")
    monkeypatch.setenv("STRONG_MODEL_NAME", "fallback-strong")
    settings = Settings(_env_file=None)
    assert settings.FAST_MODEL_NAME == "alias-fast"
    assert settings.STRONG_MODEL_NAME == "alias-strong"

    monkeypatch.delenv("GROQ_MODEL_FAST")
    monkeypatch.delenv("GROQ_MODEL_REASONING")
    fallback = Settings(_env_file=None)
    assert fallback.FAST_MODEL_NAME == "fallback-fast"
    assert fallback.STRONG_MODEL_NAME == "fallback-strong"


def _groq_provider(model_id: str = "openai/gpt-oss-20b") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        model_name="groq",
        api_base="https://api.groq.com/openai/v1",
        api_key="k",
        model_id=model_id,
    )


def test_estimate_tokens_counts_prompt_and_completion() -> None:
    payload = {
        "messages": [
            {"role": "system", "content": "x" * 400},
            {"role": "user", "content": "y" * 800},
        ],
        "max_tokens": 200,
    }
    # 1200 chars / 4 = 300 prompt tokens + 200 completion budget.
    assert OpenAICompatibleProvider._estimate_tokens(payload) == 500


def test_groq_payload_extras_only_for_gpt_oss_on_groq(monkeypatch) -> None:
    monkeypatch.setattr(OpenAICompatibleProvider, "_groq_reasoning_effort", "low")
    assert _groq_provider()._groq_payload_extras() == {"reasoning_effort": "low"}
    # Non-gpt-oss Groq model: no reasoning_effort field.
    assert _groq_provider("allam-2-7b")._groq_payload_extras() == {}
    # Non-Groq endpoint: never adds Groq-only fields.
    other = OpenAICompatibleProvider(
        model_name="openrouter",
        api_base="https://openrouter.ai/api/v1",
        api_key="k",
        model_id="openai/gpt-oss-20b",
    )
    assert other._groq_payload_extras() == {}


def test_pace_groq_request_within_budget_does_not_sleep(monkeypatch) -> None:
    provider = _groq_provider()
    monkeypatch.setattr(OpenAICompatibleProvider, "_groq_min_interval", 0.0)
    monkeypatch.setattr(OpenAICompatibleProvider, "_groq_last_request", 0.0)
    OpenAICompatibleProvider._groq_token_window.clear()
    with patch("time.sleep") as sleep_mock:
        provider._pace_groq_request(1000)
    assert not sleep_mock.called
    assert sum(t for _, t in OpenAICompatibleProvider._groq_token_window) == 1000


def test_pace_groq_request_waits_when_budget_exceeded(monkeypatch) -> None:
    monkeypatch.setattr(OpenAICompatibleProvider, "_groq_min_interval", 0.0)
    provider = _groq_provider()
    provider._groq_token_window.clear()
    # Pretend 7,500 tokens were already sent just now; an 8k budget leaves 500.
    OpenAICompatibleProvider._groq_token_window.append((time.monotonic(), 7900))
    with patch("time.sleep") as sleep_mock:
        provider._pace_groq_request(1000)
    assert sleep_mock.called
    assert sleep_mock.call_args[0][0] > 0


def test_pace_skips_non_groq_endpoint() -> None:
    provider = OpenAICompatibleProvider(
        model_name="openrouter",
        api_base="https://openrouter.ai/api/v1",
        api_key="k",
        model_id="meta-llama/llama-3.3-70b-instruct",
    )
    before = list(OpenAICompatibleProvider._groq_token_window)
    with patch("time.sleep") as sleep_mock:
        provider._pace_groq_request(999999)
    assert not sleep_mock.called
    assert list(OpenAICompatibleProvider._groq_token_window) == before



def test_daily_token_limit_is_detected_from_429_body() -> None:
    """Groq's per-day token quota must be recognised so the provider fails fast
    instead of retrying three times at 60s each (the retry storm)."""
    import httpx

    daily = httpx.Response(
        429,
        json={"error": {"message": "Rate limit reached ... on tokens per day (TPD): "
                                   "Limit 200000, Used 199443. Please try again in 6m47s."}},
    )
    burst = httpx.Response(
        429,
        json={"error": {"message": "Rate limit reached ... on tokens per minute (TPM). "
                                   "Please try again in 6s."}},
    )
    assert OpenAICompatibleProvider._is_daily_limit(daily) is True
    assert OpenAICompatibleProvider._is_daily_limit(burst) is False
    assert OpenAICompatibleProvider._is_daily_limit(None) is False
