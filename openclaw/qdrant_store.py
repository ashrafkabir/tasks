"""OC-008 — Qdrant wrapper. Per-client collection isolation.

Uses qdrant-client in embedded persistent mode (`path=...`) by default — no
running Qdrant server required for the slice. Set OPENCLAW_QDRANT_URL to point
at a running OSS server when scaling out.
"""
from __future__ import annotations
import uuid
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue,
)
from .config import get_settings


def collection_name(client: str) -> str:
    """One Qdrant collection per client, plus 'shared' for cross-engagement notes."""
    if client == "shared":
        return "shared"
    return f"client_{client}"


def _client() -> QdrantClient:
    s = get_settings()
    if s.OPENCLAW_QDRANT_URL:
        return QdrantClient(url=s.OPENCLAW_QDRANT_URL)
    s.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(s.qdrant_path))


def ensure_collection(client_slug: str, dim: int) -> None:
    name = collection_name(client_slug)
    qc = _client()
    try:
        qc.get_collection(name)
    except Exception:
        qc.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    finally:
        qc.close()


def upsert_points(
    client_slug: str,
    items: list[tuple[str, list[float], dict]],
) -> int:
    """items: list of (external_id, vector, payload). Returns count upserted."""
    if not items:
        return 0
    name = collection_name(client_slug)
    qc = _client()
    try:
        points = []
        for ext_id, vec, payload in items:
            payload = {**payload, "_ext_id": ext_id, "_client": client_slug}
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{client_slug}:{ext_id}"))
            points.append(PointStruct(id=pid, vector=vec, payload=payload))
        qc.upsert(collection_name=name, points=points)
        return len(points)
    finally:
        qc.close()


def search(
    client_slug: str,
    query_vec: list[float],
    limit: int = 8,
) -> list[dict]:
    """Search the per-client collection. Hard filter on _client to prevent leakage."""
    name = collection_name(client_slug)
    qc = _client()
    try:
        flt = Filter(must=[FieldCondition(key="_client", match=MatchValue(value=client_slug))])
        result = qc.query_points(
            collection_name=name,
            query=query_vec,
            query_filter=flt,
            limit=limit,
            with_payload=True,
        )
        return [{"score": h.score, "payload": h.payload} for h in result.points]
    finally:
        qc.close()


def reset_for_tests() -> None:
    """Wipe the embedded Qdrant data dir."""
    import shutil
    s = get_settings()
    if s.qdrant_path.exists():
        shutil.rmtree(s.qdrant_path)
