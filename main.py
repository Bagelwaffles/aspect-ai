import os
import time
import socket
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ---------- FastAPI app ----------
app = FastAPI()

# Allow a browser app to call the API (lock this down later to your site)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # TODO: change to your site URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: if you want /deploy to ping a Pipedream workflow, set its URL
# in your Render "Environment" as PD_WEBHOOK_URL. If empty, we no-op.
PD_WEBHOOK_URL = os.getenv("PD_WEBHOOK_URL", "").strip()


# ---------- Helpers ----------
async def send_to_pipedream(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST the payload to Pipedream if PD_WEBHOOK_URL is set; else no-op."""
    if not PD_WEBHOOK_URL:
        return {"status_code": 204, "note": "PD_WEBHOOK_URL not set"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(PD_WEBHOOK_URL, json=payload)
        return {"status_code": r.status_code, "text": r.text}
    except Exception as err:
        # Don’t crash the app if PD is down; just report what happened.
        return {"status_code": 599, "error": repr(err)}


def service_info() -> Dict[str, Any]:
    """Collects useful Render env details for logging/observability."""
    return {
        "host": socket.gethostname(),
        "render_service_id": os.getenv("RENDER_SERVICE_ID"),
        "render_service_name": os.getenv("RENDER_SERVICE_NAME"),
        "git_branch": os.getenv("RENDER_GIT_BRANCH"),
        "git_commit": os.getenv("RENDER_GIT_COMMIT"),
        "region": os.getenv("RENDER_REGION"),
        "port": os.getenv("PORT"),
    }


# ---------- Routes ----------
@app.get("/")
def root():
    # simple browser-friendly check
    return {"status": "ok", "service": os.getenv("RENDER_SERVICE_NAME")}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.on_event("startup")
async def notify_startup():
    """Send a 'startup' event to Pipedream (optional)."""
    payload = {
        "source": "aspect-ai",
        "action": "startup",
        "timestamp": int(time.time()),
        "service": service_info(),
        "status": "live",
    }
    # fire-and-forget; never break startup on webhook failure
    _ = await send_to_pipedream(payload)


@app.post("/deploy")
async def deploy(request: Request):
    """
    Manual deploy trigger (or just a test endpoint).
    Sends a payload to Pipedream with request + service context.
    """
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
        "service": service_info(),
    }

    result = await send_to_pipedream(payload)

    # Treat 300+ from PD as a bad gateway
    if int(result.get("status_code", 200)) >= 300:
        raise HTTPException(status_code=502, detail=f"Pipedream returned {result}")

    return {"ok": True, "pipedream": result}
