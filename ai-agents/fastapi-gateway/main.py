import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
import logging

API_KEY = os.getenv("API_GATEWAY_KEY", "changeme")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

app = FastAPI(title="ZenGlow Gateway", version="1.0.0")

# Structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("gateway")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        logger.warning("Unauthorized access attempt.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

@app.middleware("http")
async def audit_log(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}

@app.get("/ready", tags=["system"])
async def ready():
    # Add readiness checks for downstream services here
    return {"ready": True}

@app.get("/admin/ping", dependencies=[Depends(verify_api_key)], tags=["admin"])
async def admin_ping():
    return {"ping": "pong"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
