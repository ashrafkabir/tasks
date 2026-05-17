"""Per-client Qdrant collection isolation invariant.

Two clients with overlapping content must never appear in each other's results.
"""
from __future__ import annotations
from consilo import qdrant_store
from consilo.embed import Embedder


def test_no_cross_client_leakage(tmp_workspace):
    e = Embedder()
    qdrant_store.ensure_collection("acme", e.dim)
    qdrant_store.ensure_collection("contoso", e.dim)

    payload_a = {"title": "Acme quarterly letter", "kind": "event"}
    payload_b = {"title": "Contoso quarterly letter", "kind": "event"}
    text = "quarterly shareholder letter modernization budget"
    vec = e.embed([text])[0]

    qdrant_store.upsert_points("acme", [("acme-evt-1", vec, payload_a)])
    qdrant_store.upsert_points("contoso", [("contoso-evt-1", vec, payload_b)])

    # Querying acme returns only acme.
    hits_acme = qdrant_store.search("acme", vec, limit=8)
    assert hits_acme, "expected at least one hit"
    for h in hits_acme:
        assert h["payload"]["_client"] == "acme"
        assert "Acme" in h["payload"]["title"]

    # Querying contoso returns only contoso.
    hits_contoso = qdrant_store.search("contoso", vec, limit=8)
    assert hits_contoso
    for h in hits_contoso:
        assert h["payload"]["_client"] == "contoso"
        assert "Contoso" in h["payload"]["title"]
