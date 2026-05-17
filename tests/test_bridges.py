from __future__ import annotations
from unittest.mock import patch, MagicMock
import json

from consilo.bridges import telegram, whatsapp
from consilo.bridges import server as bridge_server
from consilo.vault import events_dir, kanban_path


# ---------- Telegram ----------

def _tg_update(text: str, chat_id: int = 42, message_id: int = 1) -> dict:
    return {
        "update_id": 1000,
        "message": {
            "message_id": message_id,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id, "username": "ashraf", "first_name": "Ashraf"},
            "date": 1746288000,
            "text": text,
        },
    }


def test_telegram_inbound_text_creates_event(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("CONSILO_DEFAULT_PROJECT", "digital-platform")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    # No operator chat configured → don't try to reply on slash commands.
    monkeypatch.delenv("TELEGRAM_OPERATOR_CHAT_ID", raising=False)

    fake = MagicMock()
    fake.json.return_value = {"ok": True, "result": [_tg_update("Acme update from CFO")]}
    fake.raise_for_status.return_value = None

    with patch("consilo.bridges.telegram.httpx.get", return_value=fake):
        telegram.run_polling(once=True, timeout=0)

    evs = list(events_dir("acme", "digital-platform").glob("*.md"))
    assert len(evs) == 1
    assert "Acme update from CFO" in evs[0].read_text()


def test_telegram_ticket_command_spawns_and_replies(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("CONSILO_DEFAULT_PROJECT", "digital-platform")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_OPERATOR_CHAT_ID", "42")

    upd = _tg_update("/ticket deck-outline Draft Q2 readout for Acme")
    get_mock = MagicMock()
    get_mock.json.return_value = {"ok": True, "result": [upd]}
    get_mock.raise_for_status.return_value = None
    sent: list[dict] = []

    def fake_post(url, json=None, timeout=None):
        sent.append({"url": url, "json": json})
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = {"ok": True}
        return m

    with patch("consilo.bridges.telegram.httpx.get", return_value=get_mock), \
         patch("consilo.bridges.telegram.httpx.post", side_effect=fake_post):
        telegram.run_polling(once=True, timeout=0)

    backlog = list(kanban_path("acme", "digital-platform", "backlog").glob("*.yaml"))
    assert len(backlog) == 1
    # The bot should have replied with "spawned ticket OC-T-001"
    bodies = " ".join(s["json"]["text"] for s in sent)
    assert "OC-T-001" in bodies


# ---------- WhatsApp / wuzapi ----------

def _wa_payload(text: str, chat: str = "12025550100@s.whatsapp.net") -> dict:
    return {
        "type": "Message",
        "event": {
            "Info": {"Chat": chat, "Sender": chat,
                     "ID": "wamid.abc123", "Timestamp": 1746288000,
                     "PushName": "Ashraf"},
            "Message": {"conversation": text},
        },
    }


def test_wa_webhook_inbound_creates_event(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("CONSILO_DEFAULT_PROJECT", "digital-platform")

    from fastapi.testclient import TestClient
    client = TestClient(bridge_server.app)
    r = client.post("/bridges/wa/webhook", json=_wa_payload("Quick note from Acme CIO"))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["client"] == "acme"
    assert "event_path" in data

    evs = list(events_dir("acme", "digital-platform").glob("*.md"))
    assert len(evs) == 1
    assert "Acme CIO" in evs[0].read_text()


def test_wa_webhook_ticket_command_from_operator(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("CONSILO_DEFAULT_PROJECT", "digital-platform")
    monkeypatch.setenv("WUZAPI_OPERATOR_JID", "12025550100@s.whatsapp.net")
    # No WUZAPI_BASE_URL/TOKEN → reply send is skipped, command still processed.
    monkeypatch.delenv("WUZAPI_BASE_URL", raising=False)
    monkeypatch.delenv("WUZAPI_TOKEN", raising=False)

    from fastapi.testclient import TestClient
    client = TestClient(bridge_server.app)
    r = client.post("/bridges/wa/webhook",
                    json=_wa_payload("/ticket deck-outline May 17 readout"))
    assert r.status_code == 200
    backlog = list(kanban_path("acme", "digital-platform", "backlog").glob("*.yaml"))
    assert len(backlog) == 1


def test_wa_webhook_secret_enforced(tmp_workspace, monkeypatch):
    monkeypatch.setenv("CONSILO_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("CONSILO_DEFAULT_PROJECT", "digital-platform")
    monkeypatch.setenv("WUZAPI_WEBHOOK_SECRET", "s3cr3t")

    from fastapi.testclient import TestClient
    client = TestClient(bridge_server.app)
    bad = client.post("/bridges/wa/webhook", json=_wa_payload("hi"))
    assert bad.status_code == 401
    good = client.post("/bridges/wa/webhook?secret=s3cr3t", json=_wa_payload("hi"))
    assert good.status_code == 200
