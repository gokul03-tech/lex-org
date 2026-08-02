"""Unit tests for LLM providers.

Tests the mock provider, OpenAI-compatible provider (using mocks), and
Transformers provider (mocking dependency imports).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.llm.mock_provider import MockProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider
from app.llm.provider import get_llm_provider
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
