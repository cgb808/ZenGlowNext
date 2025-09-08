"""Prompt expansion cache (persona+mode->rendered string)."""
from __future__ import annotations
import hashlib
import os
import threading
from collections import OrderedDict
from typing import Callable
from . import cache_metrics
from . import redis_backend

_max = int(os.getenv("PROMPT_CACHE_MAX", "256"))
_lock = threading.RLock()
_store: "OrderedDict[str, str]" = OrderedDict()


def _key(key_parts: list[str]) -> str:
    h = hashlib.sha256()
    for p in key_parts:
        h.update(p.encode())
        h.update(b"\0")
    return h.hexdigest()


def get(key_parts: list[str], builder: Callable[[], str]) -> str:
    k = _key(key_parts)
    # Redis first if enabled
    if redis_backend.enabled():
        rv = redis_backend.get(k)
        if isinstance(rv, str):  # fast path
            cache_metrics.increment("prompt_hits")
            return rv
    with _lock:
        v = _store.get(k)
        if v is not None:
            _store.move_to_end(k)
            cache_metrics.increment("prompt_hits")
            return v
        cache_metrics.increment("prompt_misses")
    v = builder()
    # Write to redis (best-effort)
    try:
        if redis_backend.enabled():
            ttl = int(os.getenv("PROMPT_CACHE_TTL", "3600"))
            redis_backend.set(k, v, ttl=ttl)
    except Exception:
        pass
    with _lock:
        _store[k] = v
        _store.move_to_end(k)
        if len(_store) > _max:
            _store.popitem(last=False)
    return v
