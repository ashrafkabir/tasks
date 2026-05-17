"""Parses the `## 8. Ticket plan (initial)` section of a compiled PRD and
spawns tickets in the project's backlog.

Deterministic regex parser — no LLM call. The PRD format (produced by the
interviewer or grillme skill) is the contract.
"""
from __future__ import annotations
import re
from pathlib import Path

from ..schemas import Ticket
from ..vault import project_dir
from .. import kanban


_PLAN_HEADING = re.compile(r"^##\s*8\.\s*Ticket plan", re.IGNORECASE)
_NEXT_HEADING = re.compile(r"^##\s")
_BULLET = re.compile(
    r"^\s*-\s*\[(?P<kind>[A-Za-z][A-Za-z0-9-]*)\]\s*"
    r"(?P<title>.+?)(?:\s+—\s+(?P<acceptance>.+))?$"
)


def parse_plan(prd_md: str) -> list[dict]:
    """Returns a list of {kind, title, acceptance} dicts."""
    lines = prd_md.splitlines()
    in_section = False
    out: list[dict] = []
    for ln in lines:
        if _PLAN_HEADING.match(ln):
            in_section = True
            continue
        if in_section and _NEXT_HEADING.match(ln):
            break
        if not in_section:
            continue
        m = _BULLET.match(ln)
        if m:
            out.append({
                "kind": m.group("kind").strip().lower(),
                "title": m.group("title").strip(),
                "acceptance": (m.group("acceptance") or "").strip(),
            })
    return out


def _next_ticket_id(client: str, project: str) -> int:
    existing = kanban.list_tickets(client, project)
    nums: list[int] = []
    for t in existing:
        if t.id.startswith("OC-T-"):
            tail = t.id.split("-")[-1]
            if tail.isdigit():
                nums.append(int(tail))
    return (max(nums) + 1) if nums else 1


def spawn(client: str, project: str, plan: list[dict]) -> list[Ticket]:
    n = _next_ticket_id(client, project)
    out: list[Ticket] = []
    for item in plan:
        t = Ticket(
            id=f"OC-T-{n:03d}",
            client=client,
            project=project,
            title=item["title"],
            kind=item["kind"],
            acceptance=[item["acceptance"]] if item["acceptance"] else [],
        )
        kanban.write_ticket(t)
        out.append(t)
        n += 1
    return out


def spawn_from_prd(client: str, project: str) -> tuple[list[Ticket], list[dict]]:
    """Convenience: read prd.md, parse the plan, spawn. Returns (tickets, plan)."""
    prd_path = project_dir(client, project) / "prd.md"
    if not prd_path.exists():
        raise FileNotFoundError(f"PRD not found at {prd_path}")
    plan = parse_plan(prd_path.read_text())
    if not plan:
        raise ValueError(
            f"PRD at {prd_path} has no parseable '## 8. Ticket plan (initial)' section"
        )
    return spawn(client, project, plan), plan
