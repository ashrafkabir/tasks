"""OC-023 — Telegram bridge: long-poll inbound, REST outbound.

No third-party Telegram SDK; raw httpx against the Bot API.

Inbound: each text message → ingest pipeline. If sender is the configured
operator, slash commands /ticket, /run, /approve are dispatched.

Outbound: `send_message(token, chat_id, text)` — used by openclaw.notify.
"""
from __future__ import annotations
import os
import time
from datetime import datetime, timezone
import httpx
from rich.console import Console

from ..ingest import ingest, InboundMessage

console = Console()
TG_API = "https://api.telegram.org"


def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"{TG_API}/bot{token}/sendMessage"
    r = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    r.raise_for_status()
    return r.json()


def _is_operator(chat_id: str, sender: str) -> bool:
    op = os.getenv("TELEGRAM_OPERATOR_CHAT_ID")
    return bool(op) and str(chat_id) == str(op)


def _handle_command(token: str, chat_id: str, text: str) -> str | None:
    """Returns reply text if the message is a recognized slash command."""
    parts = text.strip().split()
    if not parts:
        return None
    cmd = parts[0].lower()
    if cmd == "/help" or cmd == "/start":
        return ("OpenClaw bot. Commands:\n"
                "  /ticket <kind> <title>\n"
                "  /run <ticket-id>\n"
                "  /approve <ticket-id>\n"
                "  /status")
    if cmd == "/run" and len(parts) >= 2:
        from .. import service
        ticket_id = parts[1]
        client = os.getenv("OPENCLAW_DEFAULT_CLIENT", "")
        project = os.getenv("OPENCLAW_DEFAULT_PROJECT", "")
        try:
            r = service.run_slice(client, project, ticket_id)
            return (f"ran slice for {ticket_id}: "
                    f"verdict={r['reviewer']['verdict']}, "
                    f"suggestions={len(r['reviewer']['suggestions'])}")
        except Exception as e:
            return f"run failed: {e}"
    if cmd == "/approve" and len(parts) >= 2:
        from .. import service
        ticket_id = parts[1]
        client = os.getenv("OPENCLAW_DEFAULT_CLIENT", "")
        project = os.getenv("OPENCLAW_DEFAULT_PROJECT", "")
        try:
            r = service.approve(client, project, ticket_id, apply_suggestions=True)
            return f"approved {ticket_id}: commit {r['commit_sha'][:8] or '(none)'}"
        except Exception as e:
            return f"approve failed: {e}"
    if cmd == "/status":
        from .. import kanban
        client = os.getenv("OPENCLAW_DEFAULT_CLIENT", "")
        project = os.getenv("OPENCLAW_DEFAULT_PROJECT", "")
        try:
            tickets = kanban.list_tickets(client, project)
            return "\n".join(f"{t.state:18s} {t.id} {t.title}" for t in tickets) or "(empty board)"
        except Exception as e:
            return f"status failed: {e}"
    return None


def _process_update(token: str, upd: dict) -> None:
    msg = upd.get("message")
    if not msg or "text" not in msg:
        return
    chat_id = str(msg["chat"]["id"])
    sender = msg["from"].get("username") or msg["from"].get("first_name", "")
    text = msg["text"]
    received_at = datetime.fromtimestamp(msg["date"], tz=timezone.utc).isoformat(timespec="seconds")

    # Ingest first (every message is an event).
    summary = ingest(InboundMessage(
        source="telegram",
        chat_id=chat_id,
        message_id=str(msg["message_id"]),
        sender=sender,
        text=text,
        received_at=received_at,
    ))

    # Slash command — only honored from the configured operator chat.
    reply: str | None = None
    if text.startswith("/") and _is_operator(chat_id, sender):
        reply = _handle_command(token, chat_id, text)
        if not reply and summary.get("ticket"):
            reply = f"spawned ticket {summary['ticket']}"
    elif summary.get("ticket"):
        reply = f"spawned ticket {summary['ticket']}"

    if reply:
        try:
            send_message(token, chat_id, reply)
        except Exception as e:
            console.print(f"[red]reply failed: {e}[/]")


def run_polling(once: bool = False, timeout: int = 25) -> None:
    """Long-poll loop. `once=True` for tests / single-iteration runs."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    offset = 0
    while True:
        try:
            r = httpx.get(
                f"{TG_API}/bot{token}/getUpdates",
                params={"offset": offset, "timeout": timeout},
                timeout=timeout + 5,
            )
            r.raise_for_status()
            data = r.json()
            for upd in data.get("result", []):
                offset = max(offset, upd["update_id"] + 1)
                _process_update(token, upd)
        except Exception as e:
            console.print(f"[red]telegram poll error: {e}[/]")
            if once:
                return
            time.sleep(5)
        if once:
            return


if __name__ == "__main__":
    console.rule("[bold cyan]openclaw telegram bridge")
    run_polling()
