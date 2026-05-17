"""Vault read/write helpers. Vault is the source of truth — markdown + YAML on disk."""
from __future__ import annotations
from pathlib import Path
from .config import get_settings
from .schemas import Event, load_yaml


def project_dir(client: str, project: str) -> Path:
    s = get_settings()
    return s.vault_dir / "clients" / client / "projects" / project


def client_dir(client: str) -> Path:
    return get_settings().vault_dir / "clients" / client


def kanban_path(client: str, project: str, state: str) -> Path:
    return project_dir(client, project) / "kanban" / state


def events_dir(client: str, project: str) -> Path:
    return project_dir(client, project) / "events"


def artifacts_decks_dir(client: str, project: str) -> Path:
    return project_dir(client, project) / "artifacts" / "decks"


def briefs_dir(client: str, project: str) -> Path:
    return project_dir(client, project) / "briefs"


def audit_dir(client: str, project: str, ticket_id: str) -> Path:
    return project_dir(client, project) / "audit" / ticket_id


def list_events(client: str, project: str) -> list[Path]:
    d = events_dir(client, project)
    if not d.exists():
        return []
    return sorted(d.glob("*.md"))


def read_event_md(path: Path) -> Event:
    """Parse a markdown event file with YAML frontmatter."""
    text = path.read_text()
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        meta = load_yaml_text(fm)
        body = body.lstrip("\n")
    else:
        meta = {}
        body = text
    meta.setdefault("body", body.strip())
    return Event(**meta)


def load_yaml_text(s: str) -> dict:
    import yaml
    return yaml.safe_load(s) or {}


def ensure_project_skeleton(client: str, project: str) -> None:
    base = project_dir(client, project)
    for sub in [
        "kanban/backlog",
        "kanban/in_progress",
        "kanban/awaiting_approval",
        "kanban/approved",
        "kanban/done",
        "events",
        "briefs",
        "artifacts/decks",
        "audit",
    ]:
        (base / sub).mkdir(parents=True, exist_ok=True)
