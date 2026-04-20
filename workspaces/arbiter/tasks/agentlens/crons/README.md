# crons/
Per-task cron fragments. Drop `*.cron` files here (plain crontab
syntax, no SHELL/PATH headers), then run:

  ../../../shared/skills/memory-optimizer/cron/install-task-cron.sh "/home/aifactory/automate/openclaw-v2/workspaces/arbiter/tasks/agentlens"

They install under a task-specific marker block so uninstalling this
task only removes this task's jobs.
