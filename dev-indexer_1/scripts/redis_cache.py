"""Shim: re-export canonical Redis cache utilities.

This script-level module proxies to `app.core.redis_cache` to avoid duplication.
"""

from __future__ import annotations

from app.core.redis_cache import (  # noqa: F401
    RedisCache,
    RedisCacheError,
    cache_delete,
    cache_get_json,
    cache_get_msgpack,
    cache_rag_query_result,
    cache_set_json,
    cache_set_msgpack,
    get_cached_rag_query,
    publish_build_update,
)

__all__ = [
    "RedisCache",
    "RedisCacheError",
    "cache_set_json",
    "cache_get_json",
    "cache_set_msgpack",
    "cache_get_msgpack",
    "cache_delete",
    "cache_rag_query_result",
    "get_cached_rag_query",
    "publish_build_update",
]
