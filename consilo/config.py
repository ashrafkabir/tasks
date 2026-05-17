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
    CONSILO_LLM_MODE: str = "stub"
    CONSILO_LLM_BASE_URL: str = "http://127.0.0.1:8080/v1"
    CONSILO_LLM_MODEL: str = "gemma-4-26B-A4B-it"
    CONSILO_LLM_API_KEY: str = "sk-local"

    # Embed
    CONSILO_EMBED_MODE: str = "stub"
    CONSILO_EMBED_BASE_URL: str = "http://127.0.0.1:8081/v1"
    CONSILO_EMBED_MODEL: str = "bge-m3"
    CONSILO_EMBED_API_KEY: str = "sk-local"
    CONSILO_EMBED_DIM: int = 384

    # Storage
    CONSILO_VAULT_DIR: str = str(REPO_ROOT / "vault")
    CONSILO_TASKS_REPO: str = str(REPO_ROOT / "tasks")
    CONSILO_SQLITE_PATH: str = str(REPO_ROOT / "data" / "consilo.db")
    CONSILO_QDRANT_PATH: str = str(REPO_ROOT / "data" / "qdrant")
    CONSILO_QDRANT_URL: str | None = None

    CONSILO_LOG_LEVEL: str = "INFO"

    @property
    def vault_dir(self) -> Path:
        return Path(self.CONSILO_VAULT_DIR).resolve()

    @property
    def tasks_repo(self) -> Path:
        return Path(self.CONSILO_TASKS_REPO).resolve()

    @property
    def sqlite_path(self) -> Path:
        return Path(self.CONSILO_SQLITE_PATH).resolve()

    @property
    def qdrant_path(self) -> Path:
        return Path(self.CONSILO_QDRANT_PATH).resolve()


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
