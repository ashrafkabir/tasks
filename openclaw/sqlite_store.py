"""OC-007 — SQLite event log + audit index. Schema applied on first connect."""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from .config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    client      TEXT NOT NULL,
    project     TEXT NOT NULL,
    title       TEXT NOT NULL,
    received_at TEXT NOT NULL,
    source      TEXT NOT NULL,
    vault_path  TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_cp ON events(client, project, received_at DESC);

CREATE TABLE IF NOT EXISTS tickets (
    id          TEXT PRIMARY KEY,
    client      TEXT NOT NULL,
    project     TEXT NOT NULL,
    title       TEXT NOT NULL,
    state       TEXT NOT NULL,
    kind        TEXT NOT NULL,
    source_event TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_cp ON tickets(client, project, state);

CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    ticket_id   TEXT NOT NULL,
    agent       TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,
    audit_path  TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_ticket ON runs(ticket_id, started_at DESC);

CREATE TABLE IF NOT EXISTS approvals (
    ticket_id   TEXT PRIMARY KEY,
    decided_at  TEXT NOT NULL,
    decision    TEXT NOT NULL,
    notes       TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    s = get_settings()
    s.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(s.sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_event(event_id: str, client: str, project: str, title: str,
                 source: str, vault_path: str | None) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, client, project, title, _now(), source, vault_path),
        )


def upsert_ticket(t: dict) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO tickets(id,client,project,title,state,kind,source_event,created_at,updated_at)
               VALUES(:id,:client,:project,:title,:state,:kind,:source_event,:created_at,:updated_at)
               ON CONFLICT(id) DO UPDATE SET
                 state=excluded.state,
                 updated_at=excluded.updated_at""",
            t,
        )


def record_run(run_id: str, ticket_id: str, agent: str, status: str,
               audit_path: str | None) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, ticket_id, agent, _now(), _now(), status, audit_path),
        )


def record_approval(ticket_id: str, decision: str, notes: str | None = None) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO approvals VALUES (?, ?, ?, ?)",
            (ticket_id, _now(), decision, notes),
        )


def recent_events(client: str, project: str, limit: int = 20) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE client=? AND project=? "
            "ORDER BY received_at DESC LIMIT ?",
            (client, project, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def recent_runs(ticket_id: str, limit: int = 20) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM runs WHERE ticket_id=? ORDER BY started_at DESC LIMIT ?",
            (ticket_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
