"""OC-018/019/020 — HTMX dashboard.

Single-process FastAPI app on port 8091 (configurable). Routes:
  GET  /                           — landing: list of clients/projects + boards
  GET  /board                      — kanban board (HTMX-friendly)
  GET  /board/columns              — partial: just the columns (for refresh)
  GET  /tickets/{id}               — ticket detail + audit timeline
  POST /tickets/{id}/run           — kicks off implementer + reviewer (service.run_slice)
  POST /tickets/{id}/approve       — human approval gate (service.approve)
  GET  /healthz                    — liveness

UI stack: Jinja2 + HTMX + Alpine + Tailwind (CDN). No build step.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import kanban, audit, service, sqlite_store
from ..config import get_settings
from ..vault import project_dir

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app = FastAPI(title="OpenClaw dashboard")


KANBAN_COLUMNS = [
    "backlog", "in_progress", "awaiting_approval", "approved", "done",
]
COLUMN_LABELS = {
    "backlog": "Backlog",
    "in_progress": "In progress",
    "awaiting_approval": "Awaiting approval",
    "approved": "Approved",
    "done": "Done",
}


def _list_engagements() -> list[dict]:
    """Walk the vault and list (client, project) pairs that have a kanban dir."""
    s = get_settings()
    out: list[dict] = []
    clients_dir = s.vault_dir / "clients"
    if not clients_dir.exists():
        return out
    for c in sorted(clients_dir.iterdir()):
        if not c.is_dir() or c.name.startswith("_"):
            continue
        proj_dir = c / "projects"
        if not proj_dir.exists():
            continue
        for p in sorted(proj_dir.iterdir()):
            if not p.is_dir():
                continue
            counts = {}
            for col in KANBAN_COLUMNS:
                d = p / "kanban" / col
                counts[col] = len(list(d.glob("*.yaml"))) if d.exists() else 0
            out.append({
                "client": c.name,
                "project": p.name,
                "counts": counts,
                "total": sum(counts.values()),
            })
    return out


def _load_columns(client: str, project: str) -> dict[str, list[dict]]:
    cols = {col: [] for col in KANBAN_COLUMNS}
    try:
        tickets = kanban.list_tickets(client, project)
    except Exception:
        return cols
    for t in tickets:
        cols.setdefault(t.state, []).append(t.model_dump())
    return cols


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html",
        {"engagements": _list_engagements()},
    )


@app.get("/board", response_class=HTMLResponse)
def board(request: Request, client: str, project: str):
    cols = _load_columns(client, project)
    return templates.TemplateResponse(
        request, "board.html",
        {
            "client": client,
            "project": project,
            "columns": cols,
            "column_order": KANBAN_COLUMNS,
            "column_labels": COLUMN_LABELS,
        },
    )


@app.get("/board/columns", response_class=HTMLResponse)
def board_columns(request: Request, client: str, project: str):
    cols = _load_columns(client, project)
    return templates.TemplateResponse(
        request, "_columns.html",
        {
            "client": client,
            "project": project,
            "columns": cols,
            "column_order": KANBAN_COLUMNS,
            "column_labels": COLUMN_LABELS,
        },
    )


def _load_ticket_view(client: str, project: str, ticket_id: str) -> dict:
    t = kanban.load_ticket(client, project, ticket_id)
    pd = project_dir(client, project)
    draft_path = pd / "kanban" / "in_progress" / ticket_id / "draft.md"
    review_path = pd / "kanban" / "in_progress" / ticket_id / "review.json"
    artifact_path = pd / "artifacts" / "decks" / f"{ticket_id.lower()}-deck-outline.md"

    runs: list[dict] = []
    for p in audit.list_runs(client, project, ticket_id):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        runs.append({"file": p.name, **data})

    review = None
    if review_path.exists():
        try:
            review = json.loads(review_path.read_text())
        except Exception:
            review = None

    return {
        "ticket": t.model_dump(),
        "draft": draft_path.read_text() if draft_path.exists() else None,
        "review": review,
        "artifact": artifact_path.read_text() if artifact_path.exists() else None,
        "audit_runs": runs,
    }


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: str, client: str, project: str):
    try:
        view = _load_ticket_view(client, project, ticket_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return templates.TemplateResponse(
        request, "ticket.html",
        {
            "client": client,
            "project": project,
            **view,
        },
    )


@app.post("/tickets/{ticket_id}/run", response_class=HTMLResponse)
def ticket_run(request: Request, ticket_id: str,
               client: str = Form(...), project: str = Form(...)):
    try:
        result = service.run_slice(client, project, ticket_id)
        flash = {"ok": True, "msg": (
            f"Slice ran. Verdict: {result['reviewer']['verdict']}, "
            f"{len(result['reviewer']['suggestions'])} suggestions."
        )}
    except Exception as e:
        flash = {"ok": False, "msg": f"Run failed: {e}"}
    view = _load_ticket_view(client, project, ticket_id)
    return templates.TemplateResponse(
        request, "_ticket_panel.html",
        {"client": client, "project": project,
         "flash": flash, **view},
    )


@app.post("/tickets/{ticket_id}/approve", response_class=HTMLResponse)
def ticket_approve(request: Request, ticket_id: str,
                   client: str = Form(...), project: str = Form(...),
                   apply_suggestions: str | None = Form(default=None),
                   notes: str | None = Form(default=None)):
    apply_flag = bool(apply_suggestions)
    try:
        result = service.approve(client, project, ticket_id,
                                 apply_suggestions=apply_flag, notes=notes)
        flash = {"ok": True, "msg": (
            f"Approved. Commit {result['commit_sha'][:8] or '(no diff)'} "
            f"on branch {client}/{project}."
        )}
    except Exception as e:
        flash = {"ok": False, "msg": f"Approve failed: {e}"}
    view = _load_ticket_view(client, project, ticket_id)
    return templates.TemplateResponse(
        request, "_ticket_panel.html",
        {"client": client, "project": project,
         "flash": flash, **view},
    )


def main() -> None:
    import uvicorn
    host = os.getenv("OPENCLAW_DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("OPENCLAW_DASHBOARD_PORT", "8091"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
