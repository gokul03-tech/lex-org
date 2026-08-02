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
        model_type: Either "qwen" or "deepseek".

    Returns:
        Configured LLMProvider instance.

    Raises:
        ValueError: If model_type is unknown.
        ImportError: If the required backend package is not installed.
    """
    from app.core.config import settings

    if model_type not in ("qwen", "deepseek"):
        raise ValueError(f"Unknown model type: {model_type}. Use 'qwen' or 'deepseek'.")

    if settings.LLM_BACKEND == "mock":
        from app.llm.mock_provider import MockProvider

        return MockProvider(model_name=f"{model_type}-mock")

    if settings.LLM_BACKEND == "llama_cpp":
        from app.llm.llama_cpp_provider import LlamaCppProvider

        model_path = settings.QWEN_MODEL_PATH if model_type == "qwen" else settings.DEEPSEEK_MODEL_PATH
        if not model_path:
            raise ValueError(f"No model path configured for {model_type}. Set QWEN_MODEL_PATH or DEEPSEEK_MODEL_PATH.")
        return LlamaCppProvider(
            model_name=f"{model_type}-gguf",
            model_path=model_path,
            n_ctx=settings.LLM_N_CTX,
            n_threads=settings.LLM_N_THREADS,
            n_gpu_layers=settings.LLM_N_GPU_LAYERS,
        )

    if settings.LLM_BACKEND == "openai_compatible":
        from app.llm.openai_compatible_provider import OpenAICompatibleProvider

        model_id = settings.QWEN_MODEL_NAME if model_type == "qwen" else settings.DEEPSEEK_MODEL_NAME
        return OpenAICompatibleProvider(
            model_name=f"{model_type}-openai-compatible",
            api_base=settings.LLM_API_BASE,
            api_key=settings.LLM_API_KEY,
            model_id=model_id,
        )

    if settings.LLM_BACKEND == "transformers":
        from app.llm.transformers_provider import TransformersProvider

        model_id = settings.QWEN_HF_MODEL_ID if model_type == "qwen" else settings.DEEPSEEK_HF_MODEL_ID
        return TransformersProvider(
            model_name=f"{model_type}-transformers",
            model_id=model_id,
        )

    raise ValueError(f"Unsupported LLM backend: {settings.LLM_BACKEND}")
