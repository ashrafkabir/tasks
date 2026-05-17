from __future__ import annotations
from fastapi.testclient import TestClient
from consilo.dashboard.server import app
from consilo.schemas import Client, Ticket
from consilo.vault import client_dir, ensure_project_skeleton
from consilo import kanban
import yaml


def _setup(monkeypatch):
    ensure_project_skeleton("acme", "digital-platform")
    cd = client_dir("acme")
    cd.mkdir(parents=True, exist_ok=True)
    (cd / "client.yaml").write_text(yaml.safe_dump(
        Client(slug="acme", display_name="Acme Manufacturing").model_dump()
    ))
    (cd / "memory.md").write_text(
        "# acme — durable memory\n\n## 2026-05-04 — curation run abc (1 facts from 1 events)\n"
        "- **subject:** acme\n  **claim:** Q1 letter signals modernization budget\n"
    )
    kanban.write_ticket(Ticket(
        id="OC-T-001", client="acme", project="digital-platform",
        title="Draft readout", state="backlog", kind="deck-outline",
    ))


def test_client_page_renders(tmp_workspace, monkeypatch):
    _setup(monkeypatch)
    r = TestClient(app).get("/clients/acme")
    assert r.status_code == 200
    text = r.text
    assert "Acme" in text or "acme" in text
    assert "memory.md" in text
    assert "modernization budget" in text
    assert "digital-platform" in text


def test_client_404(tmp_workspace):
    r = TestClient(app).get("/clients/nope")
    assert r.status_code == 404


def test_client_link_on_index(tmp_workspace, monkeypatch):
    _setup(monkeypatch)
    r = TestClient(app).get("/")
    assert 'href="/clients/acme"' in r.text


def test_client_page_handles_no_memory(tmp_workspace):
    ensure_project_skeleton("acme", "digital-platform")
    client_dir("acme").mkdir(parents=True, exist_ok=True)
    r = TestClient(app).get("/clients/acme")
    assert r.status_code == 200
    assert "No durable memory yet" in r.text
