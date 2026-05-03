#!/usr/bin/env bash
# OC-003 — Launch the embeddings llama-server (bge-m3 by default).
# Foreground. Embeddings endpoint is OpenAI-compatible: POST /v1/embeddings
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

LLAMA_BIN="${LLAMA_BIN:-/home/aifactory/llama.cpp/llama-b8770/llama-server}"
LLAMA_EMBED_MODEL="${LLAMA_EMBED_MODEL:-/home/aifactory/models/bge-m3-q4_k_m.gguf}"
PORT="${LLAMA_EMBED_PORT:-8081}"
CTX="${LLAMA_EMBED_CTX:-512}"
THREADS="${LLAMA_EMBED_THREADS:-$(nproc)}"

if [ ! -x "$LLAMA_BIN" ]; then
  echo "ERROR: llama-server not found at $LLAMA_BIN" >&2
  exit 1
fi
if [ ! -f "$LLAMA_EMBED_MODEL" ]; then
  echo "ERROR: embed model not found at $LLAMA_EMBED_MODEL" >&2
  echo "       download e.g. bge-m3 GGUF, then set LLAMA_EMBED_MODEL in .env" >&2
  exit 1
fi

echo "[embed] $LLAMA_BIN -m $LLAMA_EMBED_MODEL --port $PORT --embeddings"
exec "$LLAMA_BIN" \
  -m "$LLAMA_EMBED_MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  -c "$CTX" \
  -t "$THREADS" \
  --embeddings \
  --alias bge-m3
