"""OC-015 + OC-017 — `consilo` CLI: approval gate + run-slice driver."""
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
from . import task_lifecycle, worker as worker_mod

console = Console()


@click.group()
def main() -> None:
    """Consilo — local-first agentic OS."""


@main.command("run-slice")
@click.option("--client", default="acme")
@click.option("--project", default="digital-platform")
@click.option("--ticket", "ticket_id", default="OC-T-001")
def run_slice(client: str, project: str, ticket_id: str) -> None:
    """Drive the proving slice: implementer → reviewer → awaiting_approval."""
    console.rule(f"[bold cyan]consilo run-slice {client}/{project}/{ticket_id}")
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
    console.print(f"[bold]Approve with:[/] [cyan]consilo approve {ticket_id} --client {client} --project {project} --apply[/]")


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
    console.rule(f"[bold cyan]consilo curate-memory client={client}")
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
    console.rule(f"[bold cyan]consilo brief {client}/{project}")
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


@main.command("start-task")
@click.option("--client", required=True)
@click.option("--project", required=True)
@click.option("--display-name", default=None)
@click.option("--objective", default=None)
def start_task_cmd(client: str, project: str,
                   display_name: str | None, objective: str | None) -> None:
    """Create a new project folder + prd_answers.yaml skeleton."""
    console.rule(f"[bold cyan]consilo start-task {client}/{project}")
    r = task_lifecycle.start_task(client, project,
                                   display_name=display_name, objective=objective)
    console.print(f"[green]project dir :[/] {r['project_dir']}")
    console.print(f"[green]answers     :[/] {r['answers_path']}")
    console.print()
    console.print(r["next"])


@main.command("compile-prd")
@click.option("--client", required=True)
@click.option("--project", required=True)
def compile_prd_cmd(client: str, project: str) -> None:
    """Compile prd_answers.yaml into prd.md."""
    console.rule(f"[bold cyan]consilo compile-prd {client}/{project}")
    try:
        r = task_lifecycle.compile_prd(client, project)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(2)
    console.print(f"[green]prd     :[/] {r['prd_path']}")
    console.print(f"[green]tickets :[/] {r['ticket_count_planned']} planned")
    console.print()
    console.print(f"Review the prd, then: [cyan]consilo approve-prd "
                  f"--client {client} --project {project}[/]")


@main.command("approve-prd")
@click.option("--client", required=True)
@click.option("--project", required=True)
@click.option("--autoloop/--no-autoloop", default=False,
              help="Run the autonomous loop immediately after approval.")
@click.option("--max-iter", default=10, type=int)
def approve_prd_cmd(client: str, project: str, autoloop: bool, max_iter: int) -> None:
    """Approve the PRD, spawn backlog tickets, optionally run the autoloop."""
    console.rule(f"[bold cyan]consilo approve-prd {client}/{project}")
    try:
        r = task_lifecycle.approve_prd(client, project,
                                       run_autoloop=autoloop, max_iter=max_iter)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/]")
        sys.exit(2)
    console.print(f"[green]approved :[/] {r['approved_path']}")
    console.print(f"[green]tickets  :[/] {r['ticket_count']} spawned: {r['ticket_ids']}")
    if "autoloop" in r:
        _print_autoloop(r["autoloop"])
    else:
        console.print()
        console.print(r["next"])


@main.command("autoloop")
@click.option("--client", required=True)
@click.option("--project", required=True)
@click.option("--max-iter", default=10, type=int)
def autoloop_cmd(client: str, project: str, max_iter: int) -> None:
    """Drive every backlog ticket through awaiting_approval. Stops at the human gate."""
    console.rule(f"[bold cyan]consilo autoloop {client}/{project}")
    r = task_lifecycle.autoloop(client, project, max_iter=max_iter)
    _print_autoloop(r)


def _print_autoloop(r: dict) -> None:
    console.print(f"[green]iterations  :[/] {r['iterations']}")
    for p in r["processed"]:
        if "error" in p:
            console.print(f"  [red]{p['ticket_id']} error: {p['error']}[/]")
        else:
            console.print(f"  {p['ticket_id']} → {p['verdict']} "
                          f"({p['suggestions']} suggestions)")
    console.print(f"[green]awaiting    :[/] {r['awaiting_approval']}")
    if r["awaiting_approval"]:
        console.print()
        console.print(r["next"])


@main.command("worker")
@click.option("--interval", default=300, type=int,
              help="Seconds between ticks (default 300).")
@click.option("--max-iter-per-project", default=5, type=int)
@click.option("--once", is_flag=True, help="Run a single tick and exit.")
def worker_cmd(interval: int, max_iter_per_project: int, once: bool) -> None:
    """Long-running background runner: autoloop every opted-in project.

    Each project must:
      - have prd.approved.md present, AND
      - either set autoloop_enabled: true in project.yaml,
        OR be listed in vault/shared/worker.yaml under `enable:`.

    Heartbeats are visible at /ops on the dashboard.
    """
    console.rule(f"[bold cyan]consilo worker interval={interval}s")
    r = worker_mod.run(interval=interval,
                       max_iter_per_project=max_iter_per_project, once=once)
    console.print(f"[green]worker:[/] {r['worker_id']} stopped after "
                  f"{r['iterations']} iterations")


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
