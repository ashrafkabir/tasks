from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM
    OPENCLAW_LLM_MODE: str = "stub"
    OPENCLAW_LLM_BASE_URL: str = "http://127.0.0.1:8080/v1"
    OPENCLAW_LLM_MODEL: str = "gemma-4-26B-A4B-it"
    OPENCLAW_LLM_API_KEY: str = "sk-local"

    # Embed
    OPENCLAW_EMBED_MODE: str = "stub"
    OPENCLAW_EMBED_BASE_URL: str = "http://127.0.0.1:8081/v1"
    OPENCLAW_EMBED_MODEL: str = "bge-m3"
    OPENCLAW_EMBED_API_KEY: str = "sk-local"
    OPENCLAW_EMBED_DIM: int = 384

    # Storage
    OPENCLAW_VAULT_DIR: str = str(REPO_ROOT / "vault")
    OPENCLAW_TASKS_REPO: str = str(REPO_ROOT / "tasks")
    OPENCLAW_SQLITE_PATH: str = str(REPO_ROOT / "data" / "openclaw.db")
    OPENCLAW_QDRANT_PATH: str = str(REPO_ROOT / "data" / "qdrant")
    OPENCLAW_QDRANT_URL: str | None = None

    OPENCLAW_LOG_LEVEL: str = "INFO"

    @property
    def vault_dir(self) -> Path:
        return Path(self.OPENCLAW_VAULT_DIR).resolve()

    @property
    def tasks_repo(self) -> Path:
        return Path(self.OPENCLAW_TASKS_REPO).resolve()

    @property
    def sqlite_path(self) -> Path:
        return Path(self.OPENCLAW_SQLITE_PATH).resolve()

    @property
    def qdrant_path(self) -> Path:
        return Path(self.OPENCLAW_QDRANT_PATH).resolve()


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """For tests."""
    global _settings
    _settings = None
