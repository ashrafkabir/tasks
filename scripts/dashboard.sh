#!/usr/bin/env bash
# OC-018/019/020 — Run the Consilo HTMX dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

exec .venv/bin/python -m consilo.dashboard.server
