#!/usr/bin/env bash
# OC-026 — Launch wuzapi (OSS WhatsApp Web bridge).
#
# wuzapi is a Go service that wraps `whatsmeow`. We run it in Docker by default
# because that's the maintainer's recommended path.
#
# After it's running:
#   1. Open http://127.0.0.1:8089/api/   for the API console
#   2. POST /admin/users to create a user (returns a token; copy to WUZAPI_TOKEN)
#   3. GET /session/connect?token=...    triggers QR; scan with WhatsApp on phone
#   4. POST /webhook with our bridge URL: http://127.0.0.1:8090/bridges/wa/webhook
#
# Repo: https://github.com/asternic/wuzapi  (MIT)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

PORT="${WUZAPI_PORT:-8089}"
DATA_DIR="${WUZAPI_DATA_DIR:-$(pwd)/data/wuzapi}"
mkdir -p "$DATA_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not installed. Install Docker or build wuzapi from source:" >&2
  echo "  git clone https://github.com/asternic/wuzapi && cd wuzapi && go build" >&2
  exit 1
fi

# Pull-and-run idempotently. --rm so it cleans up; --restart=no for foreground.
exec docker run --rm \
  --name openclaw-wuzapi \
  -p "127.0.0.1:${PORT}:8080" \
  -v "${DATA_DIR}:/app/dbdata" \
  -e WUZAPI_ADMIN_TOKEN="${WUZAPI_ADMIN_TOKEN:-change-me-admin-token}" \
  -e TZ="${TZ:-UTC}" \
  asternic/wuzapi:latest
