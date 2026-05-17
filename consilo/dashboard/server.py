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
import yaml as _yaml  # noqa: F401  (used inside _read_objective via lazy import)

from .. import kanban, audit, service, sqlite_store, task_lifecycle
from ..config import get_settings
from ..vault import project_dir, client_dir
from . import health as health_probe

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app = FastAPI(title="Consilo dashboard")


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


def _client_view(client_slug: str) -> dict:
    cd = client_dir(client_slug)
    client_yaml = (cd / "client.yaml").read_text() if (cd / "client.yaml").exists() else ""
    memory_md = (cd / "memory.md").read_text() if (cd / "memory.md").exists() else ""

    proj_dir = cd / "projects"
    projects: list[dict] = []
    if proj_dir.exists():
        for p in sorted(proj_dir.iterdir()):
            if not p.is_dir():
                continue
            counts = {col: 0 for col in KANBAN_COLUMNS}
            for col in KANBAN_COLUMNS:
                d = p / "kanban" / col
                if d.exists():
                    counts[col] = len(list(d.glob("*.yaml")))
            projects.append({
                "slug": p.name,
                "counts": counts,
                "total": sum(counts.values()),
                "objective": _read_objective(p),
            })

    # Recent events across all projects
    events: list[dict] = []
    try:
        events = sqlite_store.list_client_events(client_slug)[-25:][::-1]
    except Exception:
        pass

    return {
        "client": client_slug,
        "client_yaml": client_yaml,
        "memory_md": memory_md,
        "projects": projects,
        "events": events,
    }


def _read_objective(project_dir_path: Path) -> str:
    py = project_dir_path / "project.yaml"
    if not py.exists():
        return ""
    try:
        import yaml
        return (yaml.safe_load(py.read_text()) or {}).get("objective", "")
    except Exception:
        return ""


@app.get("/clients/{client_slug}", response_class=HTMLResponse)
def client_page(request: Request, client_slug: str):
    cd = client_dir(client_slug)
    if not cd.exists():
        raise HTTPException(status_code=404, detail=f"client {client_slug!r} not found")
    return templates.TemplateResponse(
        request, "client.html", _client_view(client_slug),
    )


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


@app.get("/new-task", response_class=HTMLResponse)
def new_task_page(request: Request):
    return templates.TemplateResponse(request, "new_task.html", {})


@app.post("/new-task", response_class=HTMLResponse)
def new_task_submit(request: Request,
                     client: str = Form(...), project: str = Form(...)):
    client = client.strip().lower()
    project = project.strip().lower()
    if not client or not project:
        raise HTTPException(status_code=400, detail="client and project required")
    task_lifecycle.start_task(client, project)
    return RedirectResponse(
        url=f"/prd?client={client}&project={project}",
        status_code=303,
    )


def _read_text(p: Path) -> str:
    return p.read_text() if p.exists() else ""


def _prd_view(client: str, project: str) -> dict:
    pd = project_dir(client, project)
    return {
        "client": client,
        "project": project,
        "answers_text": _read_text(pd / "prd_answers.yaml"),
        "prd_text": _read_text(pd / "prd.md"),
        "approved": (pd / "prd.approved.md").exists(),
    }


@app.get("/prd", response_class=HTMLResponse)
def prd_page(request: Request, client: str, project: str):
    pd = project_dir(client, project)
    if not pd.exists():
        raise HTTPException(status_code=404,
                            detail=f"no project at {client}/{project}")
    return templates.TemplateResponse(
        request, "prd_compose.html", _prd_view(client, project),
    )


@app.post("/prd/save", response_class=HTMLResponse)
def prd_save(request: Request,
              client: str = Form(...), project: str = Form(...),
              answers_text: str = Form(...)):
    pd = project_dir(client, project)
    if not pd.exists():
        raise HTTPException(status_code=404, detail="project not found")
    (pd / "prd_answers.yaml").write_text(answers_text)
    view = _prd_view(client, project)
    return templates.TemplateResponse(
        request, "_prd_panel.html",
        {"flash": {"ok": True, "msg": "Answers saved."}, **view},
    )


@app.post("/prd/compile", response_class=HTMLResponse)
def prd_compile(request: Request,
                 client: str = Form(...), project: str = Form(...)):
    try:
        r = task_lifecycle.compile_prd(client, project)
        flash = {"ok": True, "msg": (
            f"PRD compiled — {r['ticket_count_planned']} tickets planned."
        )}
    except Exception as e:
        flash = {"ok": False, "msg": f"compile failed: {e}"}
    view = _prd_view(client, project)
    return templates.TemplateResponse(
        request, "_prd_panel.html", {"flash": flash, **view},
    )


@app.post("/prd/approve", response_class=HTMLResponse)
def prd_approve(request: Request,
                 client: str = Form(...), project: str = Form(...),
                 run_autoloop: str | None = Form(default=None)):
    autoloop = bool(run_autoloop)
    try:
        r = task_lifecycle.approve_prd(client, project,
                                       run_autoloop=autoloop, max_iter=10)
        if autoloop and "autoloop" in r:
            extra = (f" Autoloop: {r['autoloop']['iterations']} iterations, "
                     f"{len(r['autoloop']['awaiting_approval'])} awaiting approval.")
        else:
            extra = ""
        flash = {"ok": True, "msg": (
            f"PRD approved — {r['ticket_count']} tickets spawned."
            + extra
        )}
    except Exception as e:
        flash = {"ok": False, "msg": f"approve failed: {e}"}
    view = _prd_view(client, project)
    return templates.TemplateResponse(
        request, "_prd_panel.html", {"flash": flash, **view},
    )


@app.post("/board/autoloop", response_class=HTMLResponse)
def board_autoloop(request: Request,
                    client: str = Form(...), project: str = Form(...)):
    """Run autoloop on existing backlog. Returns the refreshed board."""
    try:
        r = task_lifecycle.autoloop(client, project, max_iter=10)
        flash = {"ok": True, "msg": (
            f"Autoloop: {r['iterations']} iterations, "
            f"{len(r['awaiting_approval'])} awaiting approval."
        )}
    except Exception as e:
        flash = {"ok": False, "msg": f"autoloop failed: {e}"}
    cols = _load_columns(client, project)
    return templates.TemplateResponse(
        request, "_columns.html",
        {
            "client": client, "project": project,
            "columns": cols,
            "column_order": KANBAN_COLUMNS,
            "column_labels": COLUMN_LABELS,
            "flash": flash,
        },
    )


def _ops_view() -> dict:
    """Aggregate everything the ops console needs in one dict."""
    health = health_probe.snapshot()
    feed = sqlite_store.activity_feed(limit=50)
    queue = sqlite_store.queue_summary()
    workers = sqlite_store.list_workers()

    # Aggregate queue across all engagements.
    totals = {col: 0 for col in KANBAN_COLUMNS}
    for row in queue:
        st = row["state"]
        if st in totals:
            totals[st] += row["n"]
    return {
        "health": health,
        "feed": feed,
        "queue": queue,
        "queue_totals": totals,
        "workers": workers,
        "engagements": _list_engagements(),
        "column_order": KANBAN_COLUMNS,
        "column_labels": COLUMN_LABELS,
        "now": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/ops", response_class=HTMLResponse)
def ops_page(request: Request):
    return templates.TemplateResponse(request, "ops.html", _ops_view())


@app.get("/ops/panel", response_class=HTMLResponse)
def ops_panel(request: Request):
    """HTMX partial for live refresh of the ops console."""
    return templates.TemplateResponse(request, "_ops_panel.html", _ops_view())


@app.get("/ops/health.json")
def ops_health_json() -> dict:
    return health_probe.snapshot()


@app.get("/ops/feed.json")
def ops_feed_json(limit: int = 50) -> dict:
    return {"feed": sqlite_store.activity_feed(limit=limit)}


def main() -> None:
    import uvicorn
    host = os.getenv("CONSILO_DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("CONSILO_DASHBOARD_PORT", "8091"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
