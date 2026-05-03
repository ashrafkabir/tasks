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
make test               # 16 tests, all green
```

By default, the slice runs in `OPENCLAW_LLM_MODE=stub` (deterministic local
responder) so it works without a llama-server up. See `vault/shared/MODEL_NOTES.md`
for the live-mode steps.

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
