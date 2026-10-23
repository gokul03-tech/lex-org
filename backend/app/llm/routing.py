"""Task-level LLM model routing.

High-frequency, low-complexity steps (noise filtering, formatting, intent
detection, query rewriting) run on the fast/cheap model; genuinely complex
reasoning (critic, evidence verification, contradiction detection, debate,
strategy, research) runs on the strong model. This keeps the expensive model's
rate-limit quota free for the steps that actually need it.
"""

from __future__ import annotations

from app.llm.provider import LLMProvider, get_llm_provider


def get_fast_provider() -> LLMProvider:
    """Provider for simple, high-frequency tasks (cheap model)."""
    return get_llm_provider("fast")


def get_strong_provider() -> LLMProvider:
    """Return the provider for complex reasoning tasks (strong model)."""
    return get_llm_provider("strong")


def get_vision_provider() -> LLMProvider:
    """Return the multimodal provider used for the VLM OCR fallback."""
    return get_llm_provider("vision")
