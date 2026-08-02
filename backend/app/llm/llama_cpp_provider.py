

"""Llama.cpp GGUF LLM provider for local quantized model inference.

Requires llama-cpp-python package. Falls back to MockProvider if not installed.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.llm.provider import LLMProvider


class LlamaCppProvider(LLMProvider):
    """LLM provider using llama.cpp Python bindings for GGUF quantized models.

    Supports Qwen3 and DeepSeek-R1 quantized models with grammar-constrained
    structured output generation.
    """

    def __init__(
        self,
        model_name: str = "llama-cpp",
        model_path: str = "",
        n_ctx: int = 8192,
        n_threads: int = 8,
        n_gpu_layers: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name, **kwargs)
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self._model = None

        if model_path:
            self._load_model()

    def _load_model(self) -> None:
        """Lazy-load the GGUF model via llama-cpp-python."""
        try:
            from llama_cpp import Llama

            logger.info(f"Loading GGUF model from {self.model_path}")
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )
            logger.info(f"Model loaded: {self.model_name}")
        except ImportError:
            logger.warning("llama-cpp-python not installed. Using mock fallback.")
            self._model = None
        except Exception as exc:
            logger.error(f"Failed to load model: {exc}")
            self._model = None

    def _ensure_model(self) -> bool:
        """Ensure model is loaded; returns False if unavailable."""
        if self._model is None and self.model_path:
            self._load_model()
        return self._model is not None

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        """Generate text using the loaded GGUF model.

        Falls back to mock responses if the model is unavailable.
        """
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            return MockProvider(self.model_name).generate(
                prompt, system_prompt, max_tokens, temperature, stop
            )

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            result = self._model.create_completion(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or [],
                echo=False,
            )
            return result["choices"][0]["text"].strip()
        except Exception as exc:
            logger.error(f"LLM generation error: {exc}")
            return f"[LLM Error: {exc}]"

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON using grammar-constrained generation.

        Falls back to regular generation + JSON parsing if grammar unavailable.
        """
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            return MockProvider(self.model_name).generate_structured(
                prompt, output_schema, system_prompt, temperature
            )

        json_instruction = (
            f"Respond ONLY with valid JSON conforming to this schema:\n"
            f"{json.dumps(output_schema, indent=2)}\n\n"
            f"{prompt}"
        )

        try:
            # Try grammar-constrained generation
            schema_str = json.dumps(output_schema)
            result = self._model.create_completion(
                prompt=f"{system_prompt}\n\n{json_instruction}",
                max_tokens=4096,
                temperature=temperature,
                grammar=json.dumps(
                    {
                        "type": "object",
                        "properties": {
                            key: value
                            for key, value in self._simplify_schema(output_schema).items()
                        },
                    }
                ),
            )
            return json.loads(result["choices"][0]["text"])
        except Exception:
            # Fallback: regular generation then parse JSON
            response = self.generate(json_instruction, system_prompt, temperature=temperature)
            try:
                # Extract JSON block from response
                import re

                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
            return {"raw_response": response, "parse_error": True}

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        """Stream token-by-token generation."""
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            yield from MockProvider(self.model_name).stream_generate(
                prompt, system_prompt, max_tokens, temperature
            )
            return

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            stream = self._model.create_completion(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                text = chunk["choices"][0].get("text", "")
                if text:
                    yield text
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            yield f"[Stream Error: {exc}]"

    @staticmethod
    def _simplify_schema(schema: dict[str, Any]) -> dict[str, Any]:
        """Simplify JSON schema for llama.cpp grammar compatibility."""
        simplified = {}
        if "properties" in schema:
            for key, value in schema["properties"].items():
                if value.get("type") == "string":
                    simplified[key] = {"type": "string"}
                elif value.get("type") == "number" or value.get("type") == "integer":
                    simplified[key] = {"type": "number"}
                elif value.get("type") == "boolean":
                    simplified[key] = {"type": "boolean"}
                elif value.get("type") == "array":
                    simplified[key] = {"type": "array", "items": {"type": "string"}}
                elif value.get("type") == "object":
                    simplified[key] = {"type": "object"}
                else:
                    simplified[key] = {"type": "string"}
        return simplified
