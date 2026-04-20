# Task: AgentLens™️ Core

> The brief. Never rewritten after acceptance — revisions go in
> `memory/decisions/` as superseding records. Tier-1, keep under 400 tok.

## Origin
- Requested by: user (internal strategic R&D)
- Date opened: 2026-04-19 (migrated into task format 2026-04-20)
- Owning workspace: arbiter (as Ash)

## Ask
Build **AgentLens™️ Core** — an Agentic SEO/AEO Attribution Engine that
moves the measurement surface from "keyword → search rank" to
"intent → agent reasoning → brand recommendation." Brands need to know
*why* an AI agent recommended a competitor over them and which content
attributes drive the decision.

## Success criteria
### Phase 1: Foundation & PRD
- [x] PRD drafted (context/PRD.md)
- [x] Persona archetypes defined (Technical, Budget, Luxury, Ethical)
- [x] Scoring rubric defined (Presence / Reasoning / Competitive Delta)

### Phase 2: Architectural Design
- [x] System architecture design (research/design/system_architecture.md)
- [x] Database schema (research/design/database_schema.md)
- [ ] Agentic workflow orchestration design

### Phase 3: Agentic Core (4-stage loop)
- [ ] Stage I: Observer — scraping & visibility monitoring
- [ ] Stage II: Intent Engine — persona-driven query generation
- [ ] Stage III: Agentic Tester — sub-agent simulation + reasoning extraction
- [ ] Stage IV: Optimization Loop — AEO action plan generation

### Phase 4: UI & Visualization
- [ ] Dashboard (Next.js + Tailwind)
- [ ] Real-time intent heatmaps
- [ ] Competitor visibility matrices

## Constraints
- Reuse existing FastAPI backend at `apps/agentlens-backend/`
- Orchestration: OpenClaw `sessions_spawn`
- Web intelligence: Firecrawl + Agent Browser
- Intelligence engine: GPT-5.3 / Claude 3.5 Sonnet
- Viz: Datawrapper, Canvas, or Recharts

## Out of scope
- Public launch, pricing, GTM
- Multi-tenant auth
- Billing integration

## Deliverables (where they land)
- Drafts & reports → `outputs/`
- Code & prototypes → `apps/agentlens-backend/`, `apps/<new-app>/`
- Research notes → `research/` (design/ already populated)
- Source material user supplied → `context/` (PRD + original notes)
- Chat transcripts → `conversations/`
- Task-specific cron jobs → `crons/`
- Execution logs → `logs/`

## Links
- Progress → `PROGRESS.md`
- Index → `MEMORY.md`
- Task instructions → `AGENTS.md`
- State → `STATE.md`
