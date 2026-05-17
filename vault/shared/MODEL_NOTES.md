# Consilo — Model notes

## Chat model: gemma-4-26B-A4B-it (Q4_K_M GGUF)
- Path: `/home/aifactory/models/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf`
- Served via llama.cpp `llama-server` on port 8080 (OpenAI-compatible HTTP).
- Alias used by clients: `gemma-4-26B-A4B-it`.
- Prompt style: chat completions API; `--jinja` enabled in the launch script
  so llama-server applies the model's chat template.
- Recommended sampling for Implementer: `temperature=0.2`, `max_tokens≈1400`.
- Recommended sampling for Reviewer: `temperature=0.0`, structured-JSON output.

## Embedding model: bge-m3 (default, configurable)
- Default path placeholder: `/home/aifactory/models/bge-m3-q4_k_m.gguf`.
- Served via a second `llama-server` on port 8081 with `--embeddings`.
- Why bge-m3: dense + multilingual + long context; competitive with closed
  alternatives, fully OSS.
- Alternatives considered: `nomic-embed-text-v1.5`, `all-MiniLM-L6-v2`. bge-m3
  picked for higher recall on executive-prose retrieval.

## Stub mode (slice)
- Both LLM and Embedder run in stub mode by default. Stub LLM emits a
  deterministic deck-outline / review-JSON based on a hash signature; stub
  Embedder emits a SHA-256-derived L2-normalized vector of `CONSILO_EMBED_DIM`
  dimensions (default 384).
- Audit traces capture `"llm_mode": "stub"` so downstream consumers can never
  mistake stub outputs for live model outputs.

## Switching to live mode
1. `make llama-chat` (foreground)
2. `make llama-embed` (foreground, second terminal)
3. In `.env`: `CONSILO_LLM_MODE=live`, `CONSILO_EMBED_MODE=live`
4. `make healthz` should show `2 ok / 0 fail`.
5. `make slice` will now drive the real Gemma model end-to-end.
