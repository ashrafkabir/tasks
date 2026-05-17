from __future__ import annotations
import json
import yaml
from consilo import worker, task_lifecycle, kanban, sqlite_store
from consilo.vault import project_dir, ensure_project_skeleton


PRD_BODY = """\
# PRD

## 8. Ticket plan (initial)
- [deck-outline] Draft for x — accept
- [briefing] Brief for x — accept
"""


def _setup_project(client="acme", project="digital-platform", *, approve=True,
                   enable_via="project_yaml"):
    """Create a project with an approved PRD + 2 backlog tickets."""
    task_lifecycle.start_task(client, project)
    pd = project_dir(client, project)
    (pd / "prd.md").write_text(PRD_BODY)
    if approve:
        task_lifecycle.approve_prd(client, project)
    # Opt the project in.
    if enable_via == "project_yaml":
        pyaml = pd / "project.yaml"
        data = yaml.safe_load(pyaml.read_text()) or {}
        data["autoloop_enabled"] = True
        pyaml.write_text(yaml.safe_dump(data, sort_keys=False))


def test_tick_processes_opted_in_project(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    _setup_project()
    r = worker.tick(worker_id="test", max_iter_per_project=10)
    processed = r["processed"]
    assert len(processed) == 1
    assert processed[0]["client"] == "acme"
    assert processed[0]["project"] == "digital-platform"
    assert processed[0]["iterations"] == 2
    # No backlog tickets remain (all advanced to awaiting_approval).
    backlog = [t for t in kanban.list_tickets("acme", "digital-platform")
               if t.state == "backlog"]
    assert not backlog


def test_tick_skips_unopted_in(tmp_workspace, monkeypatch):
    """A project without autoloop_enabled and not in worker.yaml is skipped."""
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    _setup_project(enable_via="none")
    # Remove the opt-in we added by default
    pyaml = project_dir("acme", "digital-platform") / "project.yaml"
    data = yaml.safe_load(pyaml.read_text())
    data.pop("autoloop_enabled", None)
    pyaml.write_text(yaml.safe_dump(data, sort_keys=False))
    r = worker.tick(worker_id="test")
    assert r["processed"] == []


def test_tick_skips_unapproved_prd(tmp_workspace, monkeypatch):
    """A project with autoloop_enabled but no prd.approved.md is skipped."""
    task_lifecycle.start_task("acme", "digital-platform")
    pd = project_dir("acme", "digital-platform")
    pyaml = pd / "project.yaml"
    data = yaml.safe_load(pyaml.read_text())
    data["autoloop_enabled"] = True
    pyaml.write_text(yaml.safe_dump(data, sort_keys=False))
    # Backlog tickets exist but PRD never approved.
    kanban.write_ticket(__import__("consilo").schemas.Ticket(
        id="OC-T-001", client="acme", project="digital-platform",
        title="Stray", state="backlog", kind="deck-outline",
    ))
    r = worker.tick(worker_id="test")
    assert r["processed"] == []


def test_worker_yaml_opt_in(tmp_workspace, monkeypatch):
    """A project listed in vault/shared/worker.yaml is opted in even without
    autoloop_enabled in project.yaml."""
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    _setup_project(enable_via="none")
    from consilo.config import get_settings
    cfg = get_settings().vault_dir / "shared" / "worker.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(yaml.safe_dump({
        "enable": [{"client": "acme", "project": "digital-platform"}],
    }))
    r = worker.tick(worker_id="test", max_iter_per_project=10)
    assert len(r["processed"]) == 1


def test_run_once_writes_heartbeat(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_NOTIFY_MODE", "stub")
    _setup_project()
    r = worker.run(interval=1, once=True, max_iter_per_project=10)
    assert r["iterations"] == 1
    workers = sqlite_store.list_workers()
    assert len(workers) == 1
    assert workers[0]["worker_id"] == r["worker_id"]
    assert workers[0]["iterations"] == 1
    # Final payload reflects the "stopped" record.
    payload = json.loads(workers[0]["last_payload"])
    assert payload["status"] == "stopped"
