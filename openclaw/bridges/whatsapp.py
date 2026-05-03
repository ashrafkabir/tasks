"""OC-026 — WhatsApp bridge via wuzapi (OSS REST wrapper around whatsmeow).

Inbound:  wuzapi POSTs JSON webhooks to our FastAPI server (see bridges/server.py).
Outbound: REST calls to wuzapi `/chat/send/text`.

wuzapi auth: each user has a token; pass via `Token` header. Configure with
WUZAPI_BASE_URL + WUZAPI_TOKEN. Operator JID for outbound notifications:
WUZAPI_OPERATOR_JID (e.g. `12025550100@s.whatsapp.net`).
"""
from __future__ import annotations
import os
import re
from datetime import datetime, timezone
from typing import Any
import httpx
from rich.console import Console

from ..ingest import ingest, InboundMessage

console = Console()


def send_text(base_url: str, token: str, jid: str, text: str) -> dict:
    """Send a text message to `jid` via wuzapi."""
    url = base_url.rstrip("/") + "/chat/send/text"
    r = httpx.post(
        url,
        headers={"Token": token, "Content-Type": "application/json"},
        json={"Phone": jid, "Body": text},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _extract_text(payload: dict) -> str:
    """Pull the user-visible text from a wuzapi webhook payload, tolerantly."""
    ev = payload.get("event") or {}
    msg = ev.get("Message") or {}
    for k in ("conversation", "extendedTextMessage", "text", "Text"):
        v = msg.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, dict):
            t = v.get("text") or v.get("Text")
            if isinstance(t, str) and t.strip():
                return t
    # Fallback: top-level "text" / "body"
    for k in ("text", "body", "Body"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _extract_chat(payload: dict) -> str:
    ev = payload.get("event") or {}
    info = ev.get("Info") or {}
    return str(info.get("Chat") or info.get("RemoteJid") or payload.get("chat_id") or "")


def _extract_sender(payload: dict) -> str:
    ev = payload.get("event") or {}
    info = ev.get("Info") or {}
    return str(info.get("Sender") or info.get("PushName") or payload.get("sender") or "")


def _extract_message_id(payload: dict) -> str:
    ev = payload.get("event") or {}
    info = ev.get("Info") or {}
    return str(info.get("ID") or payload.get("message_id") or "")


def _extract_received_at(payload: dict) -> str:
    ev = payload.get("event") or {}
    info = ev.get("Info") or {}
    ts = info.get("Timestamp")
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    if isinstance(ts, str) and ts:
        return ts
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_operator(jid: str) -> bool:
    op = os.getenv("WUZAPI_OPERATOR_JID")
    return bool(op) and jid.split(":")[0].split("@")[0] == op.split(":")[0].split("@")[0]


def _handle_command(text: str) -> str | None:
    """Same vocabulary as the Telegram bot."""
    parts = text.strip().split()
    if not parts:
        return None
    cmd = parts[0].lower()
    if cmd == "/help":
        return ("OpenClaw WA bot. Commands:\n"
                "  /ticket <kind> <title>\n"
                "  /run <ticket-id>\n"
                "  /approve <ticket-id>\n"
                "  /status")
    if cmd == "/run" and len(parts) >= 2:
        from ..agents import implementer, reviewer
        from .. import kanban
        ticket_id = parts[1]
        client = os.getenv("OPENCLAW_DEFAULT_CLIENT", "")
        project = os.getenv("OPENCLAW_DEFAULT_PROJECT", "")
        try:
            t = kanban.load_ticket(client, project, ticket_id)
            if t.state == "backlog":
                t = kanban.transition(client, project, ticket_id, "in_progress")
            implementer.run(t)
            rev = reviewer.run(t)
            kanban.transition(client, project, ticket_id, "awaiting_approval")
            return f"ran slice for {ticket_id}: verdict={rev['verdict']}, suggestions={len(rev['suggestions'])}"
        except Exception as e:
            return f"run failed: {e}"
    if cmd == "/approve" and len(parts) >= 2:
        from click.testing import CliRunner
        from ..cli import main as cli
        client = os.getenv("OPENCLAW_DEFAULT_CLIENT", "")
        project = os.getenv("OPENCLAW_DEFAULT_PROJECT", "")
        runner = CliRunner()
        res = runner.invoke(cli, ["approve", parts[1], "--client", client,
                                   "--project", project, "--apply"])
        return f"approve exit={res.exit_code}"
    if cmd == "/status":
        from .. import kanban
        client = os.getenv("OPENCLAW_DEFAULT_CLIENT", "")
        project = os.getenv("OPENCLAW_DEFAULT_PROJECT", "")
        try:
            tickets = kanban.list_tickets(client, project)
            return "\n".join(f"{t.state}: {t.id} {t.title}" for t in tickets) or "(empty board)"
        except Exception as e:
            return f"status failed: {e}"
    return None


def handle_webhook(payload: dict[str, Any]) -> dict:
    """Process a wuzapi webhook payload. Returns ingest summary + any reply sent."""
    chat = _extract_chat(payload)
    if not chat:
        return {"ignored": True, "reason": "no chat id"}
    text = _extract_text(payload)
    if not text:
        return {"ignored": True, "reason": "no text"}

    summary = ingest(InboundMessage(
        source="whatsapp",
        chat_id=chat,
        message_id=_extract_message_id(payload),
        sender=_extract_sender(payload),
        text=text,
        received_at=_extract_received_at(payload),
    ))

    reply: str | None = None
    if text.startswith("/") and _is_operator(chat):
        reply = _handle_command(text)
        if not reply and summary.get("ticket"):
            reply = f"spawned ticket {summary['ticket']}"
    elif summary.get("ticket"):
        reply = f"spawned ticket {summary['ticket']}"

    if reply:
        base = os.getenv("WUZAPI_BASE_URL")
        tok = os.getenv("WUZAPI_TOKEN")
        if base and tok:
            try:
                send_text(base, tok, chat, reply)
            except Exception as e:
                console.print(f"[red]wuzapi reply failed: {e}[/]")
                reply = f"(send failed: {e})"

    return {**summary, "reply": reply}
