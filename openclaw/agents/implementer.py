"""OC-013 — Implementer agent. Drafts a deck-outline artifact w/ speaker notes."""
from __future__ import annotations
from pathlib import Path
from ..context import build as build_context
from ..llm import LLMClient
from ..schemas import Ticket
from ..vault import project_dir
from .. import audit, sqlite_store


SYSTEM_PROMPT = """You are the Implementer agent inside OpenClaw, a local-first agentic OS for a CxO consultant selling Visionet IT services.
Your job: produce a deck outline with speaker notes that a senior consultant can present to a client board.
Constraints:
- Markdown only.
- One H2 per slide. Each slide ends with a bold "**Speaker note:**" line.
- Recommend a single Visionet path of action.
- Do not invent client-specific facts beyond the source event and provided context.
"""


def run(ticket: Ticket) -> dict:
    bundle = build_context(ticket)
    user_prompt = (
        f"TASK_TITLE: {ticket.title}\n\n"
        + bundle.render()
        + "\n\n=== TASK ===\nDraft the deck outline now."
    )

    llm = LLMClient()
    resp = llm.chat(SYSTEM_PROMPT, user_prompt, max_tokens=1400, temperature=0.2)

    pd = project_dir(ticket.client, ticket.project)
    in_progress_dir = pd / "kanban" / "in_progress" / ticket.id
    in_progress_dir.mkdir(parents=True, exist_ok=True)
    draft_path = in_progress_dir / "draft.md"
    draft_path.write_text(resp["content"])

    run_id = audit.new_run_id()
    trace = audit.write_run(
        ticket.client, ticket.project, ticket.id, run_id,
        {
            "agent": "implementer",
            "llm_mode": resp.get("mode"),
            "llm_model": resp.get("model"),
            "system_prompt_sha": _sha(SYSTEM_PROMPT),
            "user_prompt_excerpt": user_prompt[:600],
            "draft_path": str(draft_path),
            "draft_chars": len(resp["content"]),
            "context_summary": {
                "has_source_event": bundle.source_event is not None,
                "recent_event_count": len(bundle.recent_events),
                "semantic_hit_count": len(bundle.semantic_hits),
            },
        },
    )
    sqlite_store.record_run(run_id, ticket.id, "implementer", "ok", str(trace))

    return {"run_id": run_id, "draft_path": str(draft_path), "audit_path": str(trace)}


def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:16]
