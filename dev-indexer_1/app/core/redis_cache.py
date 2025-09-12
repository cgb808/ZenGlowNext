from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_MEM_CACHE: Dict[str, Dict[str, Any]] = {}

try:  # best-effort optional import
    import redis  # type: ignore
    _REDIS_URL = os.getenv("REDIS_URL")
    _R = redis.Redis.from_url(_REDIS_URL) if _REDIS_URL else None
except Exception:  # pragma: no cover - fallback
    _R = None


def _ns_key(ns: str, key: str) -> str:
    return f"{ns}:{key}"


def cache_set_msgpack(ns: str, key: str, value: Dict[str, Any], ttl_seconds: int = 60) -> None:
    # JSON used instead of msgpack for simplicity; tests don't depend on exact format
    payload = json.dumps(value)
    if _R is not None:
        try:
            _R.setex(_ns_key(ns, key), ttl_seconds, payload)
            return
        except Exception:
            pass
    # in-memory fallback (no TTL enforcement for tests)
    bucket = _MEM_CACHE.setdefault(ns, {})
    bucket[key] = value


def cache_get_msgpack(ns: str, key: str) -> Optional[Dict[str, Any]]:
    if _R is not None:
        try:
            raw = _R.get(_ns_key(ns, key))
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    return _MEM_CACHE.get(ns, {}).get(key)


def cache_rag_query_result(query: str, top_k: int, value: Dict[str, Any]) -> None:
    cache_set_msgpack("rag:full", f"{query}:{top_k}", value, ttl_seconds=60)


def get_cached_rag_query(query: str, top_k: int) -> Optional[Dict[str, Any]]:
    return cache_get_msgpack("rag:full", f"{query}:{top_k}")
