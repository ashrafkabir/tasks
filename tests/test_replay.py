from __future__ import annotations
import json
from pathlib import Path
import pytest
from consilo import service, replay
from consilo.schemas import Ticket, Project
from consilo.vault import ensure_project_skeleton, project_dir
from consilo import kanban, sqlite_store
from consilo.ingest import ingest, InboundMessage
import yaml


def _seed():
    ensure_project_skeleton("acme", "digital-platform")
    proj = Project(slug="digital-platform", client="acme",
                   display_name="Digital Platform", objective="x", status="active")
    (project_dir("acme", "digital-platform") / "project.yaml").write_text(
        yaml.safe_dump(proj.model_dump(), sort_keys=False))
    kanban.write_ticket(Ticket(
        id="OC-T-001", client="acme", project="digital-platform",
        title="Draft readout", state="backlog", kind="deck-outline",
    ))


def test_replay_implementer_run(tmp_workspace):
    _seed()
    r = service.run_slice("acme", "digital-platform", "OC-T-001")
    impl_run_id = r["implementer"]["run_id"]

    res = replay.replay(run_id=impl_run_id, client="acme",
                        project="digital-platform", ticket_id="OC-T-001")
    assert res["agent"] == "implementer"
    assert res["replayed_from"] == impl_run_id
    new_audit = json.loads(Path(res["new_audit"]).read_text())
    assert new_audit["replay_of"] == impl_run_id
    assert "replayed_at" in new_audit


def test_replay_reviewer_run(tmp_workspace):
    _seed()
    r = service.run_slice("acme", "digital-platform", "OC-T-001")
    rev_run_id = r["reviewer"]["run_id"]
    res = replay.replay(run_id=rev_run_id, client="acme",
                        project="digital-platform", ticket_id="OC-T-001")
    assert res["agent"] == "reviewer"
    new_audit = json.loads(Path(res["new_audit"]).read_text())
    assert new_audit["replay_of"] == rev_run_id


def test_replay_briefer_run(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("CONSILO_DEFAULT_PROJECT", "digital-platform")
    _seed()
    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="m1",
        sender="x", text="Acme CFO confirmed budget."))
    from consilo.agents import briefer
    first = briefer.run("acme", "digital-platform")

    res = replay.replay(run_id=first["run_id"], client="acme",
                        project="digital-platform")
    assert res["agent"] == "briefer"
    assert res["replayed_from"] == first["run_id"]
    new_audit = json.loads(Path(res["new_audit"]).read_text())
    assert new_audit["replay_of"] == first["run_id"]


def test_replay_missing_audit_raises(tmp_workspace):
    with pytest.raises(FileNotFoundError):
        replay.replay(run_id="20260101T000000Z-deadbeef", client="acme",
                      project="digital-platform", ticket_id="OC-T-001")


def test_replay_unsupported_agent(tmp_workspace):
    _seed()
    pd = project_dir("acme", "digital-platform")
    fake_audit_dir = pd / "audit" / "OC-T-001"
    fake_audit_dir.mkdir(parents=True, exist_ok=True)
    rid = "20260101T000000Z-fake1234"
    (fake_audit_dir / f"{rid}.json").write_text(json.dumps({
        "agent": "memory-curator", "client": "acme", "project": "digital-platform",
        "ticket_id": "OC-T-001",
    }))
    with pytest.raises(ValueError):
        replay.replay(run_id=rid, client="acme", project="digital-platform",
                      ticket_id="OC-T-001")
