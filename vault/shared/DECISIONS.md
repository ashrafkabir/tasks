# OpenClaw — Decisions log

Append-only. Each entry: date, decision, rationale, alternatives considered.

---

## 2026-05-03 — Phase A defaults adopted (AFK proceed)

User approved AFK build of OC-001..OC-017 without answering the PRD §13 open
questions. Defaults locked:

| # | Question | Default chosen | Rationale |
|---|---|---|---|
| 1 | Vault layout | PRD §7 as drafted | Best-fit inference from visible spec; revisit if elided spec differs |
| 2 | Embedding model | `bge-m3` GGUF (configurable) | Strong multilingual, runs comfortably on CPU/GPU via llama.cpp |
| 3 | Tasks repo | Single `tasks/` repo, branch per project (`<client>/<project>`) | Simpler ops; cross-engagement audit search trivial |
| 4 | Primary chat | Telegram first (P1) | Bot setup simpler than WhatsApp Cloud API; v1 slice is CLI only anyway |
| 5 | Compose | Bare processes first, container at OC-025 | Avoids Docker dependency on the proving slice |

## 2026-05-03 — Stub LLM mode for proving slice

The proving slice runs in `OPENCLAW_LLM_MODE=stub` by default, with a deterministic
local responder in `openclaw/llm.py`. Live mode talks to llama-server and is
enabled by setting `OPENCLAW_LLM_MODE=live` plus starting `make llama-chat`.

Why: lets the slice prove plumbing (vault → context bundle → agent run → audit →
approval gate → git commit) without depending on a model load. Stub responses are
plainly tagged in the audit trace ("llm_mode": "stub"), so they cannot be confused
with live output downstream.

## 2026-05-03 — Qdrant embedded mode for the slice

`qdrant-client` is used in local persistent mode (`QdrantClient(path=...)`).
No Qdrant server is required for the slice. Setting `OPENCLAW_QDRANT_URL`
switches to a running OSS server when scaled out. Both code paths are OSS and
free.
