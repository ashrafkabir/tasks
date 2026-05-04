"""OC-022 — Briefer agent.

Synthesizes a tight, CxO-ready briefing in markdown from:
  - the latest event (or a specified event)
  - the client's curated memory facts (semantic-search top-k against the
    headline hint)
  - the project's stated objective

Output: vault/clients/<c>/projects/<p>/briefs/<YYYY-MM-DD>-<slug>.md
Audit:  vault/clients/<c>/projects/<p>/audit/_briefs/<run-id>.json
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..vault import (
    project_dir, briefs_dir, list_events, read_event_md,
)
from ..llm import LLMClient
from ..embed import Embedder
from .. import qdrant_store, sqlite_store, audit


SYSTEM_PROMPT = """You are the Briefer agent inside OpenClaw, producing a CxO briefing for a Visionet IT services consultant.
Output strict markdown with this section order:
  # Briefing — <client>: <headline>
  ## Headline
  ## Why now
  ## Key facts
  ## Risks
  ## Recommended next moves

Constraints:
- Tight, executive-level prose.
- 3–5 bullets per "Key facts" / "Recommended next moves".
- 2–3 bullets in "Risks".
- Cite only the provided facts/events; do not invent specifics.
- Recommend a single Visionet path of action.
"""


def _slug(s: str, n: int = 32) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n] or "brief"


def _select_event(client: str, project: str, event_id: str | None) -> dict | None:
    """Return the chosen event as a dict {id, title, body, path} or None."""
    events = list_events(client, project)
    if not events:
        return None
    chosen: Path | None = None
    if event_id:
        for p in events:
            try:
                ev = read_event_md(p)
                if ev.id == event_id:
                    chosen = p
                    break
            except Exception:
                continue
        if not chosen:
            raise FileNotFoundError(f"event id {event_id} not found in {client}/{project}")
    else:
        chosen = events[-1]
    ev = read_event_md(chosen)
    return {"id": ev.id, "title": ev.title, "body": ev.body, "path": str(chosen)}


def _semantic_memory_hits(client: str, query: str, limit: int = 6) -> list[dict]:
    try:
        e = Embedder()
        qvec = e.embed([query])[0]
        return qdrant_store.search(client, qvec, limit=limit)
    except Exception:
        return []


def _build_prompt(client: str, project: str, event: dict | None,
                  hits: list[dict], objective: str) -> str:
    lines = [f"CLIENT: {client}", f"PROJECT: {project}"]
    if event:
        lines.append(f"HEADLINE_HINT: {event['title']}")
    lines.append("")
    lines.append("OBJECTIVE:")
    lines.append(objective.strip() or "(none stated)")
    lines.append("")
    if event:
        lines.append("LATEST EVENT:")
        lines.append(event["body"][:3000])
        lines.append("")
    if hits:
        lines.append("MEMORY HITS:")
        for h in hits[:6]:
            payload = h.get("payload") or {}
            lines.append(f"- ({payload.get('kind','')}, score={h.get('score', 0):.3f}) "
                         f"{payload.get('title','')}")
        lines.append("")
    lines.append("=== TASK ===")
    lines.append("Write the briefing now.")
    return "\n".join(lines)


def run(client: str, project: str, *, event_id: str | None = None) -> dict:
    pd = project_dir(client, project)
    objective = ""
    py = pd / "project.yaml"
    if py.exists():
        import yaml
        objective = (yaml.safe_load(py.read_text()) or {}).get("objective", "")

    event = _select_event(client, project, event_id)
    headline_hint = event["title"] if event else "Strategic update"
    hits = _semantic_memory_hits(client, headline_hint)

    user_prompt = _build_prompt(client, project, event, hits, objective)
    llm = LLMClient()
    resp = llm.chat(SYSTEM_PROMPT, user_prompt, max_tokens=1500, temperature=0.2)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fname = f"{today}-{_slug(headline_hint)}.md"
    out_path = briefs_dir(client, project) / fname
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(resp["content"])

    run_id = audit.new_run_id()
    audit_root = pd / "audit" / "_briefs"
    audit_root.mkdir(parents=True, exist_ok=True)
    audit_path = audit_root / f"{run_id}.json"
    audit_path.write_text(json.dumps({
        "agent": "briefer",
        "run_id": run_id,
        "client": client,
        "project": project,
        "event_id": event["id"] if event else None,
        "llm_mode": resp.get("mode"),
        "llm_model": resp.get("model"),
        "memory_hit_count": len(hits),
        "brief_path": str(out_path),
        "brief_chars": len(resp["content"]),
        "user_prompt_excerpt": user_prompt[:600],
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2, default=str))
    sqlite_store.record_run(run_id, f"brief-{client}-{project}", "briefer",
                            "ok", str(audit_path))

    return {
        "run_id": run_id,
        "brief_path": str(out_path),
        "audit_path": str(audit_path),
        "event_id": event["id"] if event else None,
        "memory_hit_count": len(hits),
    }
