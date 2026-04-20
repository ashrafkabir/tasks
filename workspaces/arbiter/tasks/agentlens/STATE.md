---
task: AgentLens
slug: agentlens
status: active
branch: task/agentlens
started: 2026-04-20
stopped_at: null
completed_at: null
stop_reason: null
---

# State

The hourly tick reads this file. Set `status:` to one of:

- `active` — Ash continues advancing the task each tick
- `paused` — tick is a no-op; resume by setting active
- `stopped` — Ash halts; tick will unregister itself on next run
- `completed` — all objectives met; tick self-removes

When the user instructs "stop task <slug>", Ash sets `status: stopped`
and `stop_reason: <reason>` here, then the next tick cleans up the
cron registration via `unregister-task-tick.py`.
