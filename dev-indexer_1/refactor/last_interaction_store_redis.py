"""Centralized, Asynchronous Last Interaction Store (Redis-backed)

This module provides an async Redis implementation for tracking the last
interaction recap per person. It does not alter existing in-memory behavior; it
can be adopted by callers that have an async context and a Redis client.

Architectural Benefits:
- Scalable: State is shared across any number of server workers.
- Persistent: Interaction data can survive application restarts (subject to Redis persistence).
- Asynchronous: Non-blocking operations fit the async architecture.
- Centralized: Single source of truth for interaction state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:  # optional dependency
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    aioredis = None  # type: ignore

# Constants for Redis keys and TTL (Time To Live)
INTERACTION_KEY_PREFIX = "interaction:last"
INTERACTION_TTL_SECONDS = 86400  # 24 hours


@dataclass
class LastInteraction:
    person_id: str
    ts: datetime
    recap: str


def _key(person_id: str) -> str:
    return f"{INTERACTION_KEY_PREFIX}:{person_id}"


async def update_last_interaction(
    redis: "aioredis.Redis", person_id: str, recap: str
) -> None:
    """Save the last interaction summary for a person to Redis.

    Uses a Redis hash to store fields and sets a TTL for automatic expiry.
    """
    session_key = _key(person_id)
    from app.core.timezone import now_tz  # local import to avoid heavy import cycles
    now_ts = now_tz()

    interaction_data = {
        "ts": now_ts.isoformat(),
        "recap": (recap or "").strip(),
    }

    # Use an explicit transaction for atomic updates
    pipe = redis.pipeline(transaction=True)
    pipe.hset(session_key, mapping=interaction_data)
    pipe.expire(session_key, INTERACTION_TTL_SECONDS)
    await pipe.execute()


async def get_last_interaction(
    redis: "aioredis.Redis", person_id: str
) -> Optional[LastInteraction]:
    """Retrieve the last interaction summary for a person from Redis.

    Returns None if not found or if stored data is incomplete.
    """
    session_key = _key(person_id)
    data = await redis.hgetall(session_key)
    if not data:
        return None

    # redis-py returns dict[bytes, bytes] for hgetall; guard decode and parsing
    try:
        ts_raw = data.get(b"ts") if isinstance(next(iter(data.keys())), (bytes, bytearray)) else data.get("ts")  # type: ignore[index]
        recap_raw = data.get(b"recap") if isinstance(next(iter(data.keys())), (bytes, bytearray)) else data.get("recap")  # type: ignore[index]
    except StopIteration:
        ts_raw = None
        recap_raw = None

    if not ts_raw or not recap_raw:
        return None

    if isinstance(ts_raw, (bytes, bytearray)):
        ts_str = ts_raw.decode("utf-8", errors="ignore")
    else:
        ts_str = str(ts_raw)

    if isinstance(recap_raw, (bytes, bytearray)):
        recap_str = recap_raw.decode("utf-8", errors="ignore")
    else:
        recap_str = str(recap_raw)

    try:
        ts = datetime.fromisoformat(ts_str)
    except Exception:
        # Fallback: treat as UTC naive if parsing fails
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        except Exception:
            return None

    return LastInteraction(person_id=person_id, ts=ts, recap=recap_str)


__all__ = [
    "LastInteraction",
    "update_last_interaction",
    "get_last_interaction",
    "INTERACTION_KEY_PREFIX",
    "INTERACTION_TTL_SECONDS",
]
