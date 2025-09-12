"""Redis cache & messaging utilities (enhanced).

Provides both a high-level `RedisCache` class and backward-compatible
functional helpers used elsewhere in the codebase.

Key Features:
 - Env-driven connection (REDIS_HOST/PORT/DB/PASSWORD/SSL)
 - JSON + MessagePack serialization
 - Namespaced key hashing (MD5) to prevent oversized keys
 - RAG query result caching helpers (msgpack by default)
 - Build update Pub/Sub publishing
 - Graceful dependency and connection handling
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import msgpack  # type: ignore
import redis  # type: ignore

__all__ = [
    "RedisCache",
    "RedisCacheError",
    # functional helpers
    "cache_set_json",
    "cache_get_json",
    "cache_set_msgpack",
    "cache_get_msgpack",
    "cache_delete",
    "cache_rag_query_result",
    "get_cached_rag_query",
    "publish_build_update",
]


class RedisCacheError(Exception):
    pass


class RedisCache:
    """Configurable Redis cache facade.

    Instantiation pings Redis; if unavailable, raises RedisCacheError.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        ssl: Optional[bool] = None,
        socket_timeout: int = 5,
    ) -> None:
        # Support unified REDIS_URL if provided (redis://[:password@]host:port/db)
        redis_url = os.getenv("REDIS_URL")
        parsed = urlparse(redis_url) if redis_url else None
        if parsed and parsed.scheme.startswith("redis"):
            if not host:
                self.host = parsed.hostname or "localhost"
            else:
                self.host = host
            if not port:
                self.port = int(parsed.port or 6379)
            else:
                self.port = port
            if not db:
                # path like /0
                try:
                    self.db = int((parsed.path or "/0").lstrip("/"))
                except Exception:
                    self.db = 0
            else:
                self.db = db
            pw_from_url = parsed.password
            self.password = password or pw_from_url or os.getenv("REDIS_PASSWORD")
        else:
            self.host = host or os.getenv("REDIS_HOST", "localhost")
            self.port = port or int(os.getenv("REDIS_PORT", "6379"))
            self.db = db or int(os.getenv("REDIS_DB", "0"))
            self.password = password or os.getenv("REDIS_PASSWORD")
        if ssl is None:
            ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
        self.ssl = ssl
        self.client: Any
        try:
            self.client = redis.Redis(  # type: ignore[attr-defined]
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                ssl=self.ssl,
                socket_timeout=socket_timeout,
            )
            self.client.ping()  # type: ignore[call-arg]
        except Exception as e:  # pragma: no cover (network)
            # Instead of raising (which surfaces in user flow), convert this instance into a null no-op.
            print(
                f"[redis_cache] WARNING: Redis connection failed: {e}. Switching to no-op cache instance."
            )

            class _Noop:
                def __getattr__(
                    self, _name: str
                ) -> _Any:  # return a lambda that does nothing
                    return lambda *a, **k: None

            self.client = _Noop()

    # Internal helpers -------------------------------------------------
    def _ns_key(self, namespace: str, key: str, hashed: bool = True) -> str:
        if hashed:
            digest = hashlib.md5(key.encode()).hexdigest()
            return f"{namespace}:{digest}"
        return f"{namespace}:{key}"  # fallback (debugging)

    # JSON -------------------------------------------------------------
    def set_json(self, namespace: str, key: str, value: Any, ttl: int = 300) -> None:
        try:
            self.client.setex(self._ns_key(namespace, key), ttl, json.dumps(value, ensure_ascii=False))  # type: ignore[attr-defined]
        except Exception as e:
            raise RedisCacheError(f"set_json error: {e}")

    def get_json(self, namespace: str, key: str) -> Optional[Any]:
        try:
            raw = self.client.get(self._ns_key(namespace, key))  # type: ignore[attr-defined]
            return json.loads(raw) if raw else None
        except Exception as e:
            raise RedisCacheError(f"get_json error: {e}")

    # MessagePack ------------------------------------------------------
    def set_msgpack(self, namespace: str, key: str, value: Any, ttl: int = 300) -> None:
        try:
            self.client.setex(self._ns_key(namespace, key), ttl, msgpack.packb(value, use_bin_type=True))  # type: ignore[attr-defined]
        except Exception as e:
            raise RedisCacheError(f"set_msgpack error: {e}")

    def get_msgpack(self, namespace: str, key: str) -> Optional[Any]:
        try:
            raw = self.client.get(self._ns_key(namespace, key))  # type: ignore[attr-defined]
            return msgpack.unpackb(raw, raw=False) if raw else None
        except Exception as e:
            raise RedisCacheError(f"get_msgpack error: {e}")

    # Generic ----------------------------------------------------------
    def delete(self, namespace: str, key: str) -> None:
        try:
            self.client.delete(self._ns_key(namespace, key))  # type: ignore[attr-defined]
        except Exception as e:
            raise RedisCacheError(f"delete error: {e}")

    # RAG Query Result Caching ----------------------------------------
    def cache_rag_query_result(
        self, query: str, top_k: int, result: Any, ttl: int = 300
    ) -> None:
        ns = f"rag:q:{top_k}"
        # keep msgpack for compactness
        self.set_msgpack(ns, query, result, ttl)

    def get_cached_rag_query(self, query: str, top_k: int) -> Optional[Any]:
        ns = f"rag:q:{top_k}"
        return self.get_msgpack(ns, query)

    # Pub/Sub ----------------------------------------------------------
    def publish_build_update(
        self, content: Dict[str, Any], channel: Optional[str] = None
    ) -> None:
        ch = channel or os.getenv("REDIS_BUILD_CHANNEL", "build_updates")
        message: Dict[str, Any] = {
            "type": "build_update",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            packed = msgpack.packb(message, use_bin_type=True)
            self.client.publish(ch, packed)  # type: ignore[attr-defined]
        except Exception as e:
            raise RedisCacheError(f"publish_build_update error: {e}")


# Lazy global instance so import does not fail hard if Redis missing ----------
_global_cache: Optional[RedisCache] = None


class _NullRedisCache:
    """No-op stand‑in when real Redis is unavailable.

    Provides the subset of methods used by the functional helpers so higher layers
    can continue operating without branching. All getters return None; setters publish nothing.
    """

    def set_json(self, *_, **__):
        return None

    def get_json(self, *_, **__):  # noqa: D401
        return None

    def set_msgpack(self, *_, **__):
        return None

    def get_msgpack(self, *_, **__):
        return None

    def delete(self, *_, **__):
        return None

    def cache_rag_query_result(self, *_, **__):
        return None

    def get_cached_rag_query(self, *_, **__):
        return None

    def publish_build_update(self, *_, **__):
        return None


from typing import Any as _Any


def _global() -> _Any:
    global _global_cache
    if _global_cache is None:
        disable = os.getenv("DISABLE_REDIS", "0").lower() in {"1", "true", "yes"}
        if disable:
            _global_cache = _NullRedisCache()  # type: ignore
            return _global_cache
        try:
            _global_cache = RedisCache()
        except RedisCacheError as e:
            # Log once, then substitute null cache so callers never raise.
            try:
                print(f"[redis_cache] WARNING: {e}. Using null in-memory no-op cache.")
            except Exception:
                pass
            _global_cache = _NullRedisCache()  # type: ignore
    return _global_cache  # type: ignore


# Backward-Compatible Functional API ---------------------------------------
def cache_set_json(
    namespace: str, key: str, value: Any, ttl_seconds: int = 300
) -> None:
    _global().set_json(namespace, key, value, ttl_seconds)


def cache_get_json(namespace: str, key: str) -> Optional[Any]:
    return _global().get_json(namespace, key)


def cache_set_msgpack(
    namespace: str, key: str, value: Any, ttl_seconds: int = 300
) -> None:
    _global().set_msgpack(namespace, key, value, ttl_seconds)


def cache_get_msgpack(namespace: str, key: str) -> Optional[Any]:
    return _global().get_msgpack(namespace, key)


def cache_delete(namespace: str, key: str) -> None:
    _global().delete(namespace, key)


def cache_rag_query_result(
    query: str, top_k: int, result: Any, ttl_seconds: int = 300
) -> None:
    _global().cache_rag_query_result(query, top_k, result, ttl_seconds)


def get_cached_rag_query(query: str, top_k: int) -> Optional[Any]:
    return _global().get_cached_rag_query(query, top_k)


def publish_build_update(content: Dict[str, Any]) -> None:
    _global().publish_build_update(content)
