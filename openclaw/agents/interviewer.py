"""Headless PRD compiler. Same intent as the `grillme` Claude Code skill, but
runs without an interactive Claude session — reads a filled `prd_answers.yaml`
and produces `prd.md`.

Used by chat-bridge flows (Telegram operator types `/compile-prd ...`) and by
the CLI when the user prefers to edit the YAML manually.

This module is deliberately template-driven (no LLM call) because the user's
answers go in verbatim. Polish via LLM is a future opt-in flag.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

from ..vault import project_dir


PRD_ANSWERS_SKELETON = """\
# Fill in below, then run:
#   openclaw compile-prd --client {client} --project {project}
# Keep values terse, executive-grade. The grillme skill in Claude Code can
# also fill this in by interview.
client: {client}
project: {project}

cxo_goal: |
  (Who is the CxO, and what measurable goal are they accountable for?
   Name the threshold that constitutes a win.)

trigger: |
  (What just happened that makes this urgent?
   What's the latest the work can land and still matter?)

artifacts: |
  (One or more of: deck-outline, briefing, talking-points, board-readout, RFP-response.
   Be specific about quantities.)

constraints: |
  (Budget signals, internal politics, recent vendor decisions,
   compliance/regulatory items.)

capability: |
  (The Visionet service line / IP / case study we are positioning.)

success_signal: |
  (What concrete next action from the client would constitute "yes"?)

non_goals: |
  (What we are explicitly NOT doing in this engagement.)
"""


PRD_TEMPLATE = """\
# PRD — {client}/{project}

**Owner:** Ashraf · **Date:** {date}

## 1. The CxO and the goal
{cxo_goal}

## 2. Triggering event and time window
{trigger}

## 3. Artifacts to produce
{artifacts}

## 4. Constraints
{constraints}

## 5. Visionet positioning
{capability}

## 6. Success criteria
{success_signal}

## 7. Non-goals
{non_goals}

## 8. Ticket plan (initial)
{ticket_plan}
"""


_ARTIFACT_KINDS = {
    "deck-outline": "Draft deck outline with speaker notes",
    "briefing":     "Draft CxO briefing markdown",
    "talking-points": "Draft talking-points sheet",
    "board-readout": "Draft board readout deck",
    "rfp-response": "Draft RFP response section",
}


def _derive_ticket_plan(artifacts_text: str, client: str) -> list[str]:
    """Scan the user's artifacts answer for known kinds; one ticket per kind found.
    Falls back to a default deck-outline if nothing parseable."""
    found: list[str] = []
    body = artifacts_text.lower()
    for kind in _ARTIFACT_KINDS:
        if kind in body:
            found.append(kind)
    if not found:
        found = ["deck-outline"]
    lines: list[str] = []
    for kind in found:
        title = f"{_ARTIFACT_KINDS[kind]} for {client}"
        acceptance = f"Output is a valid {kind} artifact and passes reviewer."
        lines.append(f"- [{kind}] {title} — {acceptance}")
    return lines


def write_skeleton(client: str, project: str) -> Path:
    pd = project_dir(client, project)
    pd.mkdir(parents=True, exist_ok=True)
    p = pd / "prd_answers.yaml"
    if not p.exists():
        p.write_text(PRD_ANSWERS_SKELETON.format(client=client, project=project))
    return p


def compile_prd(client: str, project: str) -> dict:
    pd = project_dir(client, project)
    ans_path = pd / "prd_answers.yaml"
    if not ans_path.exists():
        raise FileNotFoundError(
            f"no prd_answers.yaml at {ans_path}. Run: "
            f"openclaw start-task --client {client} --project {project}"
        )
    raw = yaml.safe_load(ans_path.read_text()) or {}

    def _g(key: str) -> str:
        v = (raw.get(key) or "").strip()
        if not v or v.startswith("(") and v.endswith(")"):
            return "(TBD)"
        return v

    artifacts = _g("artifacts")
    ticket_plan = _derive_ticket_plan(artifacts, client)
    prd = PRD_TEMPLATE.format(
        client=client, project=project,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        cxo_goal=_g("cxo_goal"),
        trigger=_g("trigger"),
        artifacts=artifacts,
        constraints=_g("constraints"),
        capability=_g("capability"),
        success_signal=_g("success_signal"),
        non_goals=_g("non_goals"),
        ticket_plan="\n".join(ticket_plan),
    )
    out = pd / "prd.md"
    out.write_text(prd)
    return {
        "client": client,
        "project": project,
        "prd_path": str(out),
        "answers_path": str(ans_path),
        "ticket_count_planned": len(ticket_plan),
    }
