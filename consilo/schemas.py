"""OC-005 — Pydantic schemas for vault YAML files and ticket envelope."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import yaml


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Client(BaseModel):
    slug: str
    display_name: str
    industry: str | None = None
    primary_contact: str | None = None
    notes: str | None = None

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: str) -> str:
        if not v or not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"invalid client slug: {v!r}")
        return v.lower()


class Project(BaseModel):
    slug: str
    client: str
    display_name: str
    objective: str
    status: Literal["active", "paused", "closed"] = "active"

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: str) -> str:
        if not v or not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"invalid project slug: {v!r}")
        return v.lower()


TicketState = Literal[
    "backlog", "in_progress", "awaiting_approval", "approved", "done"
]


class Ticket(BaseModel):
    id: str
    client: str
    project: str
    title: str
    state: TicketState = "backlog"
    kind: str = "deck-outline"
    source_event: str | None = None
    acceptance: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class Event(BaseModel):
    id: str
    client: str
    project: str
    title: str
    body: str
    received_at: str = Field(default_factory=_now_iso)
    source: str = "synthetic"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def dump_yaml(path: Path, data: dict | BaseModel) -> None:
    if isinstance(data, BaseModel):
        data = data.model_dump()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))


def validate_vault(vault_dir: Path) -> list[str]:
    """Walk the vault and validate every client.yaml/project.yaml. Returns errors."""
    errors: list[str] = []
    clients_dir = vault_dir / "clients"
    if not clients_dir.exists():
        return errors
    for client_dir in clients_dir.iterdir():
        if not client_dir.is_dir():
            continue
        c_yaml = client_dir / "client.yaml"
        if not c_yaml.exists():
            errors.append(f"missing {c_yaml}")
            continue
        try:
            Client(**load_yaml(c_yaml))
        except Exception as e:
            errors.append(f"{c_yaml}: {e}")
        proj_dir = client_dir / "projects"
        if not proj_dir.exists():
            continue
        for p in proj_dir.iterdir():
            if not p.is_dir():
                continue
            p_yaml = p / "project.yaml"
            if not p_yaml.exists():
                errors.append(f"missing {p_yaml}")
                continue
            try:
                Project(**load_yaml(p_yaml))
            except Exception as e:
                errors.append(f"{p_yaml}: {e}")
    return errors
