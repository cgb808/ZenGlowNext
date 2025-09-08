"""In-memory embedding cache keyed by content hash.

Assumes caller normalizes text. Stores float vectors as provided.
"""
from __future__ import annotations
import hashlib
import os
import threading
from collections import OrderedDict
from typing import Sequence, List, Callable
from . import cache_metrics
from . import redis_backend
import time

_max = int(os.getenv("EMBED_CACHE_MAX", "4096"))
_lock = threading.RLock()
_store: "OrderedDict[str, List[float]]" = OrderedDict()


def _key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def get_or_set(text: str, builder) -> Sequence[float]:  # builder returns list/sequence of floats
    k = _key(text)
    # First attempt Redis if enabled
    if redis_backend.enabled():  # pragma: no branch - fast path
        rv = redis_backend.get(k)
        if isinstance(rv, list) and rv and isinstance(rv[0], (float, int)):
            cache_metrics.increment("embed_hits")
            return [float(x) for x in rv]
    # Fallback to local store
    with _lock:
        v = _store.get(k)
        if v is not None:
            _store.move_to_end(k)
            cache_metrics.increment("embed_hits")
            return v
        cache_metrics.increment("embed_misses")
    # Dogpile prevention: try short redis lock
    lock_key = f"lock:embed:{k}"
    got_lock = False
    try:
        if redis_backend.enabled():
            from app.core.redis_backend import _client  # type: ignore
            if _client is not None:  # type: ignore
                got_lock = _client.set(lock_key, b"1", nx=True, ex=10)  # type: ignore[attr-defined]
    except Exception:
        pass
    if not got_lock:
        # brief backoff then recheck
        time.sleep(0.01)
        with _lock:
            v2 = _store.get(k)
            if v2 is not None:
                cache_metrics.increment("embed_hits")
                return v2
    v = list(builder())
    # Persist to redis (best-effort) before local insert
    try:
        if redis_backend.enabled():
            ttl = int(os.getenv("EMBED_CACHE_TTL", "3600"))
            redis_backend.set(k, v, ttl=ttl)
    except Exception:
        pass
    with _lock:
        _store[k] = v
        _store.move_to_end(k)
        if len(_store) > _max:
            _store.popitem(last=False)
    # Release lock implicitly upon expiry; no delete needed
    return v


def batch_get_or_set(texts: List[str], builder: Callable[[str], Sequence[float]]) -> list[Sequence[float]]:
    """Batch variant utilizing redis mget when available.

    For misses, builder is invoked per text (future optimization: true batch embedder).
    """
    keys = [_key(t) for t in texts]
    results: list[Sequence[float] | None] = [None] * len(texts)
    remaining = list(range(len(texts)))
    if redis_backend.enabled():
        try:
            fetched = redis_backend.mget(keys)
            for i, val in enumerate(fetched):
                if isinstance(val, list):
                    results[i] = [float(x) for x in val]
                    cache_metrics.increment("embed_hits")
                    remaining.remove(i)
        except Exception:
            pass
    # Local cache for remaining
    with _lock:
        for i in list(remaining):
            k = keys[i]
            v = _store.get(k)
            if v is not None:
                _store.move_to_end(k)
                results[i] = v
                cache_metrics.increment("embed_hits")
                remaining.remove(i)
    # Build each remaining
    for i in remaining:
        cache_metrics.increment("embed_misses")
        txt = texts[i]
        # Dogpile per element
        k = keys[i]
        lock_key = f"lock:embed:{k}"
        got_lock = False
        try:
            if redis_backend.enabled():
                from app.core.redis_backend import _client  # type: ignore
                if _client is not None:  # type: ignore
                    got_lock = _client.set(lock_key, b"1", nx=True, ex=10)  # type: ignore[attr-defined]
        except Exception:
            pass
        if not got_lock:
            time.sleep(0.01)
            with _lock:
                v2 = _store.get(k)
                if v2 is not None:
                    results[i] = v2
                    cache_metrics.increment("embed_hits")
                    continue
        val = list(builder(txt))
        results[i] = val
        try:
            if redis_backend.enabled():
                ttl = int(os.getenv("EMBED_CACHE_TTL", "3600"))
                redis_backend.set(k, val, ttl=ttl)
        except Exception:
            pass
        with _lock:
            _store[k] = val
            _store.move_to_end(k)
            if len(_store) > _max:
                _store.popitem(last=False)
    # type ignore safe due to fill logic
    return [r if r is not None else [] for r in results]

__all__ = ["get_or_set", "batch_get_or_set"]
