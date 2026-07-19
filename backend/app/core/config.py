"""Central application configuration using Pydantic Settings.

All configuration values are loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

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
    SECRET_KEY: str = "change-me-in-production-use-a-secure-random-key"
    API_PREFIX: str = "/api/v1"
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

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
    LLM_BACKEND: Literal["llama_cpp", "mock", "openai_compatible"] = "mock"
    QWEN_MODEL_PATH: str = ""
    DEEPSEEK_MODEL_PATH: str = ""
    LLM_N_CTX: int = 8192
    LLM_N_THREADS: int = 8
    LLM_N_GPU_LAYERS: int = 0
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    # ── Embedding Model ─────────────────────────────────────────
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
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
