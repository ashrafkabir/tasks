from __future__ import annotations
from openclaw.ingest import ingest, InboundMessage
from openclaw.vault import events_dir, kanban_path
from openclaw import sqlite_store


def test_plain_message_creates_event(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("OPENCLAW_DEFAULT_PROJECT", "digital-platform")

    msg = InboundMessage(
        source="telegram", chat_id="42", message_id="1",
        sender="ashraf", text="Acme CFO mentioned modernization budget today.",
        received_at="2026-05-03T18:00:00+00:00",
    )
    summary = ingest(msg)

    assert summary["client"] == "acme"
    assert summary["project"] == "digital-platform"
    assert summary["ticket"] is None  # no /ticket command
    assert summary["event_path"]

    evs = list(events_dir("acme", "digital-platform").glob("*.md"))
    assert len(evs) == 1
    assert "Acme CFO" in evs[0].read_text()

    rows = sqlite_store.recent_events("acme", "digital-platform")
    assert len(rows) == 1
    assert rows[0]["source"] == "telegram"


def test_ticket_command_spawns_ticket(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("OPENCLAW_DEFAULT_PROJECT", "digital-platform")

    msg = InboundMessage(
        source="whatsapp", chat_id="12025550100@s.whatsapp.net", message_id="m1",
        sender="ashraf", text="/ticket deck-outline Draft Q2 board readout",
    )
    summary = ingest(msg)

    assert summary["ticket"] == "OC-T-001"
    backlog = list(kanban_path("acme", "digital-platform", "backlog").glob("*.yaml"))
    assert len(backlog) == 1
    assert "Draft Q2 board readout" in backlog[0].read_text()


def test_unrouted_when_no_default(tmp_workspace, monkeypatch):
    monkeypatch.delenv("OPENCLAW_DEFAULT_CLIENT", raising=False)
    monkeypatch.delenv("OPENCLAW_DEFAULT_PROJECT", raising=False)
    msg = InboundMessage(
        source="telegram", chat_id="999", message_id="2",
        sender="stranger", text="random ping",
    )
    summary = ingest(msg)
    assert summary["client"] == "_unrouted"
    assert summary["project"] == "_unrouted"


def test_explicit_route_overrides_default(tmp_workspace, monkeypatch):
    """chat_routes.yaml should win over env defaults."""
    import yaml
    s_dir = tmp_workspace / "vault" / "shared"
    s_dir.mkdir(parents=True, exist_ok=True)
    (s_dir / "chat_routes.yaml").write_text(yaml.safe_dump({
        "routes": [
            {"source": "telegram", "chat_id": 7777,
             "client": "contoso", "project": "ai-rollout"},
        ],
    }))
    monkeypatch.setenv("OPENCLAW_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("OPENCLAW_DEFAULT_PROJECT", "digital-platform")

    msg = InboundMessage(source="telegram", chat_id="7777", message_id="3",
                         sender="x", text="hello")
    summary = ingest(msg)
    assert summary["client"] == "contoso"
    assert summary["project"] == "ai-rollout"
