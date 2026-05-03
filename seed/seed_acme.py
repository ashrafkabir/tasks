"""OC-006 — Seed one client, one project, one event, one ticket.

Idempotent: re-running only writes missing files. Embeds the seed event into
the per-client Qdrant collection so semantic search has at least one point.
"""
from __future__ import annotations
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from openclaw.config import get_settings
from openclaw.schemas import Client, Project, Ticket, Event
from openclaw.vault import (
    client_dir, project_dir, ensure_project_skeleton,
    events_dir, kanban_path,
)
from openclaw import sqlite_store, qdrant_store, kanban
from openclaw.embed import Embedder
import yaml


CLIENT_SLUG = "acme"
PROJECT_SLUG = "digital-platform"
TICKET_ID = "OC-T-001"
EVENT_ID = "evt-2026-05-03-quarterly-letter"


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def main() -> None:
    s = get_settings()
    s.vault_dir.mkdir(parents=True, exist_ok=True)

    client = Client(
        slug=CLIENT_SLUG,
        display_name="Acme Manufacturing Co.",
        industry="Industrial Manufacturing",
        primary_contact="J. Doe (CIO)",
        notes="Mid-market manufacturer evaluating digital platform consolidation.",
    )
    project = Project(
        slug=PROJECT_SLUG,
        client=CLIENT_SLUG,
        display_name="Digital Platform Consolidation",
        objective=(
            "Consolidate fragmented ERP+MES tooling into a single Visionet-led "
            "digital platform; brief the Acme board quarterly on progress and risk."
        ),
        status="active",
    )

    cd = client_dir(CLIENT_SLUG)
    pd = project_dir(CLIENT_SLUG, PROJECT_SLUG)
    cd.mkdir(parents=True, exist_ok=True)
    ensure_project_skeleton(CLIENT_SLUG, PROJECT_SLUG)

    _write_if_missing(cd / "client.yaml",
                      yaml.safe_dump(client.model_dump(), sort_keys=False))
    _write_if_missing(pd / "project.yaml",
                      yaml.safe_dump(project.model_dump(), sort_keys=False))

    # Synthetic event — markdown w/ YAML frontmatter
    ev_filename = "2026-05-03-quarterly-letter.md"
    ev_path = events_dir(CLIENT_SLUG, PROJECT_SLUG) / ev_filename
    ev_body = textwrap.dedent("""\
        Acme Manufacturing's CFO published the Q1-2026 shareholder letter today.
        Highlights:
        - Revenue +6% YoY but operating margin compressed 180bps due to ERP downtime.
        - Board committed to a $12M technology modernization budget over 18 months.
        - Specific mention of evaluating "external transformation partners" by end of Q2.
        - The CIO is presenting a platform options review at the next board meeting (May 17).

        Visionet implication: this is the strongest signaling window we have had to
        propose the consolidated platform play; the board readout in two weeks is the
        natural insertion point for our recommended path.
        """)
    ev_meta = {
        "id": EVENT_ID,
        "client": CLIENT_SLUG,
        "project": PROJECT_SLUG,
        "title": "Acme Q1-2026 shareholder letter signals modernization budget",
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "synthetic",
    }
    ev_text = "---\n" + yaml.safe_dump(ev_meta, sort_keys=False) + "---\n\n" + ev_body
    _write_if_missing(ev_path, ev_text)

    sqlite_store.record_event(
        EVENT_ID, CLIENT_SLUG, PROJECT_SLUG, ev_meta["title"],
        "synthetic", str(ev_path),
    )

    # One ticket → backlog
    ticket = Ticket(
        id=TICKET_ID,
        client=CLIENT_SLUG,
        project=PROJECT_SLUG,
        title="Draft Acme board readout deck for May 17",
        kind="deck-outline",
        source_event=ev_filename,
        acceptance=[
            "Markdown deck outline with one H2 per slide.",
            "Each slide has a bold Speaker note line.",
            "Recommends a single Visionet path of action.",
            "Cites the Q1-2026 letter as the triggering event.",
        ],
    )
    # Avoid duplicate write if already on board
    existing = kanban_path(CLIENT_SLUG, PROJECT_SLUG, "backlog") / f"{TICKET_ID}.yaml"
    if not existing.exists() and not any(
        (kanban_path(CLIENT_SLUG, PROJECT_SLUG, st) / f"{TICKET_ID}.yaml").exists()
        for st in ["in_progress", "awaiting_approval", "approved", "done"]
    ):
        kanban.write_ticket(ticket)

    # Embed the event body into the client collection
    embedder = Embedder()
    qdrant_store.ensure_collection(CLIENT_SLUG, embedder.dim)
    vec = embedder.embed([ev_body])[0]
    qdrant_store.upsert_points(
        CLIENT_SLUG,
        [(EVENT_ID, vec, {"title": ev_meta["title"], "kind": "event",
                           "received_at": ev_meta["received_at"]})],
    )

    print(f"seeded: {CLIENT_SLUG}/{PROJECT_SLUG}, ticket {TICKET_ID}, event {EVENT_ID}")


if __name__ == "__main__":
    main()
