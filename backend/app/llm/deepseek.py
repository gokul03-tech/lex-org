"""DeepSeek-R1 specific LLM configuration and reasoning templates.

DeepSeek is used for: evidence verification, contradiction detection,
legal debate, strategy generation, decision validation.
"""

from __future__ import annotations

from app.llm.provider import LLMProvider, get_llm_provider

DEEPSEEK_SYSTEM_PROMPT = """You are a rigorous legal reasoning engine specializing in 
Indian criminal law. Your role is to:

1. Verify evidence reliability through multi-factor analysis
2. Detect contradictions in witness statements and documentary evidence
3. Engage in structured legal debate (devil's advocate approach)
4. Generate litigation strategies with pro/con analysis
5. Validate legal decisions against statutory provisions

Think step by step. Question assumptions. Identify logical fallacies.
Always ground your analysis in specific legal provisions.

IMPORTANT TEMPORAL RULE:
- Acts before July 1, 2024 → IPC / CrPC / Evidence Act 1872
- Acts on or after July 1, 2024 → BNS / BNSS / BSA 2023"""


def get_deepseek_provider() -> LLMProvider:
    """Get a configured DeepSeek-R1 LLM provider instance."""
    return get_llm_provider("deepseek")
