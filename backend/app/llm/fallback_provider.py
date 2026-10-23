"""Provider that transparently fails over to a second LLM backend.

The primary provider is tried first; if it raises (or returns the
provider-level "unavailable" sentinel/error dict) the fallback is attempted.
This lets the app run on a free-tier Gemini key while keeping OpenRouter as a
backup (and vice versa), so a 402/429/outage on one provider does not stall the
whole multi-agent pipeline.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from loguru import logger

from app.llm.provider import LLMProvider

# Sentinels the OpenAI-compatible provider returns instead of raising.
_UNAVAILABLE_PREFIX = "Model response unavailable"


class FallbackProvider(LLMProvider):
    """Wrap a primary provider with a fallback used only when primary fails."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        super().__init__(
            model_name=f"{primary.model_name}->{fallback.model_name}",
        )
        self.primary = primary
        self.fallback = fallback

    @property
    def model_id(self) -> str:
        return getattr(self.primary, "model_id", self.primary.model_name)

    @property
    def api_base(self) -> str:
        return getattr(self.primary, "api_base", "")

    @property
    def api_key(self) -> str:
        return getattr(self.primary, "api_key", "")

    @staticmethod
    def _structured_failed(result: Any) -> bool:
        if not isinstance(result, dict) or not result:
            return True
        return bool(result.get("parse_error")) or "error" in result

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        def call(provider: LLMProvider) -> str:
            return provider.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )

        try:
            text = call(self.primary)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Primary LLM generate failed ({exc}); using fallback.")
            return call(self.fallback)
        if not text or text.startswith(_UNAVAILABLE_PREFIX):
            logger.warning("Primary LLM generate returned no text; using fallback.")
            return call(self.fallback)
        return text

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        def call(provider: LLMProvider) -> dict[str, Any]:
            return provider.generate_structured(
                prompt,
                output_schema,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        try:
            result = call(self.primary)
        except Exception as exc:  # noqa: BLE001 - fall over to backup provider
            logger.warning(f"Primary LLM structured call failed ({exc}); using fallback.")
            return call(self.fallback)
        if self._structured_failed(result):
            logger.warning("Primary LLM returned no usable structured result; using fallback.")
            return call(self.fallback)
        return result

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> Iterator[str]:
        yielded = False
        try:
            for chunk in self.primary.stream_generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                yielded = True
                yield chunk
        except Exception as exc:  # noqa: BLE001
            if yielded:
                raise
            logger.warning(f"Primary LLM stream failed ({exc}); using fallback.")
            yield from self.fallback.stream_generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    def generate_with_images(
        self,
        prompt: str,
        images: list[bytes],
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        image_mime: str = "image/png",
    ) -> str:
        if not hasattr(self.primary, "generate_with_images"):
            return self.fallback.generate_with_images(  # type: ignore[attr-defined]
                prompt,
                images,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                image_mime=image_mime,
            )
        try:
            return self.primary.generate_with_images(  # type: ignore[attr-defined]
                prompt,
                images,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                image_mime=image_mime,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Primary LLM vision OCR failed ({exc}); using fallback.")
            return self.fallback.generate_with_images(  # type: ignore[attr-defined]
                prompt,
                images,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                image_mime=image_mime,
            )

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "backend": type(self).__name__,
            "primary": self.primary.get_model_info(),
            "fallback": self.fallback.get_model_info(),
        }
