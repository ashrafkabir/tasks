"""OC-030 — Replay an agent run from a captured audit JSON.

Re-runs the same agent (implementer, reviewer, briefer) against the *current*
state of vault/Qdrant/SQLite. Useful when the underlying model has changed,
to compare outputs, or to re-derive an artifact after fixing a bug in an
agent.

Limitations:
  - Curator replay is intentionally not supported here; clear the
    `curated_events` rows for the events you want to re-process and run
    `openclaw curate-memory` instead.
  - Replay does NOT reconstruct the literal prompt that was sent
    originally — only what was durably persisted (event MD, project YAML,
    memory.md, Qdrant points). That's the right thing for "would this run
    differently today?" but not for byte-exact reproduction.

The new audit JSON is tagged with `replay_of: <original-run-id>` so it
cannot be confused with a fresh run.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings
from .vault import audit_dir
from . import kanban
from .agents import implementer, reviewer, briefer


def _candidate_paths(run_id: str, client: str | None,
                     project: str | None, ticket_id: str | None) -> list[Path]:
    s = get_settings()
    paths: list[Path] = []
    if client and project and ticket_id:
        paths.append(audit_dir(client, project, ticket_id) / f"{run_id}.json")
    if client and project:
        # _briefs audit lives under project audit/_briefs/
        from .vault import project_dir as _pd
        paths.append(_pd(client, project) / "audit" / "_briefs" / f"{run_id}.json")
    if client:
        paths.append(s.vault_dir / "shared" / "_curation" / client / f"{run_id}.json")
    return paths


def _find_audit(run_id: str, client: str | None, project: str | None,
                ticket_id: str | None) -> Path:
    """Try the obvious locations first; fall back to a vault-wide glob."""
    for p in _candidate_paths(run_id, client, project, ticket_id):
        if p.exists():
            return p
    s = get_settings()
    matches = list(s.vault_dir.rglob(f"{run_id}.json"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"no audit found for run_id {run_id!r}")


def _tag_replay(new_audit_path: Path, original_run_id: str) -> None:
    data = json.loads(new_audit_path.read_text())
    data["replay_of"] = original_run_id
    data["replayed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_audit_path.write_text(json.dumps(data, indent=2, default=str))


def replay(*, run_id: str, client: str | None = None,
           project: str | None = None, ticket_id: str | None = None) -> dict:
    audit_path = _find_audit(run_id, client, project, ticket_id)
    original = json.loads(audit_path.read_text())
    agent = original.get("agent")
    client = client or original.get("client")
    project = project or original.get("project")
    ticket_id = ticket_id or original.get("ticket_id")

    if agent == "implementer":
        if not (client and project and ticket_id):
            raise ValueError("implementer replay needs client/project/ticket_id")
        t = kanban.load_ticket(client, project, ticket_id)
        result = implementer.run(t)
    elif agent == "reviewer":
        if not (client and project and ticket_id):
            raise ValueError("reviewer replay needs client/project/ticket_id")
        t = kanban.load_ticket(client, project, ticket_id)
        result = reviewer.run(t)
    elif agent == "briefer":
        if not (client and project):
            raise ValueError("briefer replay needs client/project")
        result = briefer.run(client, project,
                              event_id=original.get("event_id"))
    else:
        raise ValueError(
            f"replay not supported for agent {agent!r}. "
            "Curator: clear curated_events rows and re-run `openclaw curate-memory`."
        )

    new_audit_path = Path(result["audit_path"])
    _tag_replay(new_audit_path, run_id)

    return {
        "agent": agent,
        "replayed_from": run_id,
        "original_audit": str(audit_path),
        "new_audit": str(new_audit_path),
        **result,
    }
