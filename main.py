# main.py
import os
import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()

PD_WEBHOOK_URL = os.getenv("PD_WEBHOOK_URL")  # set this in Render

@app.get("/")
def root():
    return {"message": "Aspect AI is running on Render!"}

@app.post("/deploy")
async def deploy():
    if not PD_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="PD_WEBHOOK_URL is not set")

    payload = {
        "source": "aspect-ai",
        "action": "deploy",
        "note": "Triggered from Render /deploy endpoint"
    }

    # optional: add a simple auth header if you set PD_WEBHOOK_SECRET in Render too
    headers = {}
    if os.getenv("PD_WEBHOOK_SECRET"):
        headers["X-Webhook-Secret"] = os.getenv("PD_WEBHOOK_SECRET")

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(PD_WEBHOOK_URL, json=payload, headers=headers)
    if r.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"Pipedream returned {r.status_code}: {r.text}")

    return {"ok": True, "pipedream_status": r.status_code}
