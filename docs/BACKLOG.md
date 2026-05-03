# OpenClaw — System-build Kanban backlog (v0.1)

Tickets to **build the system itself**. Each ticket is small enough to land in one
focused implementation pass. IDs follow `OC-NNN`. Priority: P0 = blocks vertical
slice, P1 = first useful surface, P2 = polish/scale.

## Epics
- **E1 — Foundation:** repo, env, llama-server, model, healthchecks.
- **E2 — Vault & schema:** directory layout, YAML schemas, validators.
- **E3 — Memory:** SQLite event log, Qdrant collections, embedding service,
  ingest pipeline.
- **E4 — Orchestrator:** OpenClaw wrapper, ticket lifecycle, agent runner, audit.
- **E5 — Agents:** Implementer, Reviewer, Memory-Curator, Briefer.
- **E6 — Dashboard:** FastAPI + HTMX board, ticket views, approval UI.
- **E7 — Ingress:** Telegram bridge, WhatsApp bridge, SearXNG monitor.
- **E8 — Sync & ops:** GitHub commit hook, Cloudflared exposure, bootstrap scripts.

## Backlog (ordered)

### P0 — required for the proving slice
| ID | Epic | Title |
|---|---|---|
| OC-001 | E1 | Bootstrap repo + `.env.example` + `pyproject.toml` + `Makefile` |
| OC-002 | E1 | Local `llama-server` launch script for chat (gemma-4-26B) |
| OC-003 | E1 | Local `llama-server` launch script for embeddings |
| OC-004 | E1 | `/healthz` smoke script that pings both servers + Qdrant |
| OC-005 | E2 | Vault layout + `client.yaml` / `project.yaml` schemas + validator |
| OC-006 | E2 | Synthetic seed: one client, one project, one event |
| OC-007 | E3 | SQLite schema + migrations (events, tickets, runs, audit) |
| OC-008 | E3 | Qdrant local container + per-client collection helpers |
| OC-009 | E3 | Embedding client (OpenAI-compat) + batch upsert from vault events |
| OC-010 | E4 | OpenClaw wrapper: ticket model, transitions, file-backed kanban |
| OC-011 | E4 | Agent runner: cold-start context bundle (vault + Qdrant + SQLite) |
| OC-012 | E4 | Audit writer: per-run JSON trace |
| OC-013 | E5 | Implementer agent (deck-outline artifact w/ speaker notes) |
| OC-014 | E5 | Reviewer agent (structured suggestion list) |
| OC-015 | E4 | Approval gate: CLI `approve` command + state transition |
| OC-016 | E8 | GitHub commit on approval (project branch) |
| OC-017 | E4 | End-to-end CLI driver: `openclaw run-slice` |

### P1 — first useful surface
| ID | Epic | Title | Status |
|---|---|---|---|
| OC-018 | E6 | FastAPI skeleton + HTMX board route | pending |
| OC-019 | E6 | Ticket detail view + approval button | pending |
| OC-020 | E6 | Audit timeline view | pending |
| OC-021 | E5 | Memory-Curator agent (extract facts → per-client memory.md + Qdrant) | pending |
| OC-022 | E5 | Briefer agent (CxO briefing markdown) | pending |
| OC-022b | E7 | Shared ingest pipeline (event MD + SQLite + Qdrant + spawn rules) | **done** |
| OC-023 | E7 | Telegram bridge (polling inbound + REST outbound) | **done** |
| OC-024 | E3 | Cross-client leakage tests (collection-isolation invariants) | done (in test_collection_isolation) |
| OC-025 | E8 | Docker Compose for llama-servers + Qdrant + dashboard | pending |

### P2 — polish / scale
| ID | Epic | Title | Status |
|---|---|---|---|
| OC-026 | E7 | WhatsApp bridge via wuzapi (OSS, FastAPI webhook + REST send) | **done** |
| OC-027 | E7 | SearXNG monitor scheduler (per-client query packs) | pending |
| OC-028 | E8 | Cloudflared Tunnel + Cloudflare Access front for dashboard | pending |
| OC-029 | E6 | Per-client filter + memory inspector | pending |
| OC-030 | E4 | Replay tool: re-run an audit trace deterministically | pending |

## Dependency graph (textual)
```
OC-001 ──► OC-002 ──┐
       ──► OC-003 ──┼──► OC-004
                    │
OC-001 ──► OC-005 ──► OC-006
       ──► OC-007 ──┐
                    ├──► OC-010 ──► OC-011 ──► OC-013 ──► OC-014
OC-008 ──► OC-009 ──┘                                 │
                                                      ▼
                                               OC-015 ──► OC-016 ──► OC-017
```
**Critical path to proving slice:** 001 → 005 → 006 → 007 → 008 → 009 → 010 → 011
→ 012 → 013 → 014 → 015 → 016 → 017.

## Smallest vertical slice (P0 only)
The 17 P0 tickets are the proving-slice cut. P1+ deferred until the slice runs
end-to-end, audited, and committed.
