from __future__ import annotations
import pytest
from consilo.schemas import Ticket
from consilo import kanban
from consilo.vault import ensure_project_skeleton


def _make_ticket(state="backlog") -> Ticket:
    return Ticket(
        id="T-001", client="acme", project="proj-a",
        title="hello", state=state, kind="deck-outline",
    )


def test_full_happy_path(tmp_workspace):
    ensure_project_skeleton("acme", "proj-a")
    t = _make_ticket()
    kanban.write_ticket(t)
    assert kanban.load_ticket("acme", "proj-a", "T-001").state == "backlog"

    kanban.transition("acme", "proj-a", "T-001", "in_progress")
    kanban.transition("acme", "proj-a", "T-001", "awaiting_approval")
    kanban.transition("acme", "proj-a", "T-001", "approved")
    kanban.transition("acme", "proj-a", "T-001", "done")
    assert kanban.load_ticket("acme", "proj-a", "T-001").state == "done"


def test_illegal_transition_rejected(tmp_workspace):
    ensure_project_skeleton("acme", "proj-a")
    kanban.write_ticket(_make_ticket())
    with pytest.raises(ValueError):
        kanban.transition("acme", "proj-a", "T-001", "approved")


def test_no_terminal_resurrection(tmp_workspace):
    ensure_project_skeleton("acme", "proj-a")
    kanban.write_ticket(_make_ticket())
    kanban.transition("acme", "proj-a", "T-001", "in_progress")
    kanban.transition("acme", "proj-a", "T-001", "awaiting_approval")
    kanban.transition("acme", "proj-a", "T-001", "approved")
    kanban.transition("acme", "proj-a", "T-001", "done")
    with pytest.raises(ValueError):
        kanban.transition("acme", "proj-a", "T-001", "in_progress")
