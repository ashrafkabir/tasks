#!/usr/bin/env bash
# OC-023 — Run the Telegram polling bridge in the foreground.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN is empty. Set it in .env (from @BotFather)." >&2
  exit 1
fi

exec .venv/bin/python -m openclaw.bridges.telegram
