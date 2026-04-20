# Task: AgentLens™️ Core

> Tier-1 file. Target 400 tok, ceiling 600. Orientation only.
> Detail belongs in `memory/` and `research/` where QMD can find it.

## Goal
Ship an Agentic SEO/AEO Attribution Engine (4-stage loop: Observer →
Intent Engine → Agentic Tester → Optimization Loop) with a dashboard
for visualizing brand visibility and competitive reasoning gaps.

## Scope in / out
- **In**: FastAPI backend (already seeded under apps/agentlens-backend/),
  4-stage agentic loop, persona-driven query generation, scoring rubric
  implementation, dashboard UI, visualization.
- **Out**: GTM/pricing, public launch, multi-tenant auth, billing.

## Active constraints
- Phase 1 ✅ and most of Phase 2 ✅ (see TASK.md checkboxes).
- Reuse the existing FastAPI backend; don't rewrite.
- Orchestration must use OpenClaw `sessions_spawn`.
- Web intel: Firecrawl + Agent Browser; Intelligence: GPT-5.3 / Claude 3.5.
- See `context/PRD.md` for the full spec.

## Current focus
Designing the agentic workflow orchestration (last remaining Phase 2
checkbox) before cutting into Phase 3 Stage I Observer.

## Autonomy
Hourly tick drives this task. Set `STATE.md status: stopped` or tell
Ash "stop task agentlens" to halt. Milestones (checkbox flip or
`milestone:` in PROGRESS) run tests + evals and commit to
`task/agentlens` on pass.

## Related
- Brief → `TASK.md`
- Progress log → `PROGRESS.md`
- State → `STATE.md`
- Task index → `MEMORY.md`
- Spec → `context/PRD.md`
- Design → `research/design/`
- Backend → `apps/agentlens-backend/`

---
Created: 2026-04-19 (migrated 2026-04-20)
Owner: Ash (arbiter)
