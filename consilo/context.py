"""OC-011 — Cold-start context bundler.

Each agent run begins by reloading a curated bundle from durable memory
(vault + Qdrant + SQLite). No long-context compaction, no reuse of prior
conversational state.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .config import get_settings
from .schemas import Ticket
from .vault import (
    project_dir, client_dir, list_events, read_event_md,
)
from . import sqlite_store, qdrant_store
from .embed import Embedder


@dataclass
class ContextBundle:
    client_yaml: str = ""
    project_yaml: str = ""
    ticket: dict = field(default_factory=dict)
    source_event: dict | None = None
    recent_events: list[dict] = field(default_factory=list)
    semantic_hits: list[dict] = field(default_factory=list)

    def render(self) -> str:
        """Render the bundle as a compact prompt-ready text block."""
        parts: list[str] = []
        parts.append("=== CLIENT ===\n" + self.client_yaml.strip())
        parts.append("=== PROJECT ===\n" + self.project_yaml.strip())
        parts.append("=== TICKET ===\n" + _yaml_dump(self.ticket).strip())
        if self.source_event:
            parts.append("=== SOURCE EVENT ===\n" + self.source_event["body"].strip())
        if self.recent_events:
            lines = [f"- {e['received_at']} {e['title']}" for e in self.recent_events[:10]]
            parts.append("=== RECENT EVENTS ===\n" + "\n".join(lines))
        if self.semantic_hits:
            lines = [
                f"- score={h['score']:.3f} {h['payload'].get('title','')[:80]}"
                for h in self.semantic_hits[:8]
            ]
            parts.append("=== SEMANTIC MEMORY ===\n" + "\n".join(lines))
        return "\n\n".join(parts)


def _yaml_dump(d: dict) -> str:
    import yaml
    return yaml.safe_dump(d, sort_keys=False)


def build(ticket: Ticket) -> ContextBundle:
    s = get_settings()
    cd = client_dir(ticket.client)
    pd = project_dir(ticket.client, ticket.project)

    bundle = ContextBundle()
    cyaml = cd / "client.yaml"
    pyaml = pd / "project.yaml"
    if cyaml.exists():
        bundle.client_yaml = cyaml.read_text()
    if pyaml.exists():
        bundle.project_yaml = pyaml.read_text()
    bundle.ticket = ticket.model_dump()

    if ticket.source_event:
        ev_path = pd / "events" / ticket.source_event
        if ev_path.exists():
            ev = read_event_md(ev_path)
            bundle.source_event = {
                "id": ev.id,
                "title": ev.title,
                "received_at": ev.received_at,
                "body": ev.body,
            }

    bundle.recent_events = sqlite_store.recent_events(ticket.client, ticket.project, limit=20)

    # Best-effort semantic hits — silently empty if Qdrant/embed unavailable.
    try:
        embedder = Embedder()
        qvec = embedder.embed([ticket.title])[0]
        bundle.semantic_hits = qdrant_store.search(ticket.client, qvec, limit=8)
    except Exception:
        bundle.semantic_hits = []

    return bundle
