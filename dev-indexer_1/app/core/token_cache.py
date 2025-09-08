"""Tokenization cache (hash(text)-> tokens) to reduce CPU.

Interface kept minimal for future plug of a more advanced tokenizer.
"""
from __future__ import annotations
import hashlib
import os
import threading
from collections import OrderedDict
from typing import Any, Callable, List
from . import cache_metrics
from . import redis_backend

_max = int(os.getenv("TOKEN_CACHE_MAX", "1024"))
_lock = threading.RLock()
_store: "OrderedDict[str, Any]" = OrderedDict()


def _key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def get(text: str, builder: Callable[[], Any]) -> Any:
    k = _key(text)
    if redis_backend.enabled():
        rv = redis_backend.get(k)
        if rv is not None:
            cache_metrics.increment("token_hits")
            return rv
    with _lock:
        v = _store.get(k)
        if v is not None:
            _store.move_to_end(k)
            cache_metrics.increment("token_hits")
            return v
        cache_metrics.increment("token_misses")
    v = builder()
    try:
        if redis_backend.enabled():
            ttl = int(os.getenv("TOKEN_CACHE_TTL", "1800"))
            redis_backend.set(k, v, ttl=ttl)
    except Exception:
        pass
    with _lock:
        _store[k] = v
        _store.move_to_end(k)
        if len(_store) > _max:
            _store.popitem(last=False)
    return v


def batch_get(texts: List[str], builder: Callable[[str], Any]) -> list[Any]:
    """Batch lookup using redis mget when available; builder applied per-miss.

    This does NOT attempt local batch fill optimization beyond sequential store writes
    (acceptable given typical small batch sizes for tokenization).
    """
    keys = [_key(t) for t in texts]
    results: list[Any] = [None] * len(texts)
    remaining_indices: list[int] = []
    if redis_backend.enabled():  # try redis mget first
        try:
            fetched = redis_backend.mget(keys)
            for i, val in enumerate(fetched):
                if val is not None:
                    cache_metrics.increment("token_hits")
                    results[i] = val
                else:
                    remaining_indices.append(i)
        except Exception:
            remaining_indices = list(range(len(texts)))
    else:
        remaining_indices = list(range(len(texts)))
    # Local cache check for misses
    with _lock:
        for i in list(remaining_indices):
            k = keys[i]
            v = _store.get(k)
            if v is not None:
                _store.move_to_end(k)
                cache_metrics.increment("token_hits")
                results[i] = v
                remaining_indices.remove(i)
    # Build remaining
    for i in remaining_indices:
        cache_metrics.increment("token_misses")
        txt = texts[i]
        val = builder(txt)
        results[i] = val
        k = keys[i]
        try:
            if redis_backend.enabled():
                ttl = int(os.getenv("TOKEN_CACHE_TTL", "1800"))
                redis_backend.set(k, val, ttl=ttl)
        except Exception:
            pass
        with _lock:
            _store[k] = val
            _store.move_to_end(k)
            if len(_store) > _max:
                _store.popitem(last=False)
    return results

__all__ = ["get", "batch_get"]
