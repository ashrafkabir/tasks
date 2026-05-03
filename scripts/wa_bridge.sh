#!/usr/bin/env bash
# OC-026 — Run the bridge HTTP server (receives wuzapi WhatsApp webhooks).
# Outbound sends are direct REST calls from openclaw.notify; this server
# only handles inbound webhooks.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

exec .venv/bin/python -m openclaw.bridges.server
