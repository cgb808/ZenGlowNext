"""
Log Ingestion Gateway (The Switch)

This FastAPI router provides a high-throughput, asynchronous endpoint for
ingesting log frames. It acts as the "switch" that directs traffic into the
logging pipeline.

Responsibilities:
  - Accept log frames via a POST request.
  - Perform basic validation.
  - Add the log frame to a reliable Redis Stream.
  - Immediately return a 202 Accepted response.

This design decouples the log producer from the consumers, ensuring that the
act of logging is extremely fast and does not block the client application.
"""
from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
import msgpack

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - optional import in some envs
    aioredis = None  # type: ignore

from app.core.redis_async import get_async_redis


router = APIRouter(prefix="/log", tags=["logging"])

# The Redis Stream key where log frames will be queued.
LOG_STREAM_KEY = "log_frames_stream"


async def get_redis_client(request: Request):
    """Retrieve a shared redis.asyncio client.

    Preference order:
      1) request.app.state.redis if already initialized
      2) lazily construct via get_async_redis() helper
    """
    # Prefer an application-scoped client if already set up
    client = getattr(request.app.state, "redis", None)
    if client is not None:
        return client
    # Fallback to builder (may return None if Redis not available)
    client = get_async_redis()
    if client is None:
        raise HTTPException(status_code=503, detail="Redis client not available")
    # Optionally cache on app.state for re-use
    try:
        setattr(request.app.state, "redis", client)
    except Exception:
        pass
    return client


@router.post("/append", status_code=202)
async def append_log_frame(
    payload: Dict[str, Any],
    redis = Depends(get_redis_client),
):
    """Accepts a log frame and adds it to the processing stream."""
    # Basic validation
    if not all(k in payload for k in ["session_id", "user_id", "content"]):
        raise HTTPException(status_code=400, detail="Missing required log fields")

    try:
        # Serialize payload with MessagePack and push to Redis Streams
        packed_frame = msgpack.packb(payload, use_bin_type=True)
        await redis.xadd(LOG_STREAM_KEY, {"frame": packed_frame})
        return {"status": "queued"}
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to queue log frame: {e}")
