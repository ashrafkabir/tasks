#!/usr/bin/env bash
# OC-004 — Smoke test: chat server + embed server reachable.
set -uo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

CHAT_URL="${CONSILO_LLM_BASE_URL:-http://127.0.0.1:8080/v1}"
EMB_URL="${CONSILO_EMBED_BASE_URL:-http://127.0.0.1:8081/v1}"

ok=0; fail=0
check() {
  local name="$1" url="$2"
  if curl --silent --fail --max-time 3 -o /dev/null "$url/models"; then
    echo "[ok]   $name $url"; ok=$((ok+1))
  else
    echo "[FAIL] $name $url"; fail=$((fail+1))
  fi
}

check "chat " "$CHAT_URL"
check "embed" "$EMB_URL"

echo "---"
echo "$ok ok / $fail fail"
exit $fail
