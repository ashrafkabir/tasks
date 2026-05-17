from __future__ import annotations
from fastapi.testclient import TestClient
from openclaw.dashboard.server import app
from openclaw import task_lifecycle, kanban
from openclaw.vault import project_dir
import yaml


def _client():
    return TestClient(app)


def test_new_task_page_renders(tmp_workspace):
    r = _client().get("/new-task")
    assert r.status_code == 200
    assert "Start a new task" in r.text
    assert 'name="client"' in r.text


def test_new_task_submit_creates_skeleton_and_redirects(tmp_workspace):
    c = _client()
    r = c.post("/new-task", data={"client": "Contoso", "project": "Board-Pitch"},
               follow_redirects=False)
    assert r.status_code == 303
    assert "/prd?client=contoso&project=board-pitch" in r.headers["location"]
    pd = project_dir("contoso", "board-pitch")
    assert (pd / "prd_answers.yaml").exists()


def test_prd_page_404_for_missing_project(tmp_workspace):
    r = _client().get("/prd?client=nope&project=nope")
    assert r.status_code == 404


def test_prd_page_renders_with_skeleton(tmp_workspace):
    task_lifecycle.start_task("contoso", "board-pitch")
    r = _client().get("/prd?client=contoso&project=board-pitch")
    assert r.status_code == 200
    assert "prd_answers.yaml" in r.text
    assert "Compile PRD" in r.text
    assert "Approve PRD" in r.text


def test_prd_save_writes_answers(tmp_workspace):
    task_lifecycle.start_task("contoso", "board-pitch")
    new_yaml = ("client: contoso\nproject: board-pitch\n"
                "artifacts: deck-outline\ncxo_goal: edited\n")
    r = _client().post("/prd/save", data={
        "client": "contoso", "project": "board-pitch",
        "answers_text": new_yaml,
    })
    assert r.status_code == 200
    assert "Answers saved" in r.text
    p = project_dir("contoso", "board-pitch") / "prd_answers.yaml"
    assert p.read_text() == new_yaml


def test_prd_compile_then_approve_via_dashboard(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("contoso", "board-pitch")
    pd = project_dir("contoso", "board-pitch")
    (pd / "prd_answers.yaml").write_text(
        "client: contoso\nproject: board-pitch\n"
        "artifacts: deck-outline; briefing\ncxo_goal: x\ntrigger: x\n"
        "constraints: x\ncapability: x\nsuccess_signal: x\nnon_goals: x\n"
    )
    c = _client()
    r = c.post("/prd/compile", data={"client": "contoso", "project": "board-pitch"})
    assert r.status_code == 200
    assert "PRD compiled" in r.text
    assert (pd / "prd.md").exists()

    r = c.post("/prd/approve", data={
        "client": "contoso", "project": "board-pitch",
        "run_autoloop": "1",
    })
    assert r.status_code == 200
    assert "PRD approved" in r.text
    assert "Autoloop" in r.text
    awaiting = [t for t in kanban.list_tickets("contoso", "board-pitch")
                if t.state == "awaiting_approval"]
    assert len(awaiting) == 2


def test_board_autoloop_button(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    task_lifecycle.start_task("contoso", "board-pitch")
    pd = project_dir("contoso", "board-pitch")
    (pd / "prd.md").write_text(
        "# PRD\n\n## 8. Ticket plan (initial)\n"
        "- [deck-outline] Draft — accept\n"
    )
    task_lifecycle.approve_prd("contoso", "board-pitch")
    r = _client().post("/board/autoloop", data={
        "client": "contoso", "project": "board-pitch",
    })
    assert r.status_code == 200
    assert "awaiting_approval" in r.text
    assert "iterations" in r.text or "Autoloop" in r.text


def test_header_has_new_task_link(tmp_workspace):
    r = _client().get("/")
    assert 'href="/new-task"' in r.text
