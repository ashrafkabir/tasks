"""Ticket-spawn rules. Conservative: only explicit `/ticket` chat commands spawn.

Operator stays in control. Anything else lands as an event for triage.
"""
from __future__ import annotations
import re
import secrets
from .schemas import Ticket
from . import kanban


_TICKET_CMD = re.compile(r"^/ticket\s+(\S+)\s+(.+)$", re.IGNORECASE | re.MULTILINE)


def _next_ticket_id(client: str, project: str) -> str:
    """OC-T-XXX — increment-by-existing on the project's board."""
    existing = kanban.list_tickets(client, project)
    nums = []
    for t in existing:
        if t.id.startswith("OC-T-"):
            tail = t.id.split("-")[-1]
            if tail.isdigit():
                nums.append(int(tail))
    nxt = (max(nums) + 1) if nums else 1
    return f"OC-T-{nxt:03d}"


def maybe_spawn_ticket(
    *, client: str, project: str, event_filename: str,
    text: str, sender: str,
) -> Ticket | None:
    if not text:
        return None
    m = _TICKET_CMD.search(text)
    if not m:
        return None
    kind, title = m.group(1).strip(), m.group(2).strip()
    ticket = Ticket(
        id=_next_ticket_id(client, project),
        client=client,
        project=project,
        title=title,
        kind=kind,
        source_event=event_filename,
        acceptance=[
            f"Spawned by chat command from {sender}.",
            "Output must follow the kind-appropriate template.",
        ],
    )
    kanban.write_ticket(ticket)
    return ticket
