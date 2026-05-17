"""FastAPI server for inbound bridge webhooks.

Currently hosts:
  POST /bridges/wa/webhook  — wuzapi → ingest pipeline

Run with: `python -m consilo.bridges.server` (uvicorn on 127.0.0.1:8090)
"""
from __future__ import annotations
import os
from fastapi import FastAPI, Request, HTTPException
from .whatsapp import handle_webhook

app = FastAPI(title="Consilo bridges")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/bridges/wa/webhook")
async def wa_webhook(request: Request) -> dict:
    expected = os.getenv("WUZAPI_WEBHOOK_SECRET")
    if expected:
        got = request.headers.get("X-Wuzapi-Secret") or request.query_params.get("secret")
        if got != expected:
            raise HTTPException(status_code=401, detail="bad webhook secret")
    payload = await request.json()
    return handle_webhook(payload)


def main() -> None:
    import uvicorn
    host = os.getenv("CONSILO_BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("CONSILO_BRIDGE_PORT", "8090"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
