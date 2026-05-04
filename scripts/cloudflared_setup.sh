#!/usr/bin/env bash
# OC-028 — Bring the OpenClaw dashboard online over a Cloudflared Tunnel
# fronted by Cloudflare Access (free tier, single-user).
#
# Prereqs (one-time, in your Cloudflare account dashboard):
#   1. Add your zone (domain) to Cloudflare.
#   2. Enable Cloudflare Access (Zero Trust → Access → Applications).
#   3. Create an Access self-hosted application for the hostname you'll
#      use below; restrict the Access policy to your email address.
#
# This script does the local plumbing only:
#   - logs in (browser-based, one-time)
#   - creates a tunnel named "openclaw" (idempotent)
#   - prints the tunnel UUID for your config.yml
#   - starts the tunnel in the foreground
#
# Free tier: yes, both Tunnel and Access (up to 50 users on the free plan).
set -euo pipefail
cd "$(dirname "$0")/.."

CLOUDFLARED="${CLOUDFLARED_BIN:-/home/aifactory/cloudflared}"
TUNNEL_NAME="${OPENCLAW_TUNNEL_NAME:-openclaw}"
CONFIG="${HOME}/.cloudflared/config.yml"

if [ ! -x "$CLOUDFLARED" ]; then
  echo "ERROR: cloudflared not found at $CLOUDFLARED" >&2
  echo "  Download from https://github.com/cloudflare/cloudflared/releases" >&2
  exit 1
fi

# 1. Login (idempotent — opens a browser the first time, no-ops afterwards)
if [ ! -f "${HOME}/.cloudflared/cert.pem" ]; then
  echo "[1/3] Logging in to Cloudflare (browser will open)…"
  "$CLOUDFLARED" tunnel login
else
  echo "[1/3] Already logged in (~/.cloudflared/cert.pem present)."
fi

# 2. Ensure tunnel exists
if "$CLOUDFLARED" tunnel list | awk '{print $2}' | grep -qx "$TUNNEL_NAME"; then
  echo "[2/3] Tunnel '$TUNNEL_NAME' already exists."
else
  echo "[2/3] Creating tunnel '$TUNNEL_NAME'…"
  "$CLOUDFLARED" tunnel create "$TUNNEL_NAME"
fi

UUID="$("$CLOUDFLARED" tunnel list | awk -v n="$TUNNEL_NAME" '$2==n {print $1; exit}')"
echo "    Tunnel UUID: $UUID"

# 3. Wire config if missing
if [ ! -f "$CONFIG" ]; then
  echo "[3/3] No ~/.cloudflared/config.yml. Copy and edit infra/cloudflared/config.example.yml:"
  echo
  echo "    mkdir -p ~/.cloudflared"
  echo "    cp infra/cloudflared/config.example.yml ~/.cloudflared/config.yml"
  echo "    sed -i \"s/<YOUR-TUNNEL-UUID>/${UUID}/g\" ~/.cloudflared/config.yml"
  echo "    \$EDITOR ~/.cloudflared/config.yml   # set hostname"
  echo
  echo "Then add the DNS route:"
  echo "    $CLOUDFLARED tunnel route dns $TUNNEL_NAME openclaw.<your-zone>.com"
  echo
  exit 0
fi

# Run the tunnel in the foreground.
echo "[3/3] Starting tunnel '$TUNNEL_NAME' (Ctrl-C to stop)…"
exec "$CLOUDFLARED" tunnel --config "$CONFIG" run "$TUNNEL_NAME"
