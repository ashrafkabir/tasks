"""Shared pytest fixtures — point each test at a fresh tmp vault/data."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
from consilo import config


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONSILO_LLM_MODE", "stub")
    monkeypatch.setenv("CONSILO_EMBED_MODE", "stub")
    monkeypatch.setenv("CONSILO_VAULT_DIR", str(tmp_path / "vault"))
    monkeypatch.setenv("CONSILO_TASKS_REPO", str(tmp_path / "tasks"))
    monkeypatch.setenv("CONSILO_SQLITE_PATH", str(tmp_path / "data" / "consilo.db"))
    monkeypatch.setenv("CONSILO_QDRANT_PATH", str(tmp_path / "data" / "qdrant"))
    monkeypatch.delenv("CONSILO_QDRANT_URL", raising=False)
    config.reset_settings()
    yield tmp_path
    config.reset_settings()
