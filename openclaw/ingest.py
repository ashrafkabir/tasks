"""OC-022b — Inbound message ingest pipeline. Bridge-agnostic.

Each inbound message becomes:
  - a markdown event in vault/clients/<client>/projects/<project>/events/
  - a row in SQLite events
  - an embedded point in the per-client Qdrant collection
  - optionally a new ticket if the text matches a spawn rule
"""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import yaml

from .config import get_settings
from .schemas import Event
from .vault import ensure_project_skeleton, events_dir
from .bridges.routes import resolve as resolve_route
from . import sqlite_store, qdrant_store, spawn
from .embed import Embedder


@dataclass
class InboundMessage:
    source: str          # "telegram" | "whatsapp"
    chat_id: str         # platform chat identifier
    message_id: str      # platform unique message id
    sender: str          # display name / handle / jid
    text: str
    received_at: str | None = None  # ISO; default = now


def _slug(s: str, n: int = 32) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n] or "untitled"


def _event_id(msg: InboundMessage) -> str:
    raw = f"{msg.source}:{msg.chat_id}:{msg.message_id}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:10]
    return f"evt-{msg.source}-{digest}"


def ingest(msg: InboundMessage) -> dict:
    """Land an inbound message in the vault. Returns a summary dict."""
    received_at = msg.received_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    route = resolve_route(msg.source, msg.chat_id)

    # _unrouted lives outside vault/clients to avoid colliding with real client slugs.
    if route.client == "_unrouted":
        ensure_project_skeleton("_unrouted", "_unrouted")

    ensure_project_skeleton(route.client, route.project)

    event_id = _event_id(msg)
    received_dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    title = msg.text.strip().splitlines()[0][:80] if msg.text.strip() else "(empty message)"
    fname = f"{received_dt.strftime('%Y-%m-%d')}-{msg.source}-{_slug(title)}-{event_id[-6:]}.md"
    target = events_dir(route.client, route.project) / fname

    if not target.exists():
        meta = {
            "id": event_id,
            "client": route.client,
            "project": route.project,
            "title": title,
            "received_at": received_at,
            "source": msg.source,
            "sender": msg.sender,
            "chat_id": msg.chat_id,
            "message_id": msg.message_id,
        }
        body = msg.text.strip() or "(empty message)"
        target.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n\n" + body)
        sqlite_store.record_event(
            event_id, route.client, route.project, title, msg.source, str(target),
        )

        # Best-effort embedding — never block ingest on Qdrant/embed failure.
        try:
            e = Embedder()
            qdrant_store.ensure_collection(route.client, e.dim)
            vec = e.embed([body])[0]
            qdrant_store.upsert_points(
                route.client,
                [(event_id, vec, {"title": title, "kind": "event",
                                  "source": msg.source, "received_at": received_at})],
            )
        except Exception:
            pass

    spawned = spawn.maybe_spawn_ticket(
        client=route.client,
        project=route.project,
        event_filename=target.name,
        text=msg.text,
        sender=msg.sender,
    )

    return {
        "event_id": event_id,
        "event_path": str(target),
        "client": route.client,
        "project": route.project,
        "ticket": spawned.id if spawned else None,
    }
