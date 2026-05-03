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
from . import kanban, audit, sqlite_store, git_sync, service
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
    result = service.run_slice(client, project, ticket_id)
    console.print(f"[green]→ in_progress[/]")
    console.print("[bold]Implementer running…[/]")
    console.print(f"  draft: {result['implementer']['draft_path']}")
    console.print(f"  audit: {result['implementer']['audit_path']}")
    console.print("[bold]Reviewer running…[/]")
    console.print(f"  verdict: [yellow]{result['reviewer']['verdict']}[/]")
    console.print(f"  suggestions: {len(result['reviewer']['suggestions'])}")
    console.print(f"  audit: {result['reviewer']['audit_path']}")
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
    try:
        result = service.approve(client, project, ticket_id,
                                 apply_suggestions=apply, notes=notes)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/]")
        sys.exit(2)
    console.print(f"[green]artifact:[/] {result['artifact_path']}")
    console.print(f"[green]commit :[/] {result['commit_sha'] or '(no diff)'}")
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
