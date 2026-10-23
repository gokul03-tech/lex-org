"""Central application configuration using Pydantic Settings.

All configuration values are loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

import secrets as _secrets
import warnings
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository-relative locations, resolved from this file so no developer's
# absolute home directory is ever baked into defaults.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_MODELS_DIR = _PROJECT_ROOT / "models"


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    APP_NAME: str = "LexOrch-KG"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = ""  # Defaults to a random ephemeral key via validator below.
    API_PREFIX: str = "/api/v1"
    PROJECT_ROOT: Path = _PROJECT_ROOT
    MODELS_DIR: Path = _MODELS_DIR

    def model_post_init(self, __context) -> None:
        """Generate an ephemeral SECRET_KEY when none is configured."""
        if not self.SECRET_KEY or "change-me" in self.SECRET_KEY:
            self.SECRET_KEY = _secrets.token_urlsafe(48)
            warnings.warn(
                "SECRET_KEY is not set (or uses the insecure default). "
                "Generated a random ephemeral key — JWTs will be invalidated on restart. "
                "Set SECRET_KEY in your .env for production.",
                UserWarning,
                stacklevel=1,
            )

    # ── Server ──────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database (SQLite) ───────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/lexorch.db"
    DB_ECHO: bool = False

    # ── FalkorDB Knowledge Graph ────────────────────────────────
    FALKORDB_HOST: str = "localhost"
    FALKORDB_PORT: int = 6379
    FALKORDB_PASSWORD: str = ""
    FALKORDB_GRAPH_NAME: str = "lexorch"

    # ── Qdrant Vector Database ──────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_DOCS: str = "legal_documents"
    QDRANT_COLLECTION_SECTIONS: str = "legal_sections"
    QDRANT_VECTOR_SIZE: int = 1024  # BGE-M3 embedding dimension

    # ── Redis / Celery ──────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── LLM Configuration ───────────────────────────────────────
    LLM_BACKEND: Literal["llama_cpp", "mock", "openai_compatible", "transformers"] = "openai_compatible"
    QWEN_MODEL_PATH: str = str(_MODELS_DIR / "Qwen2.5-3B-Instruct-Q4_K_M.gguf")
    DEEPSEEK_MODEL_PATH: str = str(_MODELS_DIR / "Qwen2.5-3B-Instruct-Q4_K_M.gguf")
    LLM_N_CTX: int = 17000
    LLM_N_THREADS: int = 4
    LLM_N_GPU_LAYERS: int = 12
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 1500

    # OpenAI-compatible API configurations (vLLM / Ollama / OpenRouter)
    LLM_API_BASE: str = "https://openrouter.ai/api/v1"
    LLM_API_KEY: str = ""
    QWEN_MODEL_NAME: str = "meta-llama/llama-3.3-70b-instruct"
    DEEPSEEK_MODEL_NAME: str = "meta-llama/llama-3.3-70b-instruct"

    # ── Model routing (cost / rate-limit optimisation) ──────────
    # High-frequency, low-complexity tasks (noise filtering, formatting, intent
    # detection, query rewriting) run on FAST_MODEL_NAME; genuinely complex
    # reasoning (critic, verification, debate, strategy, research) runs on
    # STRONG_MODEL_NAME. With the openai_compatible backend these are provider
    # model ids. Both are set to the same Llama 3.3 70B model on OpenRouter so
    # every step uses a single model. Both GROQ_MODEL_* and FAST/STRONG_MODEL_NAME
    # env names are accepted (GROQ_* takes priority).
    FAST_MODEL_NAME: str = Field(
        "meta-llama/llama-3.3-70b-instruct",
        validation_alias=AliasChoices("GROQ_MODEL_FAST", "FAST_MODEL_NAME"),
    )
    STRONG_MODEL_NAME: str = Field(
        "meta-llama/llama-3.3-70b-instruct",
        validation_alias=AliasChoices("GROQ_MODEL_REASONING", "STRONG_MODEL_NAME"),
    )

    # ── LLM request retry / backoff ─────────────────────────────
    # Exponential backoff for transient provider errors (HTTP 429 / 5xx):
    # delay = min(base + 2**attempt, max) seconds, plus jitter.
    LLM_MAX_RETRIES: int = 5
    LLM_RETRY_BASE_DELAY: float = 5.0
    LLM_RETRY_MAX_DELAY: float = 60.0

    # Minimum seconds between Groq requests (a floor under the token-budget
    # pacing below). Small calls may fire faster; large ones are throttled by
    # GROQ_TPM.
    GROQ_MIN_INTERVAL: float = 2.0

    # Tokens-per-minute budget for the Groq endpoint (free on-demand tier is
    # 8,000 TPM, shared account-wide). Requests are paced so the rolling
    # 60-second total never exceeds this, which is what keeps the multi-agent
    # pipeline clear of HTTP 429s.
    GROQ_TPM: int = 8000

    # Groq's gpt-oss models are reasoning models: left unbounded they spend the
    # whole completion budget on hidden reasoning and return empty content (which
    # breaks structured JSON parsing). "low" keeps reasoning minimal.
    GROQ_REASONING_EFFORT: str = "low"

    # ── Google AI Studio (Gemini) ───────────────────────────────
    # When GEMINI_API_KEY is set it becomes the primary LLM endpoint (free
    # tier) and the LLM_API_BASE/LLM_API_KEY endpoint (e.g. OpenRouter) is used
    # as an automatic fallback. Both speak the OpenAI chat-completions protocol.
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Transformers local model configurations
    QWEN_HF_MODEL_ID: str = "Qwen/Qwen3-8B-AWQ"
    DEEPSEEK_HF_MODEL_ID: str = "casperhansen/deepseek-r1-distill-qwen-7b-awq"

    # Indian Kanoon API configurations
    INDIANKANOON_API_KEY: str = ""
    INDIANKANOON_API_BASE: str = "https://api.indiankanoon.org"

    # ── Embedding Model ─────────────────────────────────────────
    # MODELS_DIR (defined above) points at repo-root/models so weights are
    # not re-downloaded from the Hugging Face Hub on every startup.
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    # Optional Hugging Face token (authenticates Hub metadata checks).
    HF_TOKEN: str = ""
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32

    # ── Cloud Embedding Backend ─────────────────────────────────
    # "local"  -> sentence-transformers BGE-M3 (models/bge-m3)
    # "cloud"  -> OpenAI-compatible /embeddings endpoint (SiliconFlow by default)
    # "auto"   -> cloud when API base + key are set, else local
    EMBEDDING_BACKEND: Literal["local", "cloud", "auto"] = "auto"
    EMBEDDING_API_BASE: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_CLOUD_MODEL: str = "BAAI/bge-m3"
    # When the cloud endpoint fails, fall back to local BGE-M3 (per-request).
    EMBEDDING_ALLOW_LOCAL_FALLBACK: bool = True

    # ── Document Processing ─────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    OCR_LANG: str = "en"
    OCR_USE_GPU: bool = False
    # Cap the OCR-repair pre-pass to the leading N characters of a document
    # (0 = repair the whole document). The caption/issues band matters most, so
    # a small cap cuts LLM cost/latency on long scanned judgments.
    OCR_CLEAN_MAX_CHARS: int = 3000
    # Vision-LLM OCR fallback: when PyMuPDF text is too short or too garbled,
    # re-read the first pages as images through a multimodal model. Uses the
    # Gemini endpoint (same key as the primary LLM) by default; any
    # OpenAI-compatible vision endpoint works.
    VLM_OCR_ENABLED: bool = True
    VLM_OCR_MODEL: str = "google/gemini-2.5-flash"
    VLM_OCR_MAX_PAGES: int = 5
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Sandbox ─────────────────────────────────────────────────
    SANDBOX_BACKEND: Literal["docker", "process", "none"] = "process"
    SANDBOX_TIMEOUT: int = 120
    SANDBOX_MAX_MEMORY_MB: int = 4096
    SANDBOX_MAX_CPU_CORES: int = 2

    # ── Dataset Paths ───────────────────────────────────────────
    DATASETS_DIR: Path = Path("datasets")
    ACTS_DIR: Path = Path("datasets/acts")
    CONSTITUTION_DIR: Path = Path("datasets/constitution")
    LEGAL_CORPUS_DIR: Path = Path("datasets/datasets/legal_corpus")

    # ── Security ────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_BCRYPT_ROUNDS: int = 12

    # ── Logging ─────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"
    LOG_FILE: str = "logs/app.log"

    # ── Evaluation ──────────────────────────────────────────────
    EVAL_OUTPUT_DIR: str = "outputs/evaluation"
    EVAL_RUN_ON_STARTUP: bool = False


# Singleton instance
settings = Settings()
