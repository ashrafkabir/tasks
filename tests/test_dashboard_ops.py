from __future__ import annotations
from unittest.mock import patch
from fastapi.testclient import TestClient

from openclaw.dashboard.server import app
from openclaw.dashboard import health as health_probe
from openclaw import task_lifecycle, worker, sqlite_store
from openclaw.vault import project_dir


def _client():
    return TestClient(app)


def test_ops_health_json_offline_returns_failures(tmp_workspace):
    # Wipe the probe cache to force fresh failures (services not running in CI).
    health_probe._CACHE.clear()
    r = _client().get("/ops/health.json")
    assert r.status_code == 200
    data = r.json()
    assert "services" in data
    assert data["total"] >= 3
    # All services should be down in a clean test environment.
    for s in data["services"]:
        assert s["ok"] is False


def test_ops_health_json_with_mocked_ok(tmp_workspace):
    health_probe._CACHE.clear()
    with patch.object(health_probe, "_probe",
                      return_value={"name": "x", "ok": True, "status": 200}):
        r = _client().get("/ops/health.json")
    data = r.json()
    assert data["ok_count"] == data["total"]


def test_ops_feed_json_empty(tmp_workspace):
    r = _client().get("/ops/feed.json")
    assert r.status_code == 200
    assert r.json() == {"feed": []}


def test_ops_page_renders(tmp_workspace, monkeypatch):
    health_probe._CACHE.clear()
    monkeypatch.setenv("OPENCLAW_NOTIFY_MODE", "stub")
    # Seed one engagement, run one tick to produce activity rows.
    task_lifecycle.start_task("acme", "digital-platform")
    pd = project_dir("acme", "digital-platform")
    (pd / "prd.md").write_text(
        "# PRD\n\n## 8. Ticket plan (initial)\n- [deck-outline] Draft — ok\n"
    )
    task_lifecycle.approve_prd("acme", "digital-platform")
    import yaml
    pyaml = pd / "project.yaml"
    data = yaml.safe_load(pyaml.read_text())
    data["autoloop_enabled"] = True
    pyaml.write_text(yaml.safe_dump(data, sort_keys=False))
    worker.run(interval=1, once=True, max_iter_per_project=5)

    r = _client().get("/ops")
    assert r.status_code == 200
    t = r.text
    assert "Ops console" in t
    assert "Services" in t
    assert "acme / digital-platform" in t
    # At least one feed row from runs
    assert ">run<" in t or "run</span>" in t


def test_ops_panel_partial(tmp_workspace):
    health_probe._CACHE.clear()
    r = _client().get("/ops/panel")
    assert r.status_code == 200
    # Should be a partial — no <html> shell
    assert "<html" not in r.text
    assert "Services" in r.text


def test_ops_link_in_header(tmp_workspace):
    r = _client().get("/")
    assert 'href="/ops"' in r.text
