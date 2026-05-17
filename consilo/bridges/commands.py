"""Shared chat slash-command dispatcher.

Both bridges (Telegram polling, WhatsApp via wuzapi webhook) call
`dispatch(text)` to get a reply string. The bridges keep their own logic
for who-can-do-what (operator gating) and how-to-send (REST shape) — but
the command vocabulary and behavior is defined here in one place.

Vocabulary:
    /help                          — list commands
    /status                        — kanban for the default project
    /ticket <kind> <title>          — handled by ingest spawn rules; commands.py
                                      surfaces a friendly reply if a ticket
                                      was just spawned (caller passes it via
                                      `just_spawned_ticket`)
    /run <ticket-id>                — implementer + reviewer; transitions to
                                      awaiting_approval
    /approve <ticket-id>            — human gate: artifact + commit
    /start-task <client> <project>  — create project folder + answers skeleton
    /compile-prd <client> <project> — render prd.md from answers
    /approve-prd <client> <project> [autoloop]
                                    — approve PRD; optionally run autoloop
    /autoloop <client> <project>    — drive backlog → awaiting_approval
"""
from __future__ import annotations
import os
from .. import kanban, service, task_lifecycle


HELP_TEXT = (
    "Consilo bot. Commands:\n"
    "  /ticket <kind> <title>\n"
    "  /run <ticket-id>\n"
    "  /approve <ticket-id>\n"
    "  /start-task <client> <project>\n"
    "  /compile-prd <client> <project>\n"
    "  /approve-prd <client> <project> [autoloop]\n"
    "  /autoloop <client> <project>\n"
    "  /status"
)


def _defaults() -> tuple[str, str]:
    return (os.getenv("CONSILO_DEFAULT_CLIENT", ""),
            os.getenv("CONSILO_DEFAULT_PROJECT", ""))


def _cmd_status() -> str:
    client, project = _defaults()
    if not (client and project):
        return "status failed: CONSILO_DEFAULT_CLIENT/PROJECT not set"
    try:
        tickets = kanban.list_tickets(client, project)
    except Exception as e:
        return f"status failed: {e}"
    if not tickets:
        return "(empty board)"
    return "\n".join(f"{t.state}: {t.id} {t.title}" for t in tickets)


def _cmd_run(ticket_id: str) -> str:
    client, project = _defaults()
    try:
        r = service.run_slice(client, project, ticket_id)
        return (f"ran slice for {ticket_id}: "
                f"verdict={r['reviewer']['verdict']}, "
                f"suggestions={len(r['reviewer']['suggestions'])}")
    except Exception as e:
        return f"run failed: {e}"


def _cmd_approve(ticket_id: str) -> str:
    client, project = _defaults()
    try:
        r = service.approve(client, project, ticket_id, apply_suggestions=True)
        sha = (r.get("commit_sha") or "")[:8] or "(no diff)"
        return f"approved {ticket_id}: commit {sha}"
    except Exception as e:
        return f"approve failed: {e}"


def _cmd_start_task(client: str, project: str) -> str:
    try:
        r = task_lifecycle.start_task(client, project)
    except Exception as e:
        return f"start-task failed: {e}"
    return (f"started {client}/{project}\n"
            f"answers: {r['answers_path']}\n"
            f"fill it in, then: /compile-prd {client} {project}")


def _cmd_compile_prd(client: str, project: str) -> str:
    try:
        r = task_lifecycle.compile_prd(client, project)
    except Exception as e:
        return f"compile-prd failed: {e}"
    return (f"prd compiled: {r['prd_path']}\n"
            f"{r['ticket_count_planned']} tickets planned\n"
            f"next: /approve-prd {client} {project} autoloop")


def _cmd_approve_prd(client: str, project: str, *, autoloop: bool) -> str:
    try:
        r = task_lifecycle.approve_prd(client, project,
                                        run_autoloop=autoloop, max_iter=10)
    except Exception as e:
        return f"approve-prd failed: {e}"
    lines = [f"approved prd for {client}/{project}: "
             f"{r['ticket_count']} tickets — {', '.join(r['ticket_ids'])}"]
    if "autoloop" in r:
        lines.append(f"autoloop: {r['autoloop']['iterations']} iterations, "
                     f"awaiting={r['autoloop']['awaiting_approval']}")
    return "\n".join(lines)


def _cmd_autoloop(client: str, project: str) -> str:
    try:
        r = task_lifecycle.autoloop(client, project, max_iter=10)
    except Exception as e:
        return f"autoloop failed: {e}"
    return (f"autoloop for {client}/{project}: "
            f"{r['iterations']} iterations, "
            f"awaiting={r['awaiting_approval']}")


def dispatch(text: str, *, just_spawned_ticket: str | None = None) -> str | None:
    """Map a chat slash command to a reply string. Returns None if no match
    (caller decides what to do with non-command messages)."""
    parts = text.strip().split()
    if not parts:
        return None
    cmd = parts[0].lower()

    if cmd in ("/help", "/start"):
        return HELP_TEXT
    if cmd == "/status":
        return _cmd_status()

    if cmd == "/run" and len(parts) >= 2:
        return _cmd_run(parts[1])
    if cmd == "/approve" and len(parts) >= 2:
        return _cmd_approve(parts[1])

    if cmd == "/start-task" and len(parts) >= 3:
        return _cmd_start_task(parts[1], parts[2])
    if cmd == "/compile-prd" and len(parts) >= 3:
        return _cmd_compile_prd(parts[1], parts[2])
    if cmd == "/approve-prd" and len(parts) >= 3:
        autoloop = any(p.lower() in ("autoloop", "--autoloop")
                       for p in parts[3:])
        return _cmd_approve_prd(parts[1], parts[2], autoloop=autoloop)
    if cmd == "/autoloop" and len(parts) >= 3:
        return _cmd_autoloop(parts[1], parts[2])

    if cmd == "/ticket":
        # /ticket spawn happens in ingest pipeline; we just surface confirmation.
        return f"spawned ticket {just_spawned_ticket}" if just_spawned_ticket else None

    return None
