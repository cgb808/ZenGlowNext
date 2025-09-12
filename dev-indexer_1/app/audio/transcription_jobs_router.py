"""Asynchronous transcription job router.

Implements creation + status polling for audio transcription jobs using
Redis streams and async DB client. Falls back gracefully if dependencies
are absent.
"""
from __future__ import annotations

import uuid
from typing import Any

try:
    import msgpack  # type: ignore
except Exception:  # pragma: no cover - fallback minimal packer
    class _MsgPackShim:  # type: ignore
        @staticmethod
        def packb(obj: Any) -> bytes:
            return str(obj).encode("utf-8")
    msgpack = _MsgPackShim()  # type: ignore

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status

try:
    from redis.asyncio import Redis  # type: ignore
except Exception:  # pragma: no cover - stub
    class Redis:  # type: ignore
        async def set(self, *_a, **_kw):
            return True
        async def xadd(self, *_a, **_kw):
            return "0-0"

try:
    from app.core.db_client_async import AsyncDBClient  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub
    class AsyncDBClient:  # type: ignore
        async def execute(self, *_a, **_kw):
            return None
        async def fetch_all(self, *_a, **_kw):
            return []

# Dependency providers (gateways)
try:
    from gateway_app import get_db_client, get_redis_client  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - lightweight fallbacks
    async def get_db_client():  # type: ignore
        return AsyncDBClient()
    async def get_redis_client():  # type: ignore
        return Redis()

router = APIRouter(prefix="/audio", tags=["audio-jobs"])


@router.post("/transcribe/job", status_code=status.HTTP_202_ACCEPTED)
async def transcribe(
    file: UploadFile = File(...),
    db: AsyncDBClient = Depends(get_db_client),
    redis: Redis = Depends(get_redis_client),
):
    """Accept an audio file, queue a transcription job, return job id."""
    job_id = str(uuid.uuid4())
    contents = await file.read()
    try:
        await db.execute(
            "INSERT INTO transcriptions (job_id, status, filename) VALUES (%s, 'pending', %s)",
            (job_id, file.filename),
        )
    except Exception as e:  # pragma: no cover - DB failure
        raise HTTPException(status_code=500, detail=f"db_insert_failed: {e}") from e
    try:
        await redis.set(f"audio_blob:{job_id}", contents, ex=3600)
        job_payload = msgpack.packb({"job_id": job_id})
        await redis.xadd("transcription_jobs", {"payload": job_payload})
    except Exception as e:  # pragma: no cover - Redis failure
        raise HTTPException(status_code=500, detail=f"queue_failed: {e}") from e
    return {"job_id": job_id, "status": "pending"}


@router.get("/transcribe/job/status/{job_id}")
async def get_transcription_status(
    job_id: str, db: AsyncDBClient = Depends(get_db_client)
):
    """Poll for transcription job status/result."""
    try:
        rows = await db.fetch_all(
            "SELECT status, transcript FROM transcriptions WHERE job_id = %s",
            (job_id,),
        )
    except Exception as e:  # pragma: no cover - DB failure
        raise HTTPException(status_code=500, detail=f"db_query_failed: {e}") from e
    if not rows:
        raise HTTPException(status_code=404, detail="Job not found")
    row0 = rows[0]
    if isinstance(row0, dict):  # expected shape
        return row0
    # Fallback mapping if row is a tuple-like
    try:  # pragma: no cover - defensive
        status_val = row0[0]
        transcript_val = row0[1] if len(row0) > 1 else None
        return {"status": status_val, "transcript": transcript_val}
    except Exception:
        return {"status": None, "transcript": None}
