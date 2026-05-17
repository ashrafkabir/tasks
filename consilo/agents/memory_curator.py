"""OC-021 — Memory-Curator agent.

Reads events that haven't been curated yet for a given client, asks the LLM to
extract durable facts, and persists those facts to:
  1. vault/clients/<client>/memory.md (append-only, one section per run)
  2. Qdrant client_<slug> collection with kind=memory_fact (so the
     context bundler surfaces them in future agent runs)
  3. SQLite curated_events table (so the same event is never re-curated)

Idempotent: re-running with no new events is a no-op (returns
fact_count=0, no audit, nothing written).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import yaml

from ..config import get_settings
from ..vault import client_dir, read_event_md
from ..embed import Embedder
from .. import sqlite_store, qdrant_store, audit


SYSTEM_PROMPT = """You are the Memory-Curator agent inside Consilo, a local-first agentic OS for a CxO consultant.
Your job: extract durable facts about a client/project from inbound events.
A "durable fact" is a claim that will still matter weeks from now (budget, headcount, decisions, deadlines, named stakeholders, vendor evaluations, regulatory items). Skip ephemeral chatter.

Respond with strict JSON only:
{
  "facts": [
    {
      "subject": "<who/what the fact is about>",
      "claim": "<one-sentence statement of fact>",
      "evidence_event_id": "<id of the event that supports this fact>",
      "confidence": "high" | "medium" | "low",
      "tags": ["<short keyword>", ...]
    }
  ]
}
Do not include text outside the JSON object. If no durable facts can be extracted, return {"facts": []}.
"""


def _build_prompt(client_slug: str, events: list[dict]) -> str:
    lines = [f"CLIENT: {client_slug}", "", "EVENTS:"]
    for ev in events:
        path = Path(ev["vault_path"])
        if not path.exists():
            continue
        try:
            ev_md = read_event_md(path)
        except Exception:
            continue
        lines.append(f"EVENT_ID: {ev['id']}")
        lines.append(f"TITLE: {ev['title']}")
        lines.append("BODY:")
        lines.append(ev_md.body[:3000])  # cap per-event body to keep prompt manageable
        lines.append("---")
    lines.append("")
    lines.append("=== TASK ===")
    lines.append("Return the JSON object now.")
    return "\n".join(lines)


def _append_memory_md(client_slug: str, run_id: str, facts: list[dict],
                      event_count: int) -> Path:
    cd = client_dir(client_slug)
    cd.mkdir(parents=True, exist_ok=True)
    p = cd / "memory.md"
    if not p.exists():
        p.write_text(f"# {client_slug} — durable memory\n\n")
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    section = [
        f"## {ts} — curation run {run_id} ({len(facts)} facts from {event_count} events)",
        "",
    ]
    for f in facts:
        section.extend([
            f"- **subject:** {f.get('subject','')}",
            f"  **claim:** {f.get('claim','')}",
            f"  **confidence:** {f.get('confidence','')}",
            f"  **evidence:** {f.get('evidence_event_id','')}",
            f"  **tags:** {', '.join(f.get('tags', []))}",
            "",
        ])
    with p.open("a") as fh:
        fh.write("\n".join(section) + "\n")
    return p


def _embed_facts(client_slug: str, run_id: str, facts: list[dict]) -> int:
    if not facts:
        return 0
    embedder = Embedder()
    qdrant_store.ensure_collection(client_slug, embedder.dim)
    texts = [f"{f.get('subject','')}: {f.get('claim','')}" for f in facts]
    vecs = embedder.embed(texts)
    items: list[tuple[str, list[float], dict]] = []
    for i, (f, vec) in enumerate(zip(facts, vecs)):
        ext_id = f"fact-{run_id}-{i:03d}"
        payload = {
            "title": f.get("claim", "")[:120],
            "kind": "memory_fact",
            "subject": f.get("subject", ""),
            "confidence": f.get("confidence", ""),
            "evidence_event_id": f.get("evidence_event_id", ""),
            "tags": f.get("tags", []),
            "run_id": run_id,
        }
        items.append((ext_id, vec, payload))
    return qdrant_store.upsert_points(client_slug, items)


def run(client_slug: str, *, project: str | None = None,
        since: str | None = None) -> dict:
    """Curate any uncurated events for a client. Returns a summary dict.

    `project` and `since` are optional filters. With no events to process,
    returns immediately with fact_count=0 and no audit written.
    """
    all_events = sqlite_store.list_client_events(client_slug, project=project, since=since)
    if not all_events:
        return {"client": client_slug, "events_seen": 0, "events_processed": 0,
                "fact_count": 0, "skipped": True, "reason": "no events"}

    seen_ids = [e["id"] for e in all_events]
    already = sqlite_store.already_curated(seen_ids)
    pending = [e for e in all_events if e["id"] not in already]
    if not pending:
        return {"client": client_slug, "events_seen": len(all_events),
                "events_processed": 0, "fact_count": 0, "skipped": True,
                "reason": "all events already curated"}

    from ..llm import LLMClient  # local import keeps test-monkeypatch surface small
    user_prompt = _build_prompt(client_slug, pending)
    llm = LLMClient()
    resp = llm.chat(SYSTEM_PROMPT, user_prompt, max_tokens=1500, temperature=0.0)

    try:
        parsed = json.loads(resp["content"])
        facts = parsed.get("facts", [])
        if not isinstance(facts, list):
            facts = []
    except json.JSONDecodeError:
        facts = []

    run_id = audit.new_run_id()
    memory_path = _append_memory_md(client_slug, run_id, facts, len(pending))
    upserted = _embed_facts(client_slug, run_id, facts)

    for ev in pending:
        # crude attribution: count how many facts cite this event id
        n = sum(1 for f in facts if f.get("evidence_event_id") == ev["id"])
        sqlite_store.mark_curated(ev["id"], client_slug, run_id, n)

    # Audit trace lives under shared/_curation/<client>/<run>.json (not
    # per-ticket — curation is a client-scoped operation).
    s = get_settings()
    audit_dir = s.vault_dir / "shared" / "_curation" / client_slug
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_payload = {
        "agent": "memory-curator",
        "run_id": run_id,
        "client": client_slug,
        "project_filter": project,
        "since": since,
        "llm_mode": resp.get("mode"),
        "llm_model": resp.get("model"),
        "events_processed": len(pending),
        "fact_count": len(facts),
        "qdrant_upserts": upserted,
        "memory_path": str(memory_path),
        "facts": facts,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    audit_path = audit_dir / f"{run_id}.json"
    audit_path.write_text(json.dumps(audit_payload, indent=2, default=str))
    sqlite_store.record_run(run_id, f"curate-{client_slug}", "memory-curator",
                            "ok", str(audit_path))

    return {
        "client": client_slug,
        "run_id": run_id,
        "events_seen": len(all_events),
        "events_processed": len(pending),
        "fact_count": len(facts),
        "qdrant_upserts": upserted,
        "memory_path": str(memory_path),
        "audit_path": str(audit_path),
        "skipped": False,
    }
