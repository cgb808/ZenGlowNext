"""Centralized Session Manager (Redis-backed)

Asynchronous, stateless session state for streaming interactions (e.g., voice
fragments). Stores a per-session Hash and a rolling List of fragments. All
operations are async and require a `redis.asyncio.Redis` client.

If redis.asyncio is not available, this module can be imported but functions
will raise at runtime unless a compatible client is provided.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

try:  # optional dependency
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - optional
    aioredis = None  # type: ignore

SESSION_KEY_PREFIX = "session:voice"
SESSION_TTL_SECONDS = 3600  # 1 hour


async def get_session(redis: "aioredis.Redis", session_id: str) -> Dict[str, Any]:
    """Retrieve full state for a session.

    Returns a default empty structure if the session does not exist.
    """
    session_key = f"{SESSION_KEY_PREFIX}:{session_id}"
    pipe = redis.pipeline()
    pipe.hgetall(session_key)
    pipe.lrange(f"{session_key}:fragments", 0, -1)
    results = await pipe.execute()

    session_data = results[0] or {}
    fragments = results[1] or []

    if not session_data:
        return {
            "session_id": session_id,
            "accum_text": "",
            "turns": 0,
            "is_final": False,
            "fragments": [],
        }

    # Decode bytes safely
    def _get_bytes(d: Dict[bytes, bytes], key: bytes, default: bytes = b"") -> bytes:
        try:
            return d.get(key, default) or default
        except Exception:
            return default

    accum_text = _get_bytes(session_data, b"accum_text").decode("utf-8", errors="ignore")
    turns_raw = _get_bytes(session_data, b"turns", b"0")
    try:
        turns = int(turns_raw.decode() if isinstance(turns_raw, (bytes, bytearray)) else turns_raw)
    except Exception:
        turns = 0
    is_final_raw = _get_bytes(session_data, b"is_final", b"0")
    is_final = (is_final_raw == b"1") or (is_final_raw.decode(errors="ignore").strip() in {"1", "true", "True"})

    return {
        "session_id": session_id,
        "accum_text": accum_text,
        "turns": turns,
        "is_final": bool(is_final),
        "fragments": [f.decode("utf-8", errors="ignore") if isinstance(f, (bytes, bytearray)) else str(f) for f in fragments],
    }


async def append_fragment(
    redis: "aioredis.Redis", session_id: str, fragment: str, is_final: bool
) -> Dict[str, Any]:
    """Append a fragment and update session state atomically with TTL refresh."""
    session_key = f"{SESSION_KEY_PREFIX}:{session_id}"
    fragment_key = f"{session_key}:fragments"

    current_session = await get_session(redis, session_id)
    new_text = (current_session.get("accum_text", "") + (" " + fragment if fragment else "")).strip()

    pipe = redis.pipeline()
    pipe.hset(session_key, mapping={
        "accum_text": new_text,
        "is_final": "1" if is_final else "0",
        "last_updated": json.dumps(True),
    })
    if fragment:
        pipe.rpush(fragment_key, fragment)
    if is_final:
        pipe.hincrby(session_key, "turns", 1)
    pipe.expire(session_key, SESSION_TTL_SECONDS)
    pipe.expire(fragment_key, SESSION_TTL_SECONDS)
    await pipe.execute()

    return await get_session(redis, session_id)


__all__ = ["get_session", "append_fragment", "SESSION_KEY_PREFIX", "SESSION_TTL_SECONDS"]
