"""New-engagement lifecycle: start-task → compile-prd → approve-prd → autoloop.

This is the meta-layer above tickets. A single "task" creates the project
folder, captures a PRD, spawns the initial backlog, and (optionally) drives
each backlog ticket to `awaiting_approval` autonomously.

Per the hard constraint logged in DECISIONS.md (option iii):
the autoloop runs implementer + reviewer + transition to awaiting_approval
only — it does NOT auto-approve. Git-commit approvals stay human-gated.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import shutil
import yaml

from .schemas import Project
from .vault import ensure_project_skeleton, project_dir
from .agents import interviewer, planner
from . import kanban, service


def start_task(client: str, project: str, *,
               display_name: str | None = None,
               objective: str | None = None) -> dict:
    """Create the project folder + a `prd_answers.yaml` skeleton.

    Idempotent: re-running on an existing project does not clobber files.
    """
    ensure_project_skeleton(client, project)
    pd = project_dir(client, project)

    proj_yaml = pd / "project.yaml"
    if not proj_yaml.exists():
        proj = Project(
            slug=project, client=client,
            display_name=display_name or project.replace("-", " ").title(),
            objective=objective or "(set after PRD compile)",
            status="active",
        )
        proj_yaml.write_text(yaml.safe_dump(proj.model_dump(), sort_keys=False))

    answers_path = interviewer.write_skeleton(client, project)

    return {
        "client": client,
        "project": project,
        "project_dir": str(pd),
        "answers_path": str(answers_path),
        "next": (
            f"Fill in {answers_path} (use `/grillme` in Claude or edit by hand), "
            f"then: openclaw compile-prd --client {client} --project {project}"
        ),
    }


def compile_prd(client: str, project: str) -> dict:
    """Render prd.md from prd_answers.yaml."""
    return interviewer.compile_prd(client, project)


def approve_prd(client: str, project: str, *,
                run_autoloop: bool = False,
                max_iter: int = 10) -> dict:
    """Human-gate the PRD, spawn tickets, optionally drive the autoloop.

    Approval here is the human OK on the *project plan*. The downstream
    ticket-by-ticket approval gate is unchanged: each artifact still requires
    explicit `openclaw approve <ticket>` to commit/push.
    """
    pd = project_dir(client, project)
    prd_path = pd / "prd.md"
    if not prd_path.exists():
        raise FileNotFoundError(
            f"PRD not found at {prd_path}. "
            f"Run: openclaw compile-prd --client {client} --project {project}"
        )

    tickets, plan = planner.spawn_from_prd(client, project)

    # Snapshot the approved PRD so later edits to prd.md don't rewrite history.
    approved_path = pd / "prd.approved.md"
    shutil.copy2(prd_path, approved_path)

    approved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    audit_path = pd / "audit" / "_prd" / f"approved-{approved_at.replace(':', '')}.yaml"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(yaml.safe_dump({
        "kind": "prd_approval",
        "client": client,
        "project": project,
        "approved_at": approved_at,
        "prd_path": str(prd_path),
        "approved_path": str(approved_path),
        "ticket_count": len(tickets),
        "ticket_ids": [t.id for t in tickets],
        "plan": plan,
    }, sort_keys=False))

    out = {
        "client": client,
        "project": project,
        "ticket_count": len(tickets),
        "ticket_ids": [t.id for t in tickets],
        "approved_path": str(approved_path),
        "audit_path": str(audit_path),
    }
    if run_autoloop:
        out["autoloop"] = autoloop(client, project, max_iter=max_iter)
    else:
        out["next"] = (
            f"Run the autonomous loop with: "
            f"openclaw autoloop --client {client} --project {project}"
        )
    return out


def autoloop(client: str, project: str, *, max_iter: int = 10) -> dict:
    """Drive backlog → awaiting_approval, one ticket at a time, until backlog
    is empty or max_iter is hit. Never auto-approves (option iii)."""
    processed: list[dict] = []
    iterations = 0
    while iterations < max_iter:
        backlog = [
            t for t in kanban.list_tickets(client, project) if t.state == "backlog"
        ]
        if not backlog:
            break
        ticket = backlog[0]
        try:
            r = service.run_slice(client, project, ticket.id)
            processed.append({
                "ticket_id": ticket.id,
                "verdict": r["reviewer"]["verdict"],
                "suggestions": len(r["reviewer"]["suggestions"]),
            })
        except Exception as e:
            processed.append({"ticket_id": ticket.id, "error": str(e)})
            break
        iterations += 1

    awaiting = [t for t in kanban.list_tickets(client, project)
                if t.state == "awaiting_approval"]
    return {
        "client": client,
        "project": project,
        "iterations": iterations,
        "processed": processed,
        "awaiting_approval": [t.id for t in awaiting],
        "next": (
            f"Approve each: openclaw approve <ticket-id> "
            f"--client {client} --project {project} --apply"
        ),
    }
