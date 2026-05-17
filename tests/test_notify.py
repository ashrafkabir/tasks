from __future__ import annotations
from consilo import notify, kanban
from consilo.schemas import Ticket
from consilo.vault import ensure_project_skeleton


def _ticket() -> Ticket:
    return Ticket(id="OC-T-100", client="acme", project="proj-a",
                  title="Test ticket", state="backlog", kind="deck-outline")


def test_stub_notify_records_to_sink(tmp_workspace, monkeypatch):
    notify.reset_sink()
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    notify.notify_awaiting_approval(_ticket())
    sink = notify.get_sink()
    assert len(sink) == 1
    assert sink[0]["channel"] == "stub"
    assert "OC-T-100" in sink[0]["text"]


def test_kanban_transition_fires_notify(tmp_workspace, monkeypatch):
    notify.reset_sink()
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    ensure_project_skeleton("acme", "proj-a")
    kanban.write_ticket(_ticket())
    kanban.transition("acme", "proj-a", "OC-T-100", "in_progress")
    assert notify.get_sink() == []  # no fire yet
    kanban.transition("acme", "proj-a", "OC-T-100", "awaiting_approval")
    sink = notify.get_sink()
    assert len(sink) == 1
    assert "OC-T-100" in sink[0]["text"]
