# OpenClaw

Local-first agentic OS for CxO consulting workflow. **No paid APIs, no cloud LLMs,
no hosted memory.** Runs entirely on the operator's machine.

This repository is in **Phase A** — design artifacts only, no code yet.

## Read first
- [`vault/shared/system_prd.md`](vault/shared/system_prd.md) — one-page PRD
- [`docs/BACKLOG.md`](docs/BACKLOG.md) — system-build Kanban backlog
- [`docs/VERTICAL_SLICE.md`](docs/VERTICAL_SLICE.md) — smallest end-to-end slice plan

## Status
- [x] Phase A — PRD + backlog + slice plan drafted
- [x] Phase A — user approved (AFK)
- [x] Phase B — backlog finalized (defaults adopted, see DECISIONS.md)
- [x] Phase C — P0 tickets OC-001..OC-017 implemented
- [x] Phase D — proving slice green (`make slice && make approve` succeeds; tasks repo commit on `acme/digital-platform`)

## Quick start
```bash
make bootstrap          # create venv, install package + dev deps
make slice              # seed → run-slice (implementer + reviewer + awaiting_approval)
make approve            # approve --apply → done → tasks repo commit
make test               # 47 tests, all green
make dashboard          # http://127.0.0.1:8091 — kanban + ticket detail + audit timeline
make compose-up         # qdrant + searxng + wuzapi + bridge + dashboard + worker (containers)
make worker             # background runner — drives every opted-in project's backlog
make tunnel             # bring the dashboard online over Cloudflared + Access (free tier)
```

CLI surface (`openclaw <subcommand> --help`):
- `start-task`, `compile-prd`, `approve-prd`, `autoloop`
- `run-slice`, `approve`, `status`
- `curate-memory`, `brief`
- `search-monitor`
- `replay`

## New-engagement flow

```bash
# 1. Create the project folder + answers skeleton.
openclaw start-task --client contoso --project board-pitch

# 2. Fill in vault/clients/contoso/projects/board-pitch/prd_answers.yaml
#    Either run /grillme in Claude Code (interactive interviewer skill),
#    or edit the YAML by hand.

# 3. Render the PRD from answers.
openclaw compile-prd --client contoso --project board-pitch

# 4. Approve the plan → tickets spawn into backlog → autoloop drives each
#    through implementer + reviewer → all land at awaiting_approval.
openclaw approve-prd --client contoso --project board-pitch --autoloop

# 5. Approve each artifact at the human gate (still required — option iii).
openclaw approve OC-T-001 --client contoso --project board-pitch --apply
openclaw approve OC-T-002 --client contoso --project board-pitch --apply
```

The `autoloop` only drives `backlog → awaiting_approval`. The final
`approve` step that promotes a draft to an artifact and commits to the
tasks repo remains human-gated, per `DECISIONS.md`.

By default, the slice runs in `OPENCLAW_LLM_MODE=stub` (deterministic local
responder) so it works without a llama-server up. See `vault/shared/MODEL_NOTES.md`
for the live-mode steps.

## Ops console + background worker

`http://127.0.0.1:8091/ops` is a single-screen live view:
- **Health strip** — green/red dots for llama-chat (:8080), llama-embed (:8081),
  qdrant (if `OPENCLAW_QDRANT_URL` set), bridge server (:8090), searxng (:8888).
- **Queue totals** — backlog / in_progress / awaiting_approval / approved / done,
  aggregated across all engagements.
- **Workers** — live heartbeats from background `openclaw worker` instances.
- **Activity feed** — unified stream of events, agent runs, and approvals.
- **Engagements** — every (client, project) with state counts.

Auto-refreshes every 5 seconds via HTMX. Also exposes JSON endpoints
`/ops/health.json` and `/ops/feed.json` if you want to scrape it.

The background **worker** (`make worker` or via Compose) ticks every N seconds
and runs autoloop on any project that:
1. has `prd.approved.md` present, AND
2. is opted in either via `autoloop_enabled: true` in `project.yaml`, or by
   appearing in `vault/shared/worker.yaml` (see `worker.example.yaml`).

It never auto-approves — every artifact still lands at `awaiting_approval`
for the human gate.

## Memory curation (OC-021)

Inbound chat messages and other events accumulate in
`vault/clients/<client>/projects/<project>/events/`. The Memory-Curator
distills them into durable per-client facts:

```bash
openclaw curate-memory --client acme
# or                  --client acme --project digital-platform
# or                  --client acme --since 2026-04-01T00:00:00Z
```

Output:
- `vault/clients/<client>/memory.md` — append-only, one section per run, one
  bullet per fact (subject, claim, confidence, evidence event id, tags).
- Qdrant `client_<slug>` collection — each fact embedded as a `memory_fact`
  point so the context bundler surfaces them in future agent runs.
- `vault/shared/_curation/<client>/<run-id>.json` — full audit trail.
- SQLite `curated_events` row per processed event.

Idempotent: re-running with no new events is a no-op.

## Dashboard

`make dashboard` boots a FastAPI + HTMX UI on `http://127.0.0.1:8091`:

- **Engagements** (`/`) — one row per (client, project), with state counts.
- **Board** (`/board?client=…&project=…`) — kanban columns; auto-refreshes every 10s.
- **Ticket detail** (`/tickets/{id}?client=…&project=…`):
  - **Run slice** button — implementer + reviewer + transition to awaiting_approval.
  - **Approve** button (with "apply suggestions" toggle) — promotes draft to artifact, commits to project branch.
  - **Audit timeline** — every run with click-to-inspect raw JSON.

UI assets (Tailwind, HTMX, Alpine) load from CDN. Behind a Cloudflared Tunnel
+ Cloudflare Access for remote use (OC-028, deferred).

## Chat bridges (Telegram + WhatsApp)

Both bridges share one ingest pipeline (`openclaw.ingest`). Inbound messages
become events in the vault; `/ticket <kind> <title>` from the operator chat
spawns a ticket. Slash commands: `/ticket`, `/run`, `/approve`, `/status`.

Outbound: when a ticket transitions to `awaiting_approval`, `openclaw.notify`
broadcasts to all configured operator channels. Default
`OPENCLAW_NOTIFY_MODE=stub` keeps things offline; flip to `live` once tokens
are set.

```bash
# Telegram (OC-023) — set TELEGRAM_BOT_TOKEN + TELEGRAM_OPERATOR_CHAT_ID in .env
make telegram-bridge

# WhatsApp via wuzapi (OC-026) — needs Docker (or wuzapi Go binary)
make wuzapi              # terminal 1: launch wuzapi (asternic/wuzapi, MIT)
# (one-time) hit http://127.0.0.1:8089/api/  → POST /admin/users → copy token to WUZAPI_TOKEN
# (one-time) GET /session/connect           → scan QR with WhatsApp on phone
# (one-time) point wuzapi webhook → http://127.0.0.1:8090/bridges/wa/webhook
make wa-bridge           # terminal 2: FastAPI server that receives wuzapi webhooks
```

Routing chats → (client, project): edit `vault/shared/chat_routes.yaml` (see
`chat_routes.example.yaml`). If no match and no env default, events land in
`vault/clients/_unrouted/`.
