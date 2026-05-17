"""OC-012 — Per-run JSON audit traces."""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .vault import audit_dir


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{uuid.uuid4().hex[:8]}"


def write_run(client: str, project: str, ticket_id: str,
              run_id: str, payload: dict) -> Path:
    d = audit_dir(client, project, ticket_id)
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        **payload,
        "run_id": run_id,
        "ticket_id": ticket_id,
        "client": client,
        "project": project,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = d / f"{run_id}.json"
    out.write_text(json.dumps(payload, indent=2, default=str))
    return out


def list_runs(client: str, project: str, ticket_id: str) -> list[Path]:
    d = audit_dir(client, project, ticket_id)
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))
