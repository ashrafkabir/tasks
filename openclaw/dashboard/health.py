"""Probe local services for the ops console health strip.

Each probe is a quick HTTP GET with a small timeout. Failure is reported,
never raised. Results are cached for `_CACHE_TTL` seconds to avoid hammering
llama-server on a busy ops page refresh loop.
"""
from __future__ import annotations
import os
import time
from typing import Any
import httpx


_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 4.0   # seconds


def _probe(name: str, url: str, *, timeout: float = 1.5,
           expect_status: int = 200) -> dict:
    key = f"{name}:{url}"
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]
    out: dict[str, Any]
    try:
        r = httpx.get(url, timeout=timeout)
        ok = r.status_code == expect_status
        out = {"name": name, "url": url, "ok": ok, "status": r.status_code}
    except Exception as e:
        out = {"name": name, "url": url, "ok": False, "error": str(e)[:120]}
    _CACHE[key] = (now, out)
    return out


def snapshot() -> dict:
    """Probe all services that contribute to a working OpenClaw install.
    Skips Qdrant probe in embedded mode (no URL set)."""
    services: list[dict] = []
    services.append(_probe(
        "llama-chat",
        f"{os.getenv('OPENCLAW_LLM_BASE_URL', 'http://127.0.0.1:8080/v1').rstrip('/')}/models",
    ))
    services.append(_probe(
        "llama-embed",
        f"{os.getenv('OPENCLAW_EMBED_BASE_URL', 'http://127.0.0.1:8081/v1').rstrip('/')}/models",
    ))
    qurl = os.getenv("OPENCLAW_QDRANT_URL")
    if qurl:
        services.append(_probe("qdrant", f"{qurl.rstrip('/')}/healthz"))
    services.append(_probe(
        "bridge",
        f"http://127.0.0.1:{os.getenv('OPENCLAW_BRIDGE_PORT', '8090')}/healthz",
    ))
    services.append(_probe(
        "searxng",
        f"{os.getenv('SEARXNG_URL', 'http://127.0.0.1:8888').rstrip('/')}/healthz",
        expect_status=200,
    ))
    return {
        "services": services,
        "ok_count": sum(1 for s in services if s.get("ok")),
        "total": len(services),
    }
