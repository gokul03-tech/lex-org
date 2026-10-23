"""OpenAI-compatible LLM provider.

Interfaces with external API endpoints (such as vLLM, Ollama, LiteLLM) exposing an OpenAI-compatible API.
"""

from __future__ import annotations

import collections
import json
import random
import re
import threading
import time
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.llm.json_utils import parse_structured_response
from app.llm.provider import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """LLM provider for OpenAI-compatible APIs (vLLM, Ollama, etc.)."""

    _groq_request_lock = threading.Lock()
    _groq_last_request = 0.0
    # Rolling 60-second window of (timestamp, estimated_tokens) for the shared
    # account-wide token budget.
    _groq_token_window: collections.deque[tuple[float, int]] = collections.deque()
    _groq_window_seconds = 60.0
    # Keep the default 8,000 TPM tier below its rolling-minute limit even
    # when several analysis agents share this provider.
    _groq_prompt_limit = 5000
    _groq_system_limit = 1000
    _groq_output_limit = 2600
    _groq_min_interval = settings.GROQ_MIN_INTERVAL
    _groq_tpm = settings.GROQ_TPM
    _groq_reasoning_effort = settings.GROQ_REASONING_EFFORT

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

    @property
    def _is_groq(self) -> bool:
        return "api.groq.com" in self.api_base

    def _groq_payload_extras(self) -> dict[str, Any]:
        """Groq-only request fields (reasoning budget for gpt-oss models)."""
        if self._is_groq and "gpt-oss" in self.model_id:
            return {"reasoning_effort": self._groq_reasoning_effort}
        return {}

    @staticmethod
    def _fit_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        head = limit // 2
        return f"{text[:head]}\n...[context truncated]...\n{text[-(limit - head):]}"

    def _prepare_messages(self, prompt: str, system_prompt: str) -> list[dict[str, str]]:
        if not self._is_groq:
            limit = None
        else:
            # The on-demand Groq tier is limited to 8,000 TPM. Keep each
            # request small enough that the multi-agent pipeline can progress.
            limit = self._groq_prompt_limit
        if limit is not None:
            prompt = self._fit_text(prompt, limit)
            system_prompt = self._fit_text(system_prompt, self._groq_system_limit)
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _estimate_tokens(payload: dict[str, Any]) -> int:
        """Cheap upper-ish bound on a request's token cost for pacing.

        Counts message characters at ~4 chars/token plus the completion budget.
        Over-estimating only makes pacing more conservative, which is what we
        want against a hard TPM ceiling.
        """
        total = int(payload.get("max_tokens") or 0)
        for message in payload.get("messages", []):
            content = message.get("content")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += len(str(part.get("text", ""))) // 4
        return total

    def _pace_groq_request(self, estimated_tokens: int = 0) -> None:
        """Wait until sending would stay inside the rolling TPM budget.

        Groq's free on-demand tier allows only 8,000 tokens/minute shared across
        the whole account, so a fixed inter-request delay either stalls small
        calls or still bursts past the limit on large ones. Instead we track the
        tokens sent in the last 60 seconds and, when the next request would
        exceed the budget, sleep just long enough for the oldest entries to age
        out. A minimum interval still applies as a floor.
        """
        if not self._is_groq:
            return
        with self._groq_request_lock:
            now = time.monotonic()
            window = self._groq_token_window
            while window and now - window[0][0] >= self._groq_window_seconds:
                window.popleft()

            wait = self._groq_min_interval - (now - self._groq_last_request)
            if estimated_tokens and self._groq_tpm > 0:
                used = sum(tokens for _, tokens in window)
                overflow = used + estimated_tokens - self._groq_tpm
                if overflow > 0:
                    freed = 0
                    budget_wait = self._groq_window_seconds
                    for stamp, tokens in window:
                        freed += tokens
                        if freed >= overflow:
                            budget_wait = stamp + self._groq_window_seconds - now
                            break
                    wait = max(wait, budget_wait)

            if wait > 0:
                time.sleep(wait)
            self._groq_last_request = time.monotonic()
            window.append((self._groq_last_request, estimated_tokens))

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        """Return the provider's error body without exposing authorization data."""
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return f"HTTP {response.status_code}: {body}"

    @staticmethod
    def _retry_after(response: httpx.Response) -> float:
        """Extract Groq's suggested cooldown from a rate-limit response."""
        header = response.headers.get("retry-after")
        if header:
            try:
                return max(1.0, min(float(header), 60.0))
            except ValueError:
                pass
        try:
            body = response.json()
            message = str(body.get("error", {}).get("message", ""))
            match = re.search(r"try again in ([0-9.]+)s", message)
            if match:
                return max(1.0, min(float(match.group(1)), 60.0))
        except (ValueError, TypeError, AttributeError):
            pass
        return 15.0

    @staticmethod
    def _is_daily_limit(response: httpx.Response | None) -> bool:
        """True when a 429 is a per-DAY token quota, not a per-minute burst.

        Groq's daily quota ("Rate limit reached ... on tokens per day (TPD)")
        will not refill inside a retry window, so retrying each agent three
        times at 60s a go spends minutes and then fails anyway - the retry storm
        seen in the logs. Detected so the caller can fall back immediately.
        """
        if response is None:
            return False
        try:
            body = response.json()
        except ValueError:
            return False
        if not isinstance(body, dict):
            return False
        message = str(body.get("error", {}).get("message", ""))
        return bool(
            re.search(r'\b(?:tokens?\s+per\s+day|per\s+day\s*\(TPD\)|TPD)\b', message, re.I)
        )

    def _sleep_before_retry(
        self,
        attempt: int,
        response: httpx.Response | None,
        reason: str,
    ) -> None:
        """Sleep with exponential backoff (plus jitter) before the next attempt."""
        delay = min(
            settings.LLM_RETRY_BASE_DELAY + 2**attempt,
            settings.LLM_RETRY_MAX_DELAY,
        )
        if response is not None:
            delay = max(delay, self._retry_after(response))
        delay += random.uniform(0.0, 1.0)
        logger.warning(
            f"LLM request failed ({reason}); retry {attempt + 1}/"
            f"{settings.LLM_MAX_RETRIES} in {delay:.1f}s"
        )
        time.sleep(delay)

    def _post_with_backoff(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        *,
        max_retries: int | None = None,
    ) -> httpx.Response:
        """POST to ``/chat/completions`` with pacing and exponential backoff.

        Transient failures (HTTP 429 and 5xx, plus connection errors) are
        retried; other 4xx responses (auth failures, unknown model ids, bad
        requests) are raised immediately so misconfiguration surfaces fast.
        """
        retries = settings.LLM_MAX_RETRIES if max_retries is None else max_retries
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            self._pace_groq_request(self._estimate_tokens(payload))
            try:
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(
                        f"{self.api_base}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= retries:
                    raise
                self._sleep_before_retry(attempt, None, reason=type(exc).__name__)
                continue

            if response.status_code < 400:
                return response
            # A per-day token quota does not refill within the retry window, so
            # fail fast and let the caller fall back instead of burning minutes.
            if response.status_code == 429 and self._is_daily_limit(response):
                raise RuntimeError(self._error_detail(response))
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= retries:
                    raise RuntimeError(self._error_detail(response))
                self._sleep_before_retry(attempt, response, reason=str(response.status_code))
                continue
            raise RuntimeError(self._error_detail(response))
        raise RuntimeError(f"Max retries exceeded: {last_error}")

    @staticmethod
    def _coerce_to_object(parsed: Any) -> dict[str, Any]:
        """Lift the first object from a parsed JSON array, else return an empty dict."""
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    return item
        return {}

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
            headers["Authorization"] = "Bearer " + self.api_key

        messages = self._prepare_messages(prompt, system_prompt)
        if self._is_groq:
            max_tokens = min(max_tokens, self._groq_output_limit)

        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **self._groq_payload_extras(),
        }
        if stop:
            payload["stop"] = stop

        try:
            response = self._post_with_backoff(payload, headers)
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error(f"OpenAI-compatible generate error: {exc}")
            return "Model response unavailable for this analysis step."

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON response using API's JSON mode."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key

        # Append explicit JSON instructions to user prompt
        schema_text = json.dumps(
            output_schema,
            separators=(",", ":") if self._is_groq else None,
            indent=None if self._is_groq else 2,
        )
        json_prompt = (
            f"{prompt}\n\n"
            "Return ONLY one complete, valid JSON object. Do not use markdown, "
            "reasoning, or explanatory text. Keep string values concise.\n"
            f"JSON schema:\n{schema_text}"
        )
        messages = self._prepare_messages(json_prompt, system_prompt)
        request_max_tokens = max_tokens or 1500
        if self._is_groq:
            request_max_tokens = min(request_max_tokens, self._groq_output_limit)

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": request_max_tokens,
            **self._groq_payload_extras(),
        }
        # Force JSON mode for providers that support it. Groq's gpt-oss models
        # can spend their completion budget on reasoning and trip the server-side
        # JSON validator, so there we rely on the local parser instead.
        if not self._is_groq:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = self._post_with_backoff(payload, headers)
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            if not content:
                # Reasoning models (and prompts whose answer is genuinely
                # "nothing", e.g. "no exhibits found") can return an empty
                # completion. Callers treat that as "nothing extracted", so it
                # is not an error worth a warning.
                logger.debug("Structured LLM response was empty")
                return {}

            parsed = parse_structured_response(content)
            if not isinstance(parsed, dict):
                lifted = self._coerce_to_object(parsed)
                if not lifted:
                    logger.warning(
                        f"Structured LLM response was not a JSON object; "
                        f"raw snippet: {content[:120]!r}"
                    )
                return lifted
            return parsed
        except Exception as exc:
            logger.warning(f"OpenAI-compatible structured response unavailable: {exc}")
            return {"error": str(exc), "parse_error": True}

    def generate_with_images(
        self,
        prompt: str,
        images: list[bytes],
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        image_mime: str = "image/png",
    ) -> str:
        """Multimodal chat completion: prompt + base64 images in one request.

        OpenRouter (and OpenAI-compatible vision endpoints) accept a content
        array of ``text`` and ``image_url`` parts, where the image is a base64
        data URI. Used by the VLM OCR fallback. Raises on failure so the caller
        can keep the PyMuPDF/PaddleOCR text.
        """
        import base64

        headers = {}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images:
            encoded = base64.b64encode(image).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime};base64,{encoded}"},
                }
            )
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = self._post_with_backoff(payload, headers)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

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
            headers["Authorization"] = "Bearer " + self.api_key

        messages = self._prepare_messages(prompt, system_prompt)
        if self._is_groq:
            max_tokens = min(max_tokens, self._groq_output_limit)

        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **self._groq_payload_extras(),
        }

        try:
            self._pace_groq_request(self._estimate_tokens(payload))
            with httpx.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as response:
                if response.status_code >= 400:
                    raise RuntimeError(self._error_detail(response))
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
            yield "Model response unavailable for this analysis step."
