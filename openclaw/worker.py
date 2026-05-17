"""Background runner. Long-running process that:
  - walks every engagement under vault/clients/<c>/projects/<p>/
  - runs autoloop on each project that has approved-PRD + backlog tickets
  - records a heartbeat in SQLite each cycle so the ops console can show liveness

Honors option iii: never auto-approves. Each ticket lands at
`awaiting_approval` and stops there for the operator.

A project participates only if `<project>/project.yaml` has
`autoloop_enabled: true` OR if `vault/shared/worker.yaml` lists it.
Default is opt-in to avoid surprise activity. The PRD must be approved
(presence of `prd.approved.md`) — projects without an approved plan are
skipped.
"""
from __future__ import annotations
import json
import os
import signal
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

from .config import get_settings
from . import task_lifecycle, sqlite_store, kanban


_RUNNING = True


def _stop(*_a: Any) -> None:
    global _RUNNING
    _RUNNING = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_global_config() -> dict:
    s = get_settings()
    p = s.vault_dir / "shared" / "worker.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def _project_opted_in(client: str, project: str, global_cfg: dict) -> bool:
    """Project participates if either:
      - vault/shared/worker.yaml has the (client, project) pair in `enable`, OR
      - project.yaml has `autoloop_enabled: true`
    """
    for entry in global_cfg.get("enable", []) or []:
        if entry.get("client") == client and entry.get("project") == project:
            return True
    pyaml = (get_settings().vault_dir / "clients" / client / "projects"
             / project / "project.yaml")
    if not pyaml.exists():
        return False
    try:
        data = yaml.safe_load(pyaml.read_text()) or {}
    except Exception:
        return False
    return bool(data.get("autoloop_enabled"))


def _approved(client: str, project: str) -> bool:
    return (get_settings().vault_dir / "clients" / client / "projects"
            / project / "prd.approved.md").exists()


def _walk_engagements() -> list[tuple[str, str]]:
    clients_dir = get_settings().vault_dir / "clients"
    if not clients_dir.exists():
        return []
    out: list[tuple[str, str]] = []
    for c in sorted(clients_dir.iterdir()):
        if not c.is_dir() or c.name.startswith("_"):
            continue
        pdir = c / "projects"
        if not pdir.exists():
            continue
        for p in sorted(pdir.iterdir()):
            if p.is_dir():
                out.append((c.name, p.name))
    return out


def tick(*, worker_id: str, max_iter_per_project: int = 5) -> dict:
    """One pass: run autoloop on every opted-in engagement that has backlog."""
    global_cfg = _load_global_config()
    processed: list[dict] = []
    for client, project in _walk_engagements():
        if not _project_opted_in(client, project, global_cfg):
            continue
        if not _approved(client, project):
            continue
        backlog = [t for t in kanban.list_tickets(client, project)
                   if t.state == "backlog"]
        if not backlog:
            continue
        try:
            r = task_lifecycle.autoloop(client, project,
                                       max_iter=max_iter_per_project)
            processed.append({
                "client": client, "project": project,
                "iterations": r["iterations"],
                "awaiting": r["awaiting_approval"],
            })
        except Exception as e:
            processed.append({"client": client, "project": project,
                              "error": str(e)})
    return {"processed": processed, "ts": _now()}


def run(*, interval: int = 300, max_iter_per_project: int = 5,
        once: bool = False) -> dict:
    """Main loop. Heartbeats every cycle; runs `tick` between sleeps.
    Honors SIGTERM/SIGINT for clean shutdown."""
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    pid = os.getpid()
    iterations = 0
    last: dict = {}

    sqlite_store.heartbeat(worker_id, pid, iterations,
                            json.dumps({"status": "starting"}))

    while _RUNNING:
        try:
            last = tick(worker_id=worker_id,
                        max_iter_per_project=max_iter_per_project)
        except Exception as e:
            last = {"error": str(e), "ts": _now()}
        iterations += 1
        sqlite_store.heartbeat(worker_id, pid, iterations,
                                json.dumps(last, default=str)[:4000])
        if once:
            break
        # Sleep in small chunks so SIGTERM lands quickly.
        slept = 0
        while _RUNNING and slept < interval:
            time.sleep(min(2, interval - slept))
            slept += 2

    sqlite_store.heartbeat(worker_id, pid, iterations,
                            json.dumps({"status": "stopped",
                                        "last": last}, default=str)[:4000])
    return {"worker_id": worker_id, "iterations": iterations, "last": last}
