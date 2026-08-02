"""OpenAI-compatible LLM provider.

Interfaces with external API endpoints (such as vLLM, Ollama, LiteLLM) exposing an OpenAI-compatible API.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from loguru import logger

from app.llm.provider import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """LLM provider for OpenAI-compatible APIs (vLLM, Ollama, etc.)."""

    def __init__(
        self,
        model_name: str,
        api_base: str,
        api_key: str = "",
        model_id: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name, **kwargs)
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        """Generate response via chat completion API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stop:
            payload["stop"] = stop

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error(f"OpenAI-compatible generate error: {exc}")
            return f"[LLM Error: {exc}]"

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON response using API's JSON mode."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Append explicit JSON instructions to user prompt
        json_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond ONLY with a valid JSON object matching this schema:\n"
            f"{json.dumps(output_schema, indent=2)}"
        )
        messages.append({"role": "user", "content": json_prompt})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Parse out JSON from response content using regex if it contains markdown code blocks
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    return json.loads(json_match.group(0))
                return json.loads(content)
        except Exception as exc:
            logger.error(f"OpenAI-compatible generate_structured error: {exc}")
            return {"error": str(exc), "parse_error": True}

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        """Stream token generation from the completion API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        try:
            with httpx.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            chunk = data["choices"][0]["delta"].get("content", "")
                            if chunk:
                                yield chunk
                        except Exception:
                            pass
        except Exception as exc:
            logger.error(f"OpenAI-compatible stream error: {exc}")
            yield f"[Stream Error: {exc}]"
