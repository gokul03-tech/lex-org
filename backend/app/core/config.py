"""Central application configuration using Pydantic Settings.

All configuration values are loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

import secrets as _secrets
import warnings
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
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
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

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
    LLM_BACKEND: Literal["llama_cpp", "mock", "openai_compatible", "transformers"] = "mock"
    QWEN_MODEL_PATH: str = ""
    DEEPSEEK_MODEL_PATH: str = ""
    LLM_N_CTX: int = 8192
    LLM_N_THREADS: int = 8
    LLM_N_GPU_LAYERS: int = 0
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    # OpenAI-compatible API configurations (vLLM / Ollama)
    LLM_API_BASE: str = "http://localhost:8000/v1"
    LLM_API_KEY: str = ""
    QWEN_MODEL_NAME: str = "Qwen/Qwen3-8B-AWQ"
    # NOTE: deepseek-ai never released an 8B Qwen distill; use the 7B AWQ quant
    DEEPSEEK_MODEL_NAME: str = "casperhansen/deepseek-r1-distill-qwen-7b-awq"

    # Transformers local model configurations
    QWEN_HF_MODEL_ID: str = "Qwen/Qwen3-8B-AWQ"
    DEEPSEEK_HF_MODEL_ID: str = "casperhansen/deepseek-r1-distill-qwen-7b-awq"

    # Indian Kanoon API configurations
    INDIANKANOON_API_KEY: str = ""
    INDIANKANOON_API_BASE: str = "https://api.indiankanoon.org"

    # ── Embedding Model ─────────────────────────────────────────
    # Local storage for model weights (repo-root/models). Used to avoid
    # re-downloading models from the Hugging Face Hub on every startup.
    MODELS_DIR: Path = Path(__file__).resolve().parents[3] / "models"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    # Optional Hugging Face token (authenticates Hub metadata checks).
    HF_TOKEN: str = ""
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32

    # ── Document Processing ─────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    OCR_LANG: str = "en"
    OCR_USE_GPU: bool = False
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
