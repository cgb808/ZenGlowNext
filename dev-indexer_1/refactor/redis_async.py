"""Async Redis client helper.

Builds a redis.asyncio client from environment variables, mirroring the
configuration used by the synchronous RedisCache but without introducing a hard
dependency when Redis is not installed or unreachable.

Usage:
    from app.core.redis_async import get_async_redis
    r = get_async_redis()
    if r:
        await r.ping()
"""
from __future__ import annotations

import os
from typing import Optional, Any
from urllib.parse import urlparse

_async_client: Optional[Any] = None
_init_attempted = False


def _build_async_client() -> Optional[Any]:
    try:
        import redis.asyncio as aioredis  # type: ignore
    except Exception:
        return None

    # Prefer REDIS_URL when provided
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            client = aioredis.from_url(redis_url, decode_responses=False)
            return client
        except Exception:
            return None

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD")
    ssl = os.getenv("REDIS_SSL", "false").lower() in {"1", "true", "yes"}
    try:
        client = aioredis.Redis(host=host, port=port, db=db, password=password, ssl=ssl)
        return client
    except Exception:
        return None


def get_async_redis() -> Optional[Any]:
    global _async_client, _init_attempted
    if _async_client is not None or _init_attempted:
        return _async_client
    _init_attempted = True
    _async_client = _build_async_client()
    return _async_client


__all__ = ["get_async_redis"]
