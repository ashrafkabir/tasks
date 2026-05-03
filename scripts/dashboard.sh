#!/usr/bin/env bash
# OC-018/019/020 — Run the OpenClaw HTMX dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

exec .venv/bin/python -m openclaw.dashboard.server
