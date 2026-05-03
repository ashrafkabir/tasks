# OpenClaw — Smallest vertical slice plan

**Goal:** prove the loop end-to-end with the minimum surface area. Everything below
is required by the user spec for the first proving slice. Anything not listed is
explicitly deferred.

## What it must demonstrate
1. one client (`vault/clients/acme/`)
2. one project (`vault/clients/acme/projects/digital-platform/`)
3. one synthetic event (`events/2026-05-03-quarterly-letter.md`)
4. one spawned ticket (Kanban `backlog/OC-T-001.md`)
5. one Implementer run → artifact draft
6. one Reviewer run → suggestion list
7. one suggestion captured in audit
8. one approval gate (manual `openclaw approve OC-T-001`)
9. one deck-outline artifact with speaker notes
   (`artifacts/decks/2026-05-03-acme-board-readout.md`)
10. one audit trace (`audit/OC-T-001/<run-id>.json`)
11. one commit to the project branch in the tasks repo

## Non-goals for the slice
- No dashboard UI yet (CLI only — FastAPI/HTMX comes in P1).
- No Telegram/WhatsApp bridges (P1).
- No Memory-Curator (P1).
- No SearXNG monitor (P2).
- No Cloudflared tunnel (P2).
- No Docker Compose required to pass the slice — bare processes are fine; we
  containerize in OC-025.

## Slice flow (one screen)
```
[seed.py]                      → writes synthetic event into vault
   │
   ▼
[openclaw run-slice]
   │
   ├── load-context (cold)     ← reads client.yaml, project.yaml, event.md
   │                             + Qdrant nearest 8, + SQLite recent 20
   │
   ├── implementer.run         → drafts deck outline w/ speaker notes
   │                             writes in_progress/OC-T-001/draft.md
   │                             writes audit/OC-T-001/<run>.json
   │
   ├── reviewer.run            → structured suggestions
   │                             appends audit/OC-T-001/<run>.json
   │
   ├── transition → awaiting_approval (move ticket file)
   │
   └── prints: "approve with: openclaw approve OC-T-001"
        │
        ▼
[openclaw approve OC-T-001]
   │
   ├── apply suggestions? (y/N)  ← human gate
   ├── transition → approved → done
   ├── promote draft → artifacts/decks/<slug>.md
   └── git commit on project branch
```

## Files the slice will create (target tree)
```
openclaw/
├── pyproject.toml
├── Makefile
├── .env.example
├── scripts/
│   ├── llama_chat_server.sh
│   ├── llama_embed_server.sh
│   └── healthz.sh
├── openclaw/                           # python package
│   ├── __init__.py
│   ├── cli.py                          # `openclaw` entrypoint
│   ├── config.py
│   ├── llm.py                          # OpenAI-compat client → llama-server
│   ├── embed.py
│   ├── qdrant_client.py
│   ├── sqlite_store.py
│   ├── vault.py                        # vault read/write helpers
│   ├── kanban.py                       # ticket state machine on filesystem
│   ├── audit.py
│   ├── context.py                      # cold-start bundle assembler
│   └── agents/
│       ├── implementer.py
│       └── reviewer.py
├── seed/
│   └── seed_acme.py                    # synthetic client+project+event
├── tests/
│   ├── test_kanban_transitions.py
│   ├── test_collection_isolation.py
│   └── test_slice_smoke.py
└── vault/                              # already created
    ├── shared/{system_prd,DECISIONS,COSTS,MODEL_NOTES}.md
    └── clients/                        # populated by seed
```

## Acceptance for the slice
- `make slice` (or `openclaw run-slice && openclaw approve OC-T-001`) completes with
  exit 0 on a clean machine after `make bootstrap`.
- `git log` on project branch shows the approval commit with the artifact diff.
- `audit/OC-T-001/` contains ≥ 2 run JSONs (implementer + reviewer) and the
  approval record.
- `tests/test_collection_isolation.py` proves Qdrant queries on `client_acme`
  cannot return points from another client's collection.
- `vault/shared/COSTS.md` reflects $0 recurring cost.

## Estimated effort
- P0 (this slice) ≈ 17 tickets, sized for 1–3 hour increments each.
- Suggested cadence: 2–3 tickets per session with a pause-for-review between
  each meaningful one (per Phase C).
