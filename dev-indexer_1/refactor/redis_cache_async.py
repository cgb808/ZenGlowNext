"""Async Redis cache helpers.

Provides a minimal async subset for msgpack get/set and RAG query result caching
to support async routers without introducing hard failures when Redis is
unavailable. Uses the async Redis client from app.core.redis_async.
"""
from __future__ import annotations

from typing import Any, Optional
import msgpack  # type: ignore

from app.core.redis_async import get_async_redis


def _ns_key(namespace: str, key: str) -> str:
    # Keep it simple; upstream sync cache hashes keys. For async helpers, use direct keys.
    return f"{namespace}:{key}"


async def cache_set_msgpack(redis, namespace: str, key: str, value: Any, ttl_seconds: int = 300) -> None:
    if not redis:
        return
    try:
        packed = msgpack.packb(value, use_bin_type=True)
        await redis.setex(_ns_key(namespace, key), ttl_seconds, packed)
    except Exception:
        return


async def cache_get_msgpack(redis, namespace: str, key: str) -> Optional[Any]:
    if not redis:
        return None
    try:
        raw = await redis.get(_ns_key(namespace, key))
        if not raw:
            return None
        return msgpack.unpackb(raw, raw=False)
    except Exception:
        return None


async def cache_rag_query_result(redis, query: str, top_k: int, result: Any, ttl_seconds: int = 300) -> None:
    await cache_set_msgpack(redis, f"rag:q:{top_k}", query, result, ttl_seconds)


async def get_cached_rag_query(redis, query: str, top_k: int) -> Optional[Any]:
    return await cache_get_msgpack(redis, f"rag:q:{top_k}", query)


__all__ = [
    "cache_set_msgpack",
    "cache_get_msgpack",
    "cache_rag_query_result",
    "get_cached_rag_query",
]
