from __future__ import annotations
from openclaw.bridges import commands
from openclaw import task_lifecycle, kanban
from openclaw.vault import project_dir


PRD_BODY = """\
# PRD — contoso/board-pitch

## 1. Goal
x

## 8. Ticket plan (initial)
- [deck-outline] Draft for contoso — passes reviewer
- [briefing] Brief for contoso — passes reviewer
"""


def test_help_lists_all_commands(tmp_workspace):
    reply = commands.dispatch("/help")
    assert "/start-task" in reply
    assert "/compile-prd" in reply
    assert "/approve-prd" in reply
    assert "/autoloop" in reply


def test_start_task_creates_skeleton(tmp_workspace, monkeypatch):
    reply = commands.dispatch("/start-task contoso board-pitch")
    assert "started contoso/board-pitch" in reply
    pd = project_dir("contoso", "board-pitch")
    assert (pd / "prd_answers.yaml").exists()


def test_compile_prd_via_chat(tmp_workspace):
    task_lifecycle.start_task("contoso", "board-pitch")
    pd = project_dir("contoso", "board-pitch")
    (pd / "prd_answers.yaml").write_text(
        "client: contoso\nproject: board-pitch\n"
        "artifacts: deck-outline; briefing\n"
        "cxo_goal: x\ntrigger: x\nconstraints: x\n"
        "capability: x\nsuccess_signal: x\nnon_goals: x\n"
    )
    reply = commands.dispatch("/compile-prd contoso board-pitch")
    assert "prd compiled" in reply
    assert (pd / "prd.md").exists()


def test_approve_prd_via_chat_with_autoloop(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("contoso", "board-pitch")
    (project_dir("contoso", "board-pitch") / "prd.md").write_text(PRD_BODY)
    reply = commands.dispatch("/approve-prd contoso board-pitch autoloop")
    assert "approved prd" in reply
    assert "autoloop" in reply
    # Both tickets should be at awaiting_approval after autoloop.
    awaiting = [t for t in kanban.list_tickets("contoso", "board-pitch")
                if t.state == "awaiting_approval"]
    assert len(awaiting) == 2


def test_autoloop_command(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("contoso", "board-pitch")
    (project_dir("contoso", "board-pitch") / "prd.md").write_text(PRD_BODY)
    task_lifecycle.approve_prd("contoso", "board-pitch")
    reply = commands.dispatch("/autoloop contoso board-pitch")
    assert "autoloop" in reply
    assert "awaiting=" in reply


def test_dispatch_returns_none_on_unknown(tmp_workspace):
    assert commands.dispatch("hello there") is None
    assert commands.dispatch("/unknown foo") is None


def test_just_spawned_ticket_surfaces(tmp_workspace):
    # /ticket itself is processed by ingest spawn rules; commands.dispatch
    # confirms it back if the caller passes just_spawned_ticket.
    reply = commands.dispatch("/ticket deck-outline foo", just_spawned_ticket="OC-T-001")
    assert "spawned ticket OC-T-001" in reply
