from __future__ import annotations
from unittest.mock import patch
from pathlib import Path
import yaml

from openclaw.monitor import searxng
from openclaw.vault import project_dir, ensure_project_skeleton, events_dir


def _seed_queries(client="acme", project="digital-platform"):
    ensure_project_skeleton(client, project)
    (project_dir(client, project) / "queries.yaml").write_text(yaml.safe_dump({
        "queries": ["Acme modernization", "Acme CIO"],
    }))


def _fake_results(*urls: str) -> list[dict]:
    return [{"url": u, "title": f"Title for {u}",
             "content": f"Snippet about {u}",
             "engine": "duckduckgo"} for u in urls]


def test_no_queries_yaml_short_circuits(tmp_workspace):
    ensure_project_skeleton("acme", "digital-platform")
    r = searxng.run_for_project("acme", "digital-platform")
    assert r["skipped"] is True


def test_run_ingests_new_results(tmp_workspace):
    _seed_queries()
    with patch.object(searxng, "_searxng_search", side_effect=[
        _fake_results("https://news.example.com/a", "https://news.example.com/b"),
        _fake_results("https://news.example.com/c"),
    ]):
        r = searxng.run_for_project("acme", "digital-platform")
    assert r["ingested"] == 3
    assert r["deduped"] == 0
    evs = list(events_dir("acme", "digital-platform").glob("*.md"))
    assert len(evs) == 3


def test_dedupe_on_repeat_urls(tmp_workspace):
    _seed_queries()
    with patch.object(searxng, "_searxng_search",
                      return_value=_fake_results("https://news.example.com/a")):
        r1 = searxng.run_for_project("acme", "digital-platform")
        r2 = searxng.run_for_project("acme", "digital-platform")
    assert r1["ingested"] == 1
    # 2 queries × 1 result = 2 attempts; first run dedupes 1 (same URL across both
    # queries within the same run), second run dedupes both.
    assert r2["ingested"] == 0
    assert r2["deduped"] >= 1


def test_search_error_recorded_not_raised(tmp_workspace):
    _seed_queries()
    with patch.object(searxng, "_searxng_search",
                      side_effect=RuntimeError("upstream down")):
        r = searxng.run_for_project("acme", "digital-platform")
    assert r["ingested"] == 0
    assert len(r["errors"]) == 2
    assert "upstream down" in r["errors"][0]


def test_run_for_all_walks_vault(tmp_workspace):
    _seed_queries("acme", "digital-platform")
    _seed_queries("contoso", "ai-rollout")
    with patch.object(searxng, "_searxng_search", return_value=[]):
        results = searxng.run_for_all()
    slugs = {(r["client"], r["project"]) for r in results}
    assert ("acme", "digital-platform") in slugs
    assert ("contoso", "ai-rollout") in slugs
