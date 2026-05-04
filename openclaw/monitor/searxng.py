"""OC-027 — SearXNG monitor. Per-client query packs feeding the ingest pipeline.

Reads `vault/clients/<client>/projects/<project>/queries.yaml`, runs each query
against a local SearXNG instance, dedupes results by URL hash (SQLite-backed),
and ingests new results as events.

Run on demand (one-shot, idempotent) — schedule with cron/systemd if recurring:
    openclaw search-monitor --client acme --project digital-platform
    openclaw search-monitor --all   # walks every client/project with queries.yaml
"""
from __future__ import annotations
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx
import yaml

from ..config import get_settings
from ..vault import project_dir
from ..ingest import ingest, InboundMessage
from .. import sqlite_store


def _searxng_url() -> str:
    return os.getenv("SEARXNG_URL", "http://127.0.0.1:8888").rstrip("/")


SEEN_URLS_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_urls (
    url_hash    TEXT PRIMARY KEY,
    client      TEXT NOT NULL,
    project     TEXT NOT NULL,
    url         TEXT NOT NULL,
    seen_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_seen_cp ON seen_urls(client, project);
"""


def _ensure_seen_table() -> None:
    with sqlite_store.connect() as c:
        c.executescript(SEEN_URLS_SCHEMA)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_seen(client: str, project: str, url: str) -> bool:
    _ensure_seen_table()
    with sqlite_store.connect() as c:
        row = c.execute(
            "SELECT 1 FROM seen_urls WHERE url_hash=? AND client=? AND project=?",
            (_url_hash(url), client, project),
        ).fetchone()
        return row is not None


def _mark_seen(client: str, project: str, url: str) -> None:
    _ensure_seen_table()
    with sqlite_store.connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO seen_urls VALUES (?, ?, ?, ?, ?)",
            (_url_hash(url), client, project, url,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )


def _load_queries(client: str, project: str) -> list[str]:
    p = project_dir(client, project) / "queries.yaml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    qs = data.get("queries", [])
    return [str(q).strip() for q in qs if str(q).strip()]


def _searxng_search(query: str, *, limit: int = 10,
                    timeout: float = 10.0) -> list[dict[str, Any]]:
    """Hit SearXNG JSON API. Empty list on failure (logged in caller)."""
    url = f"{_searxng_url()}/search"
    params = {"q": query, "format": "json", "safesearch": "0",
              "categories": "general,news"}
    r = httpx.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return list((data.get("results") or [])[:limit])


def _format_event_text(query: str, hit: dict) -> str:
    title = hit.get("title", "(no title)")
    url = hit.get("url", "")
    snippet = hit.get("content") or hit.get("snippet") or ""
    src = hit.get("engine") or hit.get("source") or "searxng"
    return (
        f"SearXNG hit (query: {query!r}, source: {src})\n"
        f"URL: {url}\n"
        f"Title: {title}\n\n"
        f"{snippet}"
    )


def run_for_project(client: str, project: str, *,
                    per_query_limit: int = 10) -> dict:
    queries = _load_queries(client, project)
    if not queries:
        return {"client": client, "project": project, "queries": 0,
                "ingested": 0, "skipped": True, "reason": "no queries.yaml"}

    ingested = 0
    skipped = 0
    errors: list[str] = []
    for q in queries:
        try:
            hits = _searxng_search(q, limit=per_query_limit)
        except Exception as e:
            errors.append(f"{q!r}: {e}")
            continue
        for hit in hits:
            url = hit.get("url")
            if not url:
                continue
            if _is_seen(client, project, url):
                skipped += 1
                continue
            text = _format_event_text(q, hit)
            ingest(InboundMessage(
                source="searxng",
                chat_id=f"{client}:{project}",
                message_id=_url_hash(url),
                sender=hit.get("engine") or "searxng",
                text=text,
                route_override=(client, project),
            ))
            _mark_seen(client, project, url)
            ingested += 1

    return {
        "client": client,
        "project": project,
        "queries": len(queries),
        "ingested": ingested,
        "deduped": skipped,
        "errors": errors,
        "skipped": False,
    }


def run_for_all() -> list[dict]:
    """Walk vault/clients/*/projects/*/queries.yaml and run each."""
    s = get_settings()
    out: list[dict] = []
    clients_dir = s.vault_dir / "clients"
    if not clients_dir.exists():
        return out
    for c in sorted(clients_dir.iterdir()):
        if not c.is_dir() or c.name.startswith("_"):
            continue
        proj_dir = c / "projects"
        if not proj_dir.exists():
            continue
        for p in sorted(proj_dir.iterdir()):
            if not p.is_dir():
                continue
            if (p / "queries.yaml").exists():
                out.append(run_for_project(c.name, p.name))
    return out
