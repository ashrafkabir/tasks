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

## 2026-05-17 — Task lifecycle: start-task → compile-prd → approve-prd → autoloop

New meta-layer above tickets. A "task" creates a project folder, captures a
PRD, spawns the initial backlog, and runs the autoloop. Three components:

1. **`grillme` Claude Code skill** at `~/.claude/skills/grillme/SKILL.md`.
   Interactive PRD interviewer. Reads/writes the same files OpenClaw
   produces: `prd_answers.yaml` and `prd.md` in
   `vault/clients/<c>/projects/<p>/`.

2. **Headless `openclaw.agents.interviewer`** — file-driven equivalent for
   chat-bridge flows where `grillme` (Claude Code only) is not available.
   Template-only in v1; no LLM call. The user's answers go in verbatim.

3. **`openclaw.task_lifecycle`** — `start_task`, `compile_prd`,
   `approve_prd`, `autoloop`. The planner (`openclaw.agents.planner`) is a
   deterministic regex parser of the PRD's `## 8. Ticket plan (initial)`
   section. No LLM in the ticket-spawn path — keeps the contract clear.

**Autonomy policy (option iii, ratified):** the autoloop drives every
backlog ticket through `awaiting_approval` and stops. The final approval
that promotes a draft to an artifact and commits to the tasks repo is
**always human-gated**. The constraint "no irreversible action without
explicit human approval" is preserved end-to-end.

## 2026-05-04 — GitHub remote layout: nested under `task/openclaw/`

OpenClaw shares the `github.com/ashrafkabir/tasks` repo with the user's other
work (sibling branches: `task/agentlens`, `traderapp_whatsapp`). To avoid
colliding with those and to keep all OpenClaw refs grouped:

- `task/openclaw/source` — source code, mirrored from local `main`.
- `task/openclaw/<client>/<project>` — audit + artifact branch per engagement.

**Do not** create a `task/openclaw` leaf branch — it would block the
namespace for engagement branches.

For now, pushing remains manual: `git push` from the source repo, and
`git push` from each engagement's working tree under `tasks/`. A future
ticket could wire `git_sync.commit_artifact` to `git push` after each
approval if a remote is configured (gated on env to keep the slice tests
offline).

## 2026-05-04 — Memory-Curator (OC-021): client-scoped, idempotent, no auto-trigger

The curator is **explicitly invoked** (`openclaw curate-memory --client X`)
rather than auto-firing after each ingest. Reason: keeping it operator-driven
avoids spamming the LLM on every chat message and lets Ashraf batch-curate
when context warrants it.

Idempotency via the new SQLite `curated_events` table: each event id is
recorded as curated once. The same event is never re-processed.

Storage shape:
- `vault/clients/<client>/memory.md` — append-only markdown, one section per
  run. Human-readable, scannable, diffable.
- Qdrant points with `kind=memory_fact` in the per-client collection. Sit
  alongside `kind=event` points so semantic search returns both naturally.
- Audit JSON under `vault/shared/_curation/<client>/<run-id>.json` —
  client-scoped, not per-ticket, because curation is independent of any
  specific ticket.

## 2026-05-03 — Dashboard: FastAPI + Jinja2 + HTMX + Alpine + Tailwind (CDN)

**OC-018/019/020.** Single FastAPI app on `:8091`, separate from the bridges
server `:8090`, separate lifecycles. Server-rendered Jinja2 templates with
HTMX swaps for the run/approve buttons and Alpine for tiny per-row state
(audit "inspect" expanders, "apply suggestions" toggle).

UI assets via CDN (`cdn.tailwindcss.com`, `unpkg.com/htmx.org`,
`unpkg.com/alpinejs`). Local-first concern: only metadata in HTTP requests
to those CDNs from the operator's browser; nothing about clients ever leaves
the machine. Easy to vendor locally if desired.

**Service-layer extraction.** Created `openclaw.service` with `run_slice` and
`approve` so the CLI, both bridges, and the dashboard call the same code path
and produce identical audit traces. Previously the bridges duplicated the
slice logic and shelled out to the CLI for approval.

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
