from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Aspect AI", version="0.1.0")

@app.get("/")
def home():
    return {"ok": True, "app": "Aspect AI", "message": "It works! 🚀"}

@app.get("/healthz")
def health():
    return JSONResponse({"status": "healthy"})
