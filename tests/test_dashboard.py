from __future__ import annotations
from fastapi.testclient import TestClient
from consilo.dashboard.server import app
from consilo import kanban
from consilo.schemas import Ticket
from consilo.vault import ensure_project_skeleton


def _client():
    return TestClient(app)


def _seed_one_ticket(client="acme", project="digital-platform",
                     ticket_id="OC-T-001"):
    ensure_project_skeleton(client, project)
    kanban.write_ticket(Ticket(
        id=ticket_id, client=client, project=project,
        title="Draft Acme board readout deck for May 17",
        kind="deck-outline",
    ))


def test_healthz(tmp_workspace):
    r = _client().get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_index_lists_engagements(tmp_workspace):
    _seed_one_ticket()
    r = _client().get("/")
    assert r.status_code == 200
    assert "acme" in r.text
    assert "digital-platform" in r.text


def test_index_empty_state(tmp_workspace):
    r = _client().get("/")
    assert r.status_code == 200
    assert "No engagements yet" in r.text


def test_board_renders_ticket(tmp_workspace):
    _seed_one_ticket()
    r = _client().get("/board?client=acme&project=digital-platform")
    assert r.status_code == 200
    assert "OC-T-001" in r.text
    assert "Draft Acme board readout" in r.text
    assert "Backlog" in r.text


def test_board_columns_partial(tmp_workspace):
    _seed_one_ticket()
    r = _client().get("/board/columns?client=acme&project=digital-platform")
    assert r.status_code == 200
    assert "OC-T-001" in r.text
    assert "<html" not in r.text  # partial — no full layout


def test_ticket_detail(tmp_workspace):
    _seed_one_ticket()
    r = _client().get("/tickets/OC-T-001?client=acme&project=digital-platform")
    assert r.status_code == 200
    assert "OC-T-001" in r.text
    assert "Run slice" in r.text
    assert "Approve" in r.text


def test_run_then_approve_via_dashboard(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    _seed_one_ticket()
    c = _client()

    # Run slice — implementer + reviewer
    r = c.post("/tickets/OC-T-001/run",
               data={"client": "acme", "project": "digital-platform"})
    assert r.status_code == 200, r.text
    assert "Slice ran" in r.text or "Verdict" in r.text
    # The state should now be awaiting_approval
    r = c.get("/board?client=acme&project=digital-platform")
    assert "awaiting_approval" in r.text

    # Approve
    r = c.post("/tickets/OC-T-001/approve",
               data={"client": "acme", "project": "digital-platform",
                     "apply_suggestions": "1"})
    assert r.status_code == 200, r.text
    assert "Approved" in r.text

    # Done state visible on board
    r = c.get("/board?client=acme&project=digital-platform")
    assert "OC-T-001" in r.text
    assert "done" in r.text


def test_ticket_404(tmp_workspace):
    r = _client().get("/tickets/OC-T-999?client=acme&project=digital-platform")
    assert r.status_code == 404
