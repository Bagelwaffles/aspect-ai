import os, time, socket
from typing import Dict, Any
import httpx
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# ---------- simple routes (for browser + health check) ----------
@app.get("/")
def root():
    return {"status": "ok", "service": os.getenv("RENDER_SERVICE_NAME")}

@app.get("/health")
def health():
    return {"status": "healthy"}

# ---------- optional: notify Pipedream on startup / manual trigger ----------
PD_WEBHOOK_URL = os.getenv("PD_WEBHOOK_URL")  # set on Render > Environment

async def send_to_pipedream(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not PD_WEBHOOK_URL:
        return {"status_code": 204, "note": "PD_WEBHOOK_URL not set"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(PD_WEBHOOK_URL, json=payload)
        return {"status_code": r.status_code, "text": r.text}

@app.on_event("startup")
async def notify_startup():
    payload = {
        "source": "aspect-ai",
        "action": "startup",
        "timestamp": int(time.time()),
        "service": {
            "host": socket.gethostname(),
            "render_service_id": os.getenv("RENDER_SERVICE_ID"),
            "render_service_name": os.getenv("RENDER_SERVICE_NAME"),
            "git_branch": os.getenv("RENDER_GIT_BRANCH"),
            "git_commit": os.getenv("RENDER_GIT_COMMIT"),
            "region": os.getenv("RENDER_REGION"),
            "port": os.getenv("PORT"),
        },
        "status": "live",
    }
    try:
        await send_to_pipedream(payload)
    except Exception:
        # don't crash app if webhook fails
        pass

@app.post("/deploy")
async def deploy(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    payload = {
        "source": "aspect-ai",
        "action": "deploy",
        "timestamp": int(time.time()),
        "request": {
            "client_ip": request.client.host if request.client else None,
            "headers": dict(request.headers),
            "body": body,
        },
        "service": {
            "render_service_id": os.getenv("RENDER_SERVICE_ID"),
            "render_service_name": os.getenv("RENDER_SERVICE_NAME"),
            "git_branch": os.getenv("RENDER_GIT_BRANCH"),
            "git_commit": os.getenv("RENDER_GIT_COMMIT"),
        },
    }
    result = await send_to_pipedream(payload)
    if result.get("status_code", 200) >= 300:
        raise HTTPException(status_code=502, detail=f"Pipedream returned {result}")
    return {"ok": True, "pipedream": result}
