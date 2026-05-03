#!/usr/bin/env bash
# OC-002 — Launch the chat llama-server (gemma-4-26B-A4B-it).
# Reads paths from .env (or env vars). Foreground process.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

LLAMA_BIN="${LLAMA_BIN:-/home/aifactory/llama.cpp/llama-b8770/llama-server}"
LLAMA_CHAT_MODEL="${LLAMA_CHAT_MODEL:-/home/aifactory/models/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf}"
PORT="${LLAMA_CHAT_PORT:-8080}"
CTX="${LLAMA_CHAT_CTX:-8192}"
THREADS="${LLAMA_CHAT_THREADS:-$(nproc)}"

if [ ! -x "$LLAMA_BIN" ]; then
  echo "ERROR: llama-server not found at $LLAMA_BIN" >&2
  exit 1
fi
if [ ! -f "$LLAMA_CHAT_MODEL" ]; then
  echo "ERROR: chat model not found at $LLAMA_CHAT_MODEL" >&2
  exit 1
fi

echo "[chat] $LLAMA_BIN -m $LLAMA_CHAT_MODEL --port $PORT -c $CTX -t $THREADS"
exec "$LLAMA_BIN" \
  -m "$LLAMA_CHAT_MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  -c "$CTX" \
  -t "$THREADS" \
  --jinja \
  --alias gemma-4-26B-A4B-it
