"""OC-015 + OC-017 — `openclaw` CLI: approval gate + run-slice driver."""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from .config import get_settings
from . import kanban, audit, sqlite_store, git_sync
from .vault import project_dir, audit_dir
from .schemas import Ticket
from .agents import implementer, reviewer

console = Console()


@click.group()
def main() -> None:
    """OpenClaw — local-first agentic OS."""


@main.command("run-slice")
@click.option("--client", default="acme")
@click.option("--project", default="digital-platform")
@click.option("--ticket", "ticket_id", default="OC-T-001")
def run_slice(client: str, project: str, ticket_id: str) -> None:
    """Drive the proving slice: implementer → reviewer → awaiting_approval."""
    console.rule(f"[bold cyan]openclaw run-slice {client}/{project}/{ticket_id}")

    t = kanban.load_ticket(client, project, ticket_id)
    if t.state == "backlog":
        t = kanban.transition(client, project, ticket_id, "in_progress")
        console.print(f"[green]→ in_progress[/]")

    console.print("[bold]Implementer running…[/]")
    impl = implementer.run(t)
    console.print(f"  draft: {impl['draft_path']}")
    console.print(f"  audit: {impl['audit_path']}")

    console.print("[bold]Reviewer running…[/]")
    rev = reviewer.run(t)
    console.print(f"  verdict: [yellow]{rev['verdict']}[/]")
    console.print(f"  suggestions: {len(rev['suggestions'])}")
    console.print(f"  audit: {rev['audit_path']}")

    t = kanban.transition(client, project, ticket_id, "awaiting_approval")
    console.print(f"[green]→ awaiting_approval[/]")
    console.print()
    console.print(f"[bold]Approve with:[/] [cyan]openclaw approve {ticket_id} --client {client} --project {project} --apply[/]")


@main.command("approve")
@click.argument("ticket_id")
@click.option("--client", default="acme")
@click.option("--project", default="digital-platform")
@click.option("--apply/--no-apply", default=False,
              help="Apply reviewer suggestions before approving.")
@click.option("--notes", default=None)
def approve_cmd(ticket_id: str, client: str, project: str, apply: bool,
                notes: str | None) -> None:
    """OC-015 — Human approval gate. Promotes draft to artifact and commits."""
    t = kanban.load_ticket(client, project, ticket_id)
    if t.state != "awaiting_approval":
        console.print(f"[red]ticket {ticket_id} is in state {t.state!r}, cannot approve[/]")
        sys.exit(2)

    pd = project_dir(client, project)
    draft = pd / "kanban" / "in_progress" / ticket_id / "draft.md"
    review = pd / "kanban" / "in_progress" / ticket_id / "review.json"
    if not draft.exists():
        console.print(f"[red]missing draft: {draft}[/]")
        sys.exit(2)

    body = draft.read_text()
    if apply and review.exists():
        suggestions = json.loads(review.read_text()).get("suggestions", [])
        if suggestions:
            body = body + "\n\n---\n\n## Reviewer suggestions applied\n"
            for s in suggestions:
                slide = s.get("slide")
                slide_str = f"slide {slide}" if slide else "general"
                body += f"- ({slide_str}, {s.get('severity','?')}) {s.get('fix','')}\n"
            draft.write_text(body)

    artifact_name = f"{ticket_id.lower()}-deck-outline.md"
    artifact_path = pd / "artifacts" / "decks" / artifact_name
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(draft, artifact_path)

    t = kanban.transition(client, project, ticket_id, "approved")
    t = kanban.transition(client, project, ticket_id, "done")

    run_id = audit.new_run_id()
    audit_path = audit.write_run(
        client, project, ticket_id, run_id,
        {
            "agent": "approver",
            "decision": "approved",
            "applied_suggestions": apply,
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

    console.print(f"[green]artifact:[/] {artifact_path}")
    console.print(f"[green]commit :[/] {sha or '(no diff)'}")
    console.print(f"[green]ticket :[/] done")


@main.command("status")
@click.option("--client", default="acme")
@click.option("--project", default="digital-platform")
def status_cmd(client: str, project: str) -> None:
    """Print the kanban board for a project."""
    tbl = Table(title=f"{client}/{project} board")
    tbl.add_column("State")
    tbl.add_column("Ticket")
    tbl.add_column("Title")
    for t in kanban.list_tickets(client, project):
        tbl.add_row(t.state, t.id, t.title)
    console.print(tbl)


if __name__ == "__main__":
    main()
