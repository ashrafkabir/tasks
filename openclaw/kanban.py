"""OC-010 — Filesystem-backed Kanban + ticket lifecycle."""
from __future__ import annotations
import shutil
from datetime import datetime, timezone
from pathlib import Path
import yaml
from .schemas import Ticket, TicketState
from .vault import kanban_path, ensure_project_skeleton
from . import sqlite_store


VALID_TRANSITIONS: dict[TicketState, set[TicketState]] = {
    "backlog":            {"in_progress"},
    "in_progress":        {"awaiting_approval", "backlog"},
    "awaiting_approval":  {"approved", "in_progress"},
    "approved":           {"done"},
    "done":               set(),
}


def _ticket_filename(ticket_id: str) -> str:
    return f"{ticket_id}.yaml"


def _find(client: str, project: str, ticket_id: str) -> tuple[Path, TicketState] | None:
    for state in ["backlog", "in_progress", "awaiting_approval", "approved", "done"]:
        p = kanban_path(client, project, state) / _ticket_filename(ticket_id)
        if p.exists():
            return p, state  # type: ignore[return-value]
    return None


def write_ticket(t: Ticket) -> Path:
    ensure_project_skeleton(t.client, t.project)
    target = kanban_path(t.client, t.project, t.state) / _ticket_filename(t.id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(t.model_dump(), sort_keys=False))
    sqlite_store.upsert_ticket(t.model_dump())
    return target


def load_ticket(client: str, project: str, ticket_id: str) -> Ticket:
    found = _find(client, project, ticket_id)
    if not found:
        raise FileNotFoundError(f"ticket not found: {ticket_id}")
    data = yaml.safe_load(found[0].read_text())
    return Ticket(**data)


def transition(client: str, project: str, ticket_id: str,
               target_state: TicketState) -> Ticket:
    found = _find(client, project, ticket_id)
    if not found:
        raise FileNotFoundError(f"ticket not found: {ticket_id}")
    src_path, src_state = found
    if target_state not in VALID_TRANSITIONS[src_state]:
        raise ValueError(
            f"illegal transition {src_state} -> {target_state} for {ticket_id}"
        )
    t = Ticket(**yaml.safe_load(src_path.read_text()))
    t.state = target_state
    t.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    dst_path = kanban_path(client, project, target_state) / _ticket_filename(ticket_id)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(yaml.safe_dump(t.model_dump(), sort_keys=False))
    src_path.unlink()
    sqlite_store.upsert_ticket(t.model_dump())
    return t


def list_tickets(client: str, project: str, state: TicketState | None = None) -> list[Ticket]:
    states = [state] if state else list(VALID_TRANSITIONS.keys())
    out: list[Ticket] = []
    for st in states:
        d = kanban_path(client, project, st)
        if not d.exists():
            continue
        for p in sorted(d.glob("*.yaml")):
            out.append(Ticket(**yaml.safe_load(p.read_text())))
    return out
