from __future__ import annotations
import json
from pathlib import Path
from openclaw.ingest import ingest, InboundMessage
from openclaw.agents import briefer
from openclaw.vault import briefs_dir, project_dir
from openclaw.schemas import Project
from openclaw.vault import client_dir, ensure_project_skeleton
import yaml


def _seed_project_with_event(monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("OPENCLAW_DEFAULT_PROJECT", "digital-platform")
    ensure_project_skeleton("acme", "digital-platform")
    proj = Project(slug="digital-platform", client="acme",
                   display_name="Digital Platform",
                   objective="Consolidate ERP+MES into a single platform.",
                   status="active")
    (project_dir("acme", "digital-platform") / "project.yaml").write_text(
        yaml.safe_dump(proj.model_dump(), sort_keys=False))
    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="1",
        sender="ashraf",
        text="Acme CFO confirmed $12M modernization budget; board readout in 2 weeks.",
        received_at="2026-05-03T18:00:00+00:00",
    ))


def test_briefer_writes_brief_and_audit(tmp_workspace, monkeypatch):
    _seed_project_with_event(monkeypatch)
    result = briefer.run("acme", "digital-platform")
    assert result["event_id"]
    brief = Path(result["brief_path"]).read_text()
    assert "# Briefing" in brief
    assert "Headline" in brief
    assert "Key facts" in brief
    assert "Recommended next moves" in brief

    audit = json.loads(Path(result["audit_path"]).read_text())
    assert audit["agent"] == "briefer"
    assert audit["llm_mode"] == "stub"
    assert audit["brief_chars"] > 200


def test_briefer_uses_specific_event_id(tmp_workspace, monkeypatch):
    _seed_project_with_event(monkeypatch)
    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="2",
        sender="ashraf", text="A second, less critical update about logistics.",
        received_at="2026-05-04T18:00:00+00:00",
    ))
    # Pick the *first* (older) event explicitly.
    from openclaw import sqlite_store
    events = sqlite_store.list_client_events("acme", "digital-platform")
    older = events[0]["id"]
    result = briefer.run("acme", "digital-platform", event_id=older)
    assert result["event_id"] == older


def test_briefer_404_on_missing_event(tmp_workspace, monkeypatch):
    _seed_project_with_event(monkeypatch)
    import pytest
    with pytest.raises(FileNotFoundError):
        briefer.run("acme", "digital-platform", event_id="evt-does-not-exist")


def test_briefer_no_events_still_writes_default(tmp_workspace):
    """No events shouldn't crash; brief is generic."""
    ensure_project_skeleton("acme", "digital-platform")
    result = briefer.run("acme", "digital-platform")
    assert result["event_id"] is None
    brief = Path(result["brief_path"]).read_text()
    assert "Briefing" in brief
