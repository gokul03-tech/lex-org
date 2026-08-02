"""Transformers-based LLM provider.

Loads model weights locally using Hugging Face's transformers library.
Supports CPU offloading and quantization configuration.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.llm.provider import LLMProvider


class TransformersProvider(LLMProvider):
    """LLM provider using local Hugging Face Transformers pipelines."""

    def __init__(
        self,
        model_name: str,
        model_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name, **kwargs)
        self.model_id = model_id
        self._tokenizer = None
        self._model = None
        self._load_attempted = False

    def _load_model(self) -> None:
        """Lazy-load the tokenizer and model using transformers."""
        self._load_attempted = True
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info(f"Loading HF model: {self.model_id}")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)

            # Load the model with automatic device mapping (CPU offloading if VRAM is insufficient)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype="auto",
                device_map="auto",
            )
            logger.info(f"HF model {self.model_id} loaded successfully on {self._model.device}")
        except ImportError as exc:
            logger.warning(
                f"Required library for Transformers not installed (torch/transformers/accelerate): {exc}. "
                "Falling back to MockProvider."
            )
            self._model = None
        except Exception as exc:
            logger.error(f"Failed to load HF model {self.model_id}: {exc}")
            self._model = None

    def _ensure_model(self) -> bool:
        """Ensure the model is loaded; returns False if unavailable."""
        if not self._load_attempted:
            self._load_model()
        return self._model is not None and self._tokenizer is not None

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        """Generate text using local model inference."""
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            return MockProvider(self.model_name).generate(
                prompt, system_prompt, max_tokens, temperature, stop
            )

        import torch

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

            # Generation parameters
            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "do_sample": temperature > 0.0,
            }
            if temperature > 0.0:
                gen_kwargs["temperature"] = temperature

            # Generate output tokens
            with torch.no_grad():
                outputs = self._model.generate(**inputs, **gen_kwargs)

            # Decode only the newly generated tokens
            input_len = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_len:]
            return self._tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        except Exception as exc:
            logger.error(f"Transformers generate error: {exc}")
            return f"[LLM Error: {exc}]"

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON output using schema prompt and validation parsing."""
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            return MockProvider(self.model_name).generate_structured(
                prompt, output_schema, system_prompt, temperature
            )

        json_instruction = (
            f"{prompt}\n\n"
            f"You MUST respond ONLY with a valid JSON object matching this schema:\n"
            f"{json.dumps(output_schema, indent=2)}"
        )

        response = self.generate(
            prompt=json_instruction,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        try:
            # Extract JSON block using regex if any markdown wrappers are present
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(response)
        except Exception:
            return {"raw_response": response, "parse_error": True}

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        """Stream generated text token by token."""
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            yield from MockProvider(self.model_name).stream_generate(
                prompt, system_prompt, max_tokens, temperature
            )
            return

        from threading import Thread

        import torch
        from transformers import TextIteratorStreamer

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

            streamer = TextIteratorStreamer(self._tokenizer, skip_prompt=True, skip_special_tokens=True)

            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "do_sample": temperature > 0.0,
                "streamer": streamer,
            }
            if temperature > 0.0:
                gen_kwargs["temperature"] = temperature

            # Run generate in background thread so caller can stream from the queue
            thread = Thread(target=self._model.generate, kwargs={**inputs, **gen_kwargs})
            thread.start()

            for new_text in streamer:
                yield new_text
        except Exception as exc:
            logger.error(f"Transformers stream error: {exc}")
            yield f"[Stream Error: {exc}]"
