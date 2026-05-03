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

## 2026-05-03 — Bridges: Telegram (raw HTTP) + WhatsApp via wuzapi (OSS)

**Telegram (OC-023):** raw httpx against Bot API `getUpdates` polling — avoids
adding a third-party Telegram SDK to the dependency tree. Outbound via
`sendMessage`. Operator chat id (`TELEGRAM_OPERATOR_CHAT_ID`) gates slash
commands `/ticket`, `/run`, `/approve`, `/status`.

**WhatsApp (OC-026):** wuzapi (https://github.com/asternic/wuzapi, MIT) — Go
REST/webhook wrapper around `whatsmeow`. Same architectural shape as
llama-server: a local HTTP service this Python process talks to. wuzapi runs
via `make wuzapi` (Docker by default). Inbound webhooks land at our FastAPI
server `bridges/server.py` on port 8090. Outbound via wuzapi `/chat/send/text`.

**TOS caveat (logged for future-me):** any non-Cloud-API WhatsApp library
uses the WA Web protocol — formally a grey area in WA's TOS for automation.
Standard practice for personal/operator-only use. If WA ever escalates this
posture, swap OC-026 to the sanctioned Cloud API path (Meta business account
needed; free tier exists).

**Shared ingest pipeline (OC-022b):** both bridges feed `openclaw.ingest`,
which writes the event MD, records SQLite, embeds into Qdrant, and applies
spawn rules. `/ticket <kind> <title>` is the only auto-spawn rule (operator
keeps control). Routing via `vault/shared/chat_routes.yaml` with env defaults.

**Outbound notify (`openclaw.notify`):** kanban transitions to
`awaiting_approval` automatically broadcast to all configured channels.
`OPENCLAW_NOTIFY_MODE=stub` (default) records to a session-local sink so
tests stay offline; `live` attempts real sends and never raises on failure.

## 2026-05-03 — Qdrant embedded mode for the slice

`qdrant-client` is used in local persistent mode (`QdrantClient(path=...)`).
No Qdrant server is required for the slice. Setting `OPENCLAW_QDRANT_URL`
switches to a running OSS server when scaled out. Both code paths are OSS and
free.
