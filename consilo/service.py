"""Shared service layer — run_slice + approve.

Used by:
  - consilo.cli (terminal driver)
  - consilo.bridges.{telegram,whatsapp} (chat command handlers)
  - consilo.dashboard.server (HTMX dashboard)

Keeping this in one place means a slash command, a CLI invocation, and a
dashboard button all hit the same code path and produce the same audit trail.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from .schemas import Ticket
from . import kanban, audit, sqlite_store, git_sync
from .vault import project_dir
from .agents import implementer, reviewer


def run_slice(client: str, project: str, ticket_id: str) -> dict:
    """Drive backlog → in_progress → implementer → reviewer → awaiting_approval."""
    t = kanban.load_ticket(client, project, ticket_id)
    if t.state == "backlog":
        t = kanban.transition(client, project, ticket_id, "in_progress")
    impl = implementer.run(t)
    rev = reviewer.run(t)
    t = kanban.transition(client, project, ticket_id, "awaiting_approval")
    return {
        "ticket_id": ticket_id,
        "state": t.state,
        "implementer": impl,
        "reviewer": rev,
    }


def approve(client: str, project: str, ticket_id: str, *,
            apply_suggestions: bool = True, notes: str | None = None) -> dict:
    """Human-gate transition: awaiting_approval → approved → done + git commit."""
    t = kanban.load_ticket(client, project, ticket_id)
    if t.state != "awaiting_approval":
        raise ValueError(f"ticket {ticket_id} is in state {t.state!r}, cannot approve")

    pd = project_dir(client, project)
    draft = pd / "kanban" / "in_progress" / ticket_id / "draft.md"
    review = pd / "kanban" / "in_progress" / ticket_id / "review.json"
    if not draft.exists():
        raise FileNotFoundError(f"missing draft: {draft}")

    body = draft.read_text()
    if apply_suggestions and review.exists():
        suggestions = json.loads(review.read_text()).get("suggestions", [])
        if suggestions:
            body += "\n\n---\n\n## Reviewer suggestions applied\n"
            for s in suggestions:
                slide = s.get("slide")
                slide_str = f"slide {slide}" if slide else "general"
                body += f"- ({slide_str}, {s.get('severity','?')}) {s.get('fix','')}\n"
            draft.write_text(body)

    artifact_name = f"{ticket_id.lower()}-deck-outline.md"
    artifact_path = pd / "artifacts" / "decks" / artifact_name
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(draft, artifact_path)

    kanban.transition(client, project, ticket_id, "approved")
    kanban.transition(client, project, ticket_id, "done")

    run_id = audit.new_run_id()
    audit_path = audit.write_run(
        client, project, ticket_id, run_id,
        {
            "agent": "approver",
            "decision": "approved",
            "applied_suggestions": apply_suggestions,
            "artifact_path": str(artifact_path),
            "notes": notes,
        },
    )
    sqlite_store.record_approval(ticket_id, "approved", notes)
    sqlite_store.record_run(run_id, ticket_id, "approver", "ok", str(audit_path))

    audit_files = audit.list_runs(client, project, ticket_id)
    sha = git_sync.commit_artifact(
        client, project, ticket_id, artifact_path, audit_files,
        message=f"approve: {ticket_id} → {artifact_name}",
    )
    return {
        "ticket_id": ticket_id,
        "artifact_path": str(artifact_path),
        "commit_sha": sha,
    }
