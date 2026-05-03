"""Shared pytest fixtures — point each test at a fresh tmp vault/data."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
from openclaw import config


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENCLAW_LLM_MODE", "stub")
    monkeypatch.setenv("OPENCLAW_EMBED_MODE", "stub")
    monkeypatch.setenv("OPENCLAW_VAULT_DIR", str(tmp_path / "vault"))
    monkeypatch.setenv("OPENCLAW_TASKS_REPO", str(tmp_path / "tasks"))
    monkeypatch.setenv("OPENCLAW_SQLITE_PATH", str(tmp_path / "data" / "openclaw.db"))
    monkeypatch.setenv("OPENCLAW_QDRANT_PATH", str(tmp_path / "data" / "qdrant"))
    monkeypatch.delenv("OPENCLAW_QDRANT_URL", raising=False)
    config.reset_settings()
    yield tmp_path
    config.reset_settings()
