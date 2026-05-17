# Consilo — System PRD (one page)

**Status:** Draft v0.1 — pending user review
**Date:** 2026-05-03
**Owner:** Ashraf Kabir (Visionet CxO consulting)

## 1. Purpose
A fully local, zero-recurring-cost agentic operating system that supports CxO-facing
consulting work: monitor client developments, generate and prioritize work, draft
executive artifacts (decks, briefings, talking points), preserve client/project memory,
and expose a full audit trail. The system reduces time-to-first-draft and prevents loss
of context between engagements while keeping every byte of client material on Ashraf's
machine.

## 2. Users and surfaces
- **Primary user:** Ashraf (operator, reviewer, approver).
- **Surfaces:**
  - Local web dashboard (FastAPI + HTMX/Alpine/Tailwind), accessed remotely via
    Cloudflared Tunnel + Cloudflare Access (free tier).
  - Chat ingress over Telegram Bot API and WhatsApp Cloud API (free tier).
  - Markdown vault (Obsidian-compatible) as the human-readable source of truth.
  - GitHub private repo (per-project branches) as version control / artifact history.

## 3. Hard constraints (non-negotiable)
- No paid APIs, no cloud LLMs, no hosted memory services.
- No outbound third-party LLM calls. Local inference only.
- No compaction-based long-context behavior — agents clear and reload from durable
  memory every run.
- No cross-client leakage — strict per-client memory + filesystem isolation.
- No irreversible action without explicit human approval.
- If a design choice forces a paid dependency, **stop and ask**.

## 4. Local stack (locked)
| Concern | Choice |
|---|---|
| LLM runtime | llama.cpp `llama-server` (OpenAI-compatible HTTP) |
| Main model | `gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` |
| Embeddings | second `llama-server` instance (local embedding model, TBD) |
| Vector store | Qdrant OSS (local, Docker) |
| Event log / episodic | SQLite |
| Source-of-truth docs | Markdown vault (Obsidian layout) |
| Web search | SearXNG self-hosted |
| Remote dashboard access | Cloudflared Tunnel + Cloudflare Access (free) |
| Chat | Telegram Bot API + WhatsApp Cloud API (free tier) |
| VCS | GitHub private repo |
| Orchestration wrapper | Consilo (local agentic framework) |
| Service runtime | Docker Compose |
| Backend lang | Python (FastAPI) |
| Frontend | HTMX + Alpine + Tailwind |

## 5. Architecture summary
```
                  ┌──────────────────────────────────────────┐
                  │            Markdown vault                │
                  │  (vault/shared/, vault/clients/<c>/<p>/) │
                  └──────────────────────────────────────────┘
                              ▲                  ▲
                              │ writes           │ reads
        ┌─────────────────────┴─────┐    ┌───────┴────────────────────┐
        │       Orchestrator        │    │   Agents (per role)        │
        │  (Consilo, FastAPI)      │◄──►│  Implementer, Reviewer,    │
        │  Kanban + tickets + audit │    │  Memory-Curator, Briefer   │
        └────────┬───────────┬──────┘    └─────────┬──────────────────┘
                 │           │                      │
       ┌─────────▼──┐  ┌─────▼──────┐    ┌──────────▼──────────┐
       │  SQLite    │  │  Qdrant    │    │  llama-server       │
       │ events,    │  │ semantic   │    │  (chat + embed)     │
       │ tickets,   │  │  memory    │    │  OpenAI-compatible  │
       │ audit      │  │ per-client │    │                     │
       └────────────┘  └────────────┘    └─────────────────────┘
                 ▲           ▲                      ▲
                 │           │                      │
         ┌───────┴───────────┴──────────────────────┴────────┐
         │  Ingress: dashboard (HTMX), Telegram, WhatsApp,   │
         │  SearXNG, GitHub sync                             │
         └────────────────────────────────────────────────────┘
```

## 6. Memory model (clear-and-reload)
- **Episodic / event log:** SQLite — every event, ticket transition, agent run, tool
  call, model output excerpt.
- **Semantic memory:** Qdrant — per-client isolated collection (`client_<slug>`) +
  shared collection (`shared`). Embeddings produced by the local embedding `llama-server`.
- **Source of truth:** markdown vault. Memory services index *from* the vault; the vault
  is never derived from Qdrant.
- **No compaction.** Each agent run starts cold: pulls a curated context bundle from
  vault + Qdrant + SQLite based on the active ticket, then exits. Long-context drift
  is prevented by design.

## 7. Vault layout (assumption — confirm)
```
consilo/
├── vault/
│   ├── shared/
│   │   ├── system_prd.md
│   │   ├── DECISIONS.md
│   │   ├── COSTS.md
│   │   └── MODEL_NOTES.md
│   └── clients/
│       └── <client-slug>/
│           ├── client.yaml          # stable client profile
│           ├── projects/
│           │   └── <project-slug>/
│           │       ├── project.yaml
│           │       ├── kanban/
│           │       │   ├── backlog/
│           │       │   ├── in_progress/
│           │       │   ├── awaiting_approval/
│           │       │   ├── approved/
│           │       │   └── done/
│           │       ├── events/      # raw signals (news, mail, call notes)
│           │       ├── briefs/
│           │       ├── artifacts/
│           │       │   └── decks/
│           │       └── audit/       # per-run traces
│           └── memory/              # per-client extracted facts (markdown)
└── ...
```
> Assumption flag: I inferred this from the visible spec mentioning
> `vault/shared/system_prd.md`, `vault/clients/<client>/`, `awaiting_approval/`,
> and `artifacts/decks/`. Please confirm or correct the elided sections.

## 8. Agent roles (initial set)
- **Implementer** — picks a ticket, drafts the artifact, writes to `in_progress/`.
- **Reviewer** — critiques the draft against ticket acceptance criteria + client
  context, returns a structured suggestion list.
- **Memory-Curator** — extracts durable facts from new events into per-client memory
  files, embeds into Qdrant.
- **Briefer** — synthesizes a CxO-ready briefing or deck outline with speaker notes.
- All agents share an OpenAI-compatible client pointed at local `llama-server`.

## 9. Approval gates and audit
- Every meaningful artifact transitions `in_progress → awaiting_approval` and waits
  for explicit human approval before `approved → done`.
- Every agent run writes a structured audit record (JSON) under
  `audit/<ticket-id>/<run-id>.json` capturing: prompts, retrieved context refs,
  model outputs, tool calls, decisions, timestamps.
- Every approved transition is committed to the project branch in the tasks repo.

## 10. Communication
- Inbound: Telegram + WhatsApp messages routed through a chat bridge that creates
  events tagged to the active client/project context.
- Outbound: dashboard cards + chat pings on `awaiting_approval` transitions.
- All chat traffic logged to SQLite and the per-project audit trail.

## 11. Out of scope (v1)
- Multi-user / team mode.
- Mobile native apps (chat + dashboard PWA cover this).
- Direct integrations to client SaaS (Salesforce, etc.) — defer to manual paste +
  scheduled SearXNG monitoring in v1.
- Auto-sending external messages without approval.

## 12. Success criteria
- First proving slice runs end-to-end (see `docs/VERTICAL_SLICE.md`) with all
  artifacts present, audit captured, and a clean GitHub commit.
- Two real client engagements onboarded into the vault with non-leaking memory.
- < 2 minutes from new event ingestion to ticket appearing on the Kanban board.
- 100% of approved actions traceable from artifact back to source events.
- Zero recurring cost confirmed in `COSTS.md`.

## 13. Open questions for user (before scaffolding deeper)
1. Is the vault layout in §7 correct, or do the elided sections specify something different?
2. Confirm the **embedding model** preference (e.g., `bge-m3-q5_k_m.gguf`,
   `nomic-embed-text-v1.5`)? I will pick one local default if unspecified.
3. Confirm the **tasks repo** layout — single repo per machine with branches per
   project, or one repo per client?
4. Telegram + WhatsApp: which is primary for v1? (I'll wire Telegram first if
   unspecified — simpler bot setup.)
5. Should the orchestrator run as a single Docker Compose stack from day one, or
   start as bare-Python services and dockerize later?
