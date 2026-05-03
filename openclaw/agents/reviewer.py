"""OC-014 — Reviewer agent. Returns structured suggestions on the implementer's draft."""
from __future__ import annotations
import json
from ..context import build as build_context
from ..llm import LLMClient
from ..schemas import Ticket
from ..vault import project_dir
from .. import audit, sqlite_store


SYSTEM_PROMPT = """You are the Reviewer agent inside OpenClaw.
You critique a deck-outline draft against:
- the source event (factual fidelity),
- the project objective (relevance),
- the consultant's CxO style (tight, action-oriented, no filler).
Respond with strict JSON of the form:
{
  "verdict": "ok" | "needs-revisions",
  "suggestions": [
    {"slide": <int|null>, "issue": "...", "fix": "...", "severity": "minor|major"}
  ]
}
Do not include any text outside the JSON object.
"""


def run(ticket: Ticket) -> dict:
    pd = project_dir(ticket.client, ticket.project)
    draft_path = pd / "kanban" / "in_progress" / ticket.id / "draft.md"
    if not draft_path.exists():
        raise FileNotFoundError(f"no draft to review at {draft_path}")
    draft = draft_path.read_text()

    bundle = build_context(ticket)
    user_prompt = (
        bundle.render()
        + "\n\n=== DRAFT TO REVIEW ===\n"
        + draft
        + "\n\n=== TASK ===\nReturn the JSON review now."
    )
    llm = LLMClient()
    resp = llm.chat(SYSTEM_PROMPT, user_prompt, max_tokens=900, temperature=0.0)

    parsed: dict
    try:
        parsed = json.loads(resp["content"])
    except json.JSONDecodeError:
        parsed = {"verdict": "needs-revisions",
                  "suggestions": [{"slide": None, "issue": "review JSON unparseable",
                                    "fix": "rerun reviewer", "severity": "major"}],
                  "_raw": resp["content"]}

    review_path = pd / "kanban" / "in_progress" / ticket.id / "review.json"
    review_path.write_text(json.dumps(parsed, indent=2))

    run_id = audit.new_run_id()
    trace = audit.write_run(
        ticket.client, ticket.project, ticket.id, run_id,
        {
            "agent": "reviewer",
            "llm_mode": resp.get("mode"),
            "llm_model": resp.get("model"),
            "review_path": str(review_path),
            "verdict": parsed.get("verdict"),
            "suggestion_count": len(parsed.get("suggestions", [])),
            "suggestions": parsed.get("suggestions", []),
        },
    )
    sqlite_store.record_run(run_id, ticket.id, "reviewer", "ok", str(trace))

    return {
        "run_id": run_id,
        "review_path": str(review_path),
        "audit_path": str(trace),
        "verdict": parsed.get("verdict"),
        "suggestions": parsed.get("suggestions", []),
    }
