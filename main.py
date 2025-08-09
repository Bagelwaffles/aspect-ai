from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

HTML = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Aspect AI</title></head>
  <body style="font-family:system-ui;margin:40px">
    <h1>Aspect AI</h1>
    <p>✅ Service is running on Render.</p>
  </body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root_get():
    return HTML

# Handle HEAD so Render health checks / browsers don't trigger 405
@app.head("/")
async def root_head():
    return Response()

# Simple health endpoint for monitors
@app.get("/healthz")
async def health():
    return JSONResponse({"status": "ok"})
