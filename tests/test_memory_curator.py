from __future__ import annotations
import json
from openclaw.ingest import ingest, InboundMessage
from openclaw.agents import memory_curator
from openclaw.vault import client_dir
from openclaw import sqlite_store, qdrant_store


def _seed_two_events(monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("OPENCLAW_DEFAULT_PROJECT", "digital-platform")
    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="1",
        sender="ashraf",
        text="Acme Q1 letter signals a $12M modernization budget. CFO mentioned a board readout.",
        received_at="2026-05-03T18:00:00+00:00",
    ))
    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="2",
        sender="ashraf",
        text="CIO wants to evaluate platform partners for the ERP modernization push.",
        received_at="2026-05-03T19:00:00+00:00",
    ))


def test_curator_extracts_facts_and_persists(tmp_workspace, monkeypatch):
    _seed_two_events(monkeypatch)

    result = memory_curator.run("acme")
    assert result["skipped"] is False
    assert result["events_processed"] == 2
    assert result["fact_count"] >= 1
    assert result["qdrant_upserts"] == result["fact_count"]

    mem = (client_dir("acme") / "memory.md").read_text()
    assert "acme — durable memory" in mem
    assert "subject" in mem
    assert "claim" in mem

    # SQLite should record both events as curated.
    curated = sqlite_store.already_curated([
        ev["id"] for ev in sqlite_store.list_client_events("acme")
    ])
    assert len(curated) == 2

    # Audit JSON written.
    from openclaw.config import get_settings
    audit_dir = get_settings().vault_dir / "shared" / "_curation" / "acme"
    files = list(audit_dir.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    assert payload["agent"] == "memory-curator"
    assert payload["fact_count"] == result["fact_count"]


def test_curator_idempotent(tmp_workspace, monkeypatch):
    _seed_two_events(monkeypatch)
    first = memory_curator.run("acme")
    assert first["skipped"] is False

    second = memory_curator.run("acme")
    assert second["skipped"] is True
    assert second["reason"] == "all events already curated"

    # Memory file should still have only one section.
    mem = (client_dir("acme") / "memory.md").read_text()
    assert mem.count("curation run") == 1


def test_curator_no_events_short_circuits(tmp_workspace):
    result = memory_curator.run("nonexistent-client")
    assert result["skipped"] is True
    assert result["reason"] == "no events"


def test_curator_facts_searchable_in_qdrant(tmp_workspace, monkeypatch):
    """A fact embedded by the curator must be retrievable from the per-client
    collection (proves memory is wired into the same retrieval surface as events)."""
    _seed_two_events(monkeypatch)
    memory_curator.run("acme")
    from openclaw.embed import Embedder
    e = Embedder()
    qvec = e.embed(["modernization budget"])[0]
    hits = qdrant_store.search("acme", qvec, limit=10)
    assert hits, "expected qdrant hits for client_acme"
    kinds = {h["payload"].get("kind") for h in hits}
    assert "memory_fact" in kinds


def test_curator_picks_up_new_events_after_first_run(tmp_workspace, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEFAULT_CLIENT", "acme")
    monkeypatch.setenv("OPENCLAW_DEFAULT_PROJECT", "digital-platform")
    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="1",
        sender="ashraf", text="First event about budget",
    ))
    first = memory_curator.run("acme")
    assert first["events_processed"] == 1

    ingest(InboundMessage(
        source="telegram", chat_id="42", message_id="2",
        sender="ashraf", text="Second event about platform",
    ))
    second = memory_curator.run("acme")
    assert second["skipped"] is False
    assert second["events_processed"] == 1  # only the new one
    mem = (client_dir("acme") / "memory.md").read_text()
    assert mem.count("curation run") == 2
