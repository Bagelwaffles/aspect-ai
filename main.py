from fastapi import FastAPI, Request, HTTPException
import os, socket, time
import httpx

app = FastAPI()

PD_WEBHOOK_URL = os.getenv("PD_WEBHOOK_URL") or os.getenv("PD_WEBHOOK_URL".upper())
PD_WEBHOOK_SECRET = os.getenv("PD_WEBHOOK_SECRET") or os.getenv("PD_WEBHOOK_SECRET".upper())

# Helper: send JSON to Pipedream
async def send_to_pipedream(payload: dict):
    if not PD_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="PD_WEBHOOK_URL not set")
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Secret": PD_WEBHOOK_SECRET or ""   # optional auth
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(PD_WEBHOOK_URL, json=payload, headers=headers)
        return {"status_code": r.status_code, "text": r.text}

@app.get("/")
def root():
    return {"message": "Aspect AI is running on Render!"}

# ------------- NEW: notify Pipedream on startup -------------
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
        "status": "live"
    }
    try:
        await send_to_pipedream(payload)
    except Exception as e:
        # Don’t crash the app if the webhook fails; just log.
        print("Pipedream startup webhook failed:", e)

# ------------- NEW: manual deploy trigger -------------
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
            "body": body
        },
        "service": {
            "render_service_id": os.getenv("RENDER_SERVICE_ID"),
            "render_service_name": os.getenv("RENDER_SERVICE_NAME"),
            "git_branch": os.getenv("RENDER_GIT_BRANCH"),
            "git_commit": os.getenv("RENDER_GIT_COMMIT"),
        }
    }

    result = await send_to_pipedream(payload)
    if result["status_code"] >= 300:
        raise HTTPException(status_code=502, detail=f"Pipedream returned {result['status_code']}: {result['text']}")
    return {"ok": True, "pipedream": result}
