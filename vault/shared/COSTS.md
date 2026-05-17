# Consilo — Costs

**Recurring monetary cost: $0.**

| Component | Cost | Notes |
|---|---|---|
| llama.cpp / llama-server | $0 | OSS, local. |
| Gemma 4-26B-A4B-it GGUF (Q4_K_M) | $0 | Already on disk at `/home/aifactory/models/`. |
| bge-m3 GGUF (embeddings) | $0 | OSS; user must download once. |
| Qdrant OSS | $0 | Used in local embedded mode in the slice. |
| SQLite | $0 | stdlib via `sqlite3`. |
| Markdown vault | $0 | Filesystem. |
| SearXNG | $0 | Self-hosted Docker (P2). |
| Cloudflared Tunnel + Cloudflare Access | $0 | Free tier, single user (P2). |
| Telegram Bot API | $0 | Free (P1). |
| WhatsApp Cloud API | $0 | Free tier within Meta limits (P2). |
| GitHub private repo | $0 | Free for individuals. |

**Compute:** local CPU/GPU electricity only. No metered API calls.

If at any point a design decision threatens to introduce a recurring cost, that
decision must be paused per the hard constraints in `system_prd.md` §3.
