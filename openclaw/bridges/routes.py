"""Chat → (client, project) routing.

Resolution order:
  1. `vault/shared/chat_routes.yaml` exact match (source + chat_id)
  2. `OPENCLAW_DEFAULT_CLIENT` / `OPENCLAW_DEFAULT_PROJECT` env vars
  3. `_unrouted` fallback (event lands in vault/clients/_unrouted/)
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import yaml
from ..config import get_settings


@dataclass
class Route:
    client: str
    project: str
    source: str = "default"


def _routes_path() -> Path:
    return get_settings().vault_dir / "shared" / "chat_routes.yaml"


def load_routes() -> list[dict]:
    p = _routes_path()
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    return data.get("routes", [])


def resolve(source: str, chat_id: str) -> Route:
    for r in load_routes():
        if r.get("source") == source and str(r.get("chat_id")) == str(chat_id):
            return Route(client=r["client"], project=r["project"], source=source)

    default_client = os.getenv("OPENCLAW_DEFAULT_CLIENT")
    default_project = os.getenv("OPENCLAW_DEFAULT_PROJECT")
    if default_client and default_project:
        return Route(client=default_client, project=default_project, source=source)

    return Route(client="_unrouted", project="_unrouted", source=source)
