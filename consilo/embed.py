"""OC-009 — Embedding client (OpenAI-compat /v1/embeddings).

Stub mode produces a deterministic vector from a hash of the input — sufficient
to exercise upsert/search plumbing without a live embed server.
"""
from __future__ import annotations
import hashlib
import math
import struct
import httpx
from .config import get_settings


class EmbedError(Exception):
    pass


class Embedder:
    def __init__(self, settings=None):
        self.s = settings or get_settings()

    @property
    def mode(self) -> str:
        return self.s.CONSILO_EMBED_MODE.lower()

    @property
    def dim(self) -> int:
        return self.s.CONSILO_EMBED_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.mode == "stub":
            return [self._stub_vec(t) for t in texts]
        return self._live_embed(texts)

    def _live_embed(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.s.CONSILO_EMBED_BASE_URL.rstrip('/')}/embeddings"
        headers = {"Authorization": f"Bearer {self.s.CONSILO_EMBED_API_KEY}"}
        payload = {"model": self.s.CONSILO_EMBED_MODEL, "input": texts}
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=60)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise EmbedError(f"embed server call failed: {e}") from e
        data = r.json()
        return [item["embedding"] for item in data["data"]]

    def _stub_vec(self, text: str) -> list[float]:
        """Deterministic pseudo-embedding: SHA-256 stream → floats → L2-normalized."""
        d = self.dim
        out: list[float] = []
        seed = text.encode("utf-8")
        i = 0
        while len(out) < d:
            h = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
            for j in range(0, len(h), 4):
                if len(out) >= d:
                    break
                u32 = struct.unpack(">I", h[j:j+4])[0]
                out.append((u32 / 0xFFFFFFFF) * 2.0 - 1.0)
            i += 1
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        return [x / norm for x in out]
