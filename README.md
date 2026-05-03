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
make test               # 5 tests, all green
```

By default, the slice runs in `OPENCLAW_LLM_MODE=stub` (deterministic local
responder) so it works without a llama-server up. See `vault/shared/MODEL_NOTES.md`
for the live-mode steps.
