from __future__ import annotations
from pathlib import Path
import yaml
import pytest

from openclaw import task_lifecycle, kanban
from openclaw.agents import planner, interviewer
from openclaw.vault import project_dir


PRD_BODY = """\
# PRD — acme/board-pitch

**Owner:** Ashraf · **Date:** 2026-05-17

## 1. The CxO and the goal
CFO wants 2pp opex reduction by EOY.

## 2. Triggering event and time window
Q1 letter cites ERP downtime. Board meets in 14 days.

## 3. Artifacts to produce
deck-outline; briefing; talking-points

## 4. Constraints
Recent vendor incumbent must be acknowledged, not attacked.

## 5. Visionet positioning
Platform consolidation IP.

## 6. Success criteria
CIO requests a 30-min staff slot.

## 7. Non-goals
No RFP response yet.

## 8. Ticket plan (initial)
- [deck-outline] Draft board readout deck for Acme — markdown w/ speaker notes
- [briefing] Draft CFO briefing for Acme — 1-pager
- [talking-points] Talking-points sheet for Acme — bullets only
"""


def test_start_task_creates_folder_and_skeleton(tmp_workspace):
    r = task_lifecycle.start_task("acme", "board-pitch")
    pd = project_dir("acme", "board-pitch")
    assert pd.exists()
    assert (pd / "project.yaml").exists()
    answers = pd / "prd_answers.yaml"
    assert answers.exists()
    assert "client: acme" in answers.read_text()
    assert "project: board-pitch" in answers.read_text()
    # idempotent
    answers.write_text("custom: content")
    task_lifecycle.start_task("acme", "board-pitch")
    assert "custom: content" in answers.read_text()


def test_compile_prd_emits_prd_with_ticket_plan(tmp_workspace):
    task_lifecycle.start_task("acme", "board-pitch")
    pd = project_dir("acme", "board-pitch")
    (pd / "prd_answers.yaml").write_text(yaml.safe_dump({
        "client": "acme", "project": "board-pitch",
        "cxo_goal": "CFO wants opex down",
        "trigger": "Q1 letter",
        "artifacts": "deck-outline, briefing",
        "constraints": "Politics",
        "capability": "Platform IP",
        "success_signal": "CIO meeting",
        "non_goals": "no RFP",
    }))
    r = task_lifecycle.compile_prd("acme", "board-pitch")
    prd = Path(r["prd_path"]).read_text()
    assert "# PRD — acme/board-pitch" in prd
    assert "## 8. Ticket plan" in prd
    assert "[deck-outline]" in prd
    assert "[briefing]" in prd


def test_compile_prd_without_skeleton_errors(tmp_workspace):
    with pytest.raises(FileNotFoundError):
        task_lifecycle.compile_prd("acme", "missing")


def test_planner_parses_ticket_plan():
    plan = planner.parse_plan(PRD_BODY)
    assert len(plan) == 3
    assert plan[0]["kind"] == "deck-outline"
    assert plan[1]["kind"] == "briefing"
    assert plan[2]["kind"] == "talking-points"
    assert "board readout deck" in plan[0]["title"]


def test_approve_prd_spawns_tickets(tmp_workspace):
    task_lifecycle.start_task("acme", "board-pitch")
    pd = project_dir("acme", "board-pitch")
    (pd / "prd.md").write_text(PRD_BODY)
    r = task_lifecycle.approve_prd("acme", "board-pitch")
    assert r["ticket_count"] == 3
    ids = r["ticket_ids"]
    assert ids == ["OC-T-001", "OC-T-002", "OC-T-003"]
    assert (pd / "prd.approved.md").exists()
    backlog = kanban.list_tickets("acme", "board-pitch", "backlog")
    assert len(backlog) == 3


def test_approve_prd_without_plan_section_errors(tmp_workspace):
    task_lifecycle.start_task("acme", "board-pitch")
    (project_dir("acme", "board-pitch") / "prd.md").write_text(
        "# PRD\n\n## 1. Foo\nx"
    )
    with pytest.raises(ValueError):
        task_lifecycle.approve_prd("acme", "board-pitch")


def test_autoloop_drives_all_backlog_to_awaiting(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("acme", "board-pitch")
    (project_dir("acme", "board-pitch") / "prd.md").write_text(PRD_BODY)
    task_lifecycle.approve_prd("acme", "board-pitch")

    r = task_lifecycle.autoloop("acme", "board-pitch", max_iter=10)
    assert r["iterations"] == 3
    assert set(r["awaiting_approval"]) == {"OC-T-001", "OC-T-002", "OC-T-003"}
    # No backlog tickets remain — they're all awaiting approval.
    assert not kanban.list_tickets("acme", "board-pitch", "backlog")


def test_autoloop_respects_max_iter(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("acme", "board-pitch")
    (project_dir("acme", "board-pitch") / "prd.md").write_text(PRD_BODY)
    task_lifecycle.approve_prd("acme", "board-pitch")

    r = task_lifecycle.autoloop("acme", "board-pitch", max_iter=2)
    assert r["iterations"] == 2
    assert len(r["awaiting_approval"]) == 2
    assert len(kanban.list_tickets("acme", "board-pitch", "backlog")) == 1


def test_approve_prd_with_autoloop_combined(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("acme", "board-pitch")
    (project_dir("acme", "board-pitch") / "prd.md").write_text(PRD_BODY)
    r = task_lifecycle.approve_prd("acme", "board-pitch", run_autoloop=True)
    assert "autoloop" in r
    assert r["autoloop"]["iterations"] == 3
