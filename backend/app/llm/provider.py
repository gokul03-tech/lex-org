"""Abstract LLM Provider interface for LexOrch-KG.

Defines the contract that all LLM backends (llama.cpp, mock, OpenAI-compatible) must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM backends must implement generate() and generate_structured().
    """

    def __init__(self, model_name: str, **kwargs: Any) -> None:
        """Initialize the LLM provider.

        Args:
            model_name: Human-readable name of the model.
            **kwargs: Backend-specific configuration.
        """
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        """Generate a text response from the LLM.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system-level instruction.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (0.0 = deterministic).
            stop: Optional list of stop sequences.

        Returns:
            The generated text response.
        """
        ...

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate a structured JSON response conforming to output_schema.

        Args:
            prompt: The user prompt.
            output_schema: JSON Schema dict describing expected output.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature.

        Returns:
            Parsed JSON response as a dictionary.
        """
        ...

    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        """Stream text generation token by token.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instruction.
            max_tokens: Maximum tokens.
            temperature: Sampling temperature.

        Yields:
            Generated text chunks.
        """
        ...

    def get_model_info(self) -> dict[str, Any]:
        """Return metadata about the loaded model."""
        return {
            "model_name": self.model_name,
            "backend": type(self).__name__,
        }


def get_llm_provider(model_type: str = "qwen") -> LLMProvider:
    """Factory function to instantiate the appropriate LLM provider.

    Args:
        model_type: One of "qwen" / "deepseek" (concrete roles) or
            "fast" / "strong" (task-based routing roles). "fast" selects the
            cheap model for simple, high-frequency tasks; "strong" selects the
            powerful model for complex reasoning.

    Returns:
        Configured LLMProvider instance.

    Raises:
        ValueError: If model_type is unknown.
        ImportError: If the required backend package is not installed.
    """
    from app.core.config import settings

    valid_roles = ("qwen", "deepseek", "fast", "strong", "vision")
    if model_type not in valid_roles:
        raise ValueError(
            f"Unknown model type: {model_type}. Use one of {', '.join(valid_roles)}."
        )

    # "fast" follows the lightweight "qwen" path and "strong" the reasoning
    # "deepseek" path on the local backends; the openai_compatible backend maps
    # each role to its own model id.
    legacy_type = "qwen" if model_type in ("qwen", "fast", "vision") else "deepseek"

    if settings.LLM_BACKEND == "mock":
        from app.llm.mock_provider import MockProvider

        return MockProvider(model_name=f"{model_type}-mock")

    if settings.LLM_BACKEND == "llama_cpp":
        from app.llm.llama_cpp_provider import LlamaCppProvider

        model_path = (
            settings.QWEN_MODEL_PATH
            if legacy_type == "qwen"
            else (settings.DEEPSEEK_MODEL_PATH or settings.QWEN_MODEL_PATH)
        )
        if not model_path:
            # No GGUF configured for this slot: load local HF weights instead
            # (e.g. an AWQ model stored under MODELS_DIR) via transformers.
            hf_model_id = (
                settings.QWEN_HF_MODEL_ID
                if legacy_type == "qwen"
                else settings.DEEPSEEK_HF_MODEL_ID
            )
            from loguru import logger

            logger.warning(
                f"No GGUF path configured for '{model_type}' under LLM_BACKEND=llama_cpp; "
                f"falling back to TransformersProvider with model_id={hf_model_id}"
            )
            from app.llm.transformers_provider import TransformersProvider

            return TransformersProvider(
                model_name=f"{model_type}-transformers",
                model_id=hf_model_id,
            )
        return LlamaCppProvider(
            model_name=f"{model_type}-gguf",
            model_path=model_path,
            n_ctx=settings.LLM_N_CTX,
            n_threads=settings.LLM_N_THREADS,
            n_gpu_layers=settings.LLM_N_GPU_LAYERS,
        )

    if settings.LLM_BACKEND == "openai_compatible":
        from app.llm.fallback_provider import FallbackProvider
        from app.llm.openai_compatible_provider import OpenAICompatibleProvider

        role_model = {
            "qwen": settings.QWEN_MODEL_NAME,
            "deepseek": settings.DEEPSEEK_MODEL_NAME,
            "fast": settings.FAST_MODEL_NAME,
            "strong": settings.STRONG_MODEL_NAME,
            # Empty VLM_OCR_MODEL inherits the Gemini model (multimodal).
            "vision": settings.VLM_OCR_MODEL or settings.GEMINI_MODEL,
        }[model_type]

        def _build(api_base: str, api_key: str, model_id: str) -> OpenAICompatibleProvider:
            return OpenAICompatibleProvider(
                model_name=f"{model_type}-openai-compatible",
                api_base=api_base,
                api_key=api_key,
                model_id=model_id,
            )

        # Gemini (free tier) is primary when configured; the OpenRouter/LiteLLM
        # endpoint acts as an automatic fallback for 402/429/outage resilience.
        if settings.GEMINI_API_KEY:
            primary = _build(
                settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, settings.GEMINI_MODEL
            )
            if settings.LLM_API_KEY and settings.LLM_API_KEY != settings.GEMINI_API_KEY:
                return FallbackProvider(
                    primary,
                    _build(settings.LLM_API_BASE, settings.LLM_API_KEY, role_model),
                )
            return primary

        return _build(settings.LLM_API_BASE, settings.LLM_API_KEY, role_model)

    if settings.LLM_BACKEND == "transformers":
        from app.llm.transformers_provider import TransformersProvider

        model_id = (
            settings.QWEN_HF_MODEL_ID
            if legacy_type == "qwen"
            else settings.DEEPSEEK_HF_MODEL_ID
        )
        return TransformersProvider(
            model_name=f"{model_type}-transformers",
            model_id=model_id,
        )

    raise ValueError(f"Unsupported LLM backend: {settings.LLM_BACKEND}")
