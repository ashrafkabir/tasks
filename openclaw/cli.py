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
from .agents import implementer, reviewer, memory_curator, briefer

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


@main.command("curate-memory")
@click.option("--client", required=True)
@click.option("--project", default=None,
              help="Optional: only curate events from this project.")
@click.option("--since", default=None,
              help="ISO timestamp; only consider events received at or after.")
def curate_memory_cmd(client: str, project: str | None, since: str | None) -> None:
    """OC-021 — extract durable facts from uncurated events into memory.md + Qdrant."""
    console.rule(f"[bold cyan]openclaw curate-memory client={client}")
    result = memory_curator.run(client, project=project, since=since)
    if result.get("skipped"):
        console.print(f"[yellow]skipped:[/] {result.get('reason')}")
        return
    console.print(f"[green]events processed :[/] {result['events_processed']}")
    console.print(f"[green]facts extracted  :[/] {result['fact_count']}")
    console.print(f"[green]qdrant upserts   :[/] {result['qdrant_upserts']}")
    console.print(f"[green]memory file      :[/] {result['memory_path']}")
    console.print(f"[green]audit            :[/] {result['audit_path']}")


@main.command("brief")
@click.option("--client", required=True)
@click.option("--project", required=True)
@click.option("--event-id", default=None,
              help="Brief about a specific event id; defaults to latest event.")
def brief_cmd(client: str, project: str, event_id: str | None) -> None:
    """OC-022 — synthesize a CxO briefing markdown into briefs/."""
    console.rule(f"[bold cyan]openclaw brief {client}/{project}")
    try:
        result = briefer.run(client, project, event_id=event_id)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(2)
    console.print(f"[green]brief :[/] {result['brief_path']}")
    console.print(f"[green]audit :[/] {result['audit_path']}")
    console.print(f"[green]event :[/] {result['event_id']}")
    console.print(f"[green]memory hits:[/] {result['memory_hit_count']}")


@main.command("search-monitor")
@click.option("--client", default=None)
@click.option("--project", default=None)
@click.option("--all", "all_", is_flag=True,
              help="Walk every client/project that has queries.yaml.")
def search_monitor_cmd(client: str | None, project: str | None, all_: bool) -> None:
    """OC-027 — run SearXNG queries for a project (or all) and ingest new hits."""
    from .monitor import searxng
    if all_:
        results = searxng.run_for_all()
    else:
        if not client or not project:
            console.print("[red]--client and --project required (or use --all)[/]")
            sys.exit(2)
        results = [searxng.run_for_project(client, project)]
    for r in results:
        if r.get("skipped"):
            console.print(f"[yellow]{r['client']}/{r['project']}: skipped — {r.get('reason')}[/]")
            continue
        console.print(f"[green]{r['client']}/{r['project']}:[/] "
                      f"queries={r['queries']} ingested={r['ingested']} "
                      f"deduped={r['deduped']} errors={len(r['errors'])}")
        for e in r["errors"]:
            console.print(f"  [red]err:[/] {e}")


@main.command("replay")
@click.option("--run-id", required=True)
@click.option("--client", default=None)
@click.option("--project", default=None)
@click.option("--ticket", "ticket_id", default=None)
def replay_cmd(run_id: str, client: str | None, project: str | None,
               ticket_id: str | None) -> None:
    """OC-030 — re-run the agent that produced a captured audit run."""
    from . import replay as replay_mod
    try:
        result = replay_mod.replay(run_id=run_id, client=client,
                                   project=project, ticket_id=ticket_id)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/]")
        sys.exit(2)
    console.print(f"[green]agent       :[/] {result['agent']}")
    console.print(f"[green]replayed of :[/] {result['replayed_from']}")
    console.print(f"[green]new audit   :[/] {result['new_audit']}")


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
