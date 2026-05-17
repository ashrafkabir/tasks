"""Outbound notifier — broadcast to all configured operator channels.

Modes:
  - stub: record the call into a session-local sink; never hits the network.
           Used by tests and any time tokens are absent.
  - live: best-effort send to Telegram + wuzapi. Failures are logged in the
           returned list but never raised — the kanban transition that
           triggered the notify must not be blocked.

Triggered automatically by `kanban.transition` on entry to awaiting_approval.
"""
from __future__ import annotations
import os
from typing import Any
from .config import get_settings
from .schemas import Ticket


_SINK: list[dict[str, Any]] = []


def reset_sink() -> None:
    _SINK.clear()


def get_sink() -> list[dict[str, Any]]:
    return list(_SINK)


def _format(ticket: Ticket) -> str:
    return (
        f"Consilo — ticket awaiting approval\n"
        f"  id      : {ticket.id}\n"
        f"  client  : {ticket.client}\n"
        f"  project : {ticket.project}\n"
        f"  title   : {ticket.title}\n\n"
        f"Reply: /approve {ticket.id}"
    )


def _mode() -> str:
    return os.getenv("CONSILO_NOTIFY_MODE", "stub").lower()


def notify_awaiting_approval(ticket: Ticket) -> list[dict[str, Any]]:
    text = _format(ticket)
    results: list[dict[str, Any]] = []

    if _mode() == "stub":
        entry = {"channel": "stub", "ticket_id": ticket.id, "text": text, "ok": True}
        _SINK.append(entry)
        return [entry]

    # Telegram
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_OPERATOR_CHAT_ID")
    if tg_token and tg_chat:
        try:
            from .bridges.telegram import send_message
            send_message(tg_token, tg_chat, text)
            results.append({"channel": "telegram", "ok": True})
        except Exception as e:
            results.append({"channel": "telegram", "ok": False, "error": str(e)})

    # WhatsApp via wuzapi
    wa_url = os.getenv("WUZAPI_BASE_URL")
    wa_token = os.getenv("WUZAPI_TOKEN")
    wa_jid = os.getenv("WUZAPI_OPERATOR_JID")
    if wa_url and wa_token and wa_jid:
        try:
            from .bridges.whatsapp import send_text
            send_text(wa_url, wa_token, wa_jid, text)
            results.append({"channel": "whatsapp", "ok": True})
        except Exception as e:
            results.append({"channel": "whatsapp", "ok": False, "error": str(e)})

    if not results:
        # Live mode but nothing configured → fall back to stub sink.
        entry = {"channel": "stub", "ticket_id": ticket.id, "text": text,
                 "ok": True, "note": "no live channel configured"}
        _SINK.append(entry)
        results.append(entry)

    return results
