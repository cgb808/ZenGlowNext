"""In-process response cache with msgpack pre-serialization.

Features:
  * LRU with TTL.
  * Optional msgpack negotiation (Accept: application/msgpack).
  * Pre-serializes and stores both JSON-able Python object and msgpack bytes to avoid re-work.
  * Disabled via RESPONSE_CACHE_DISABLED=1.

Environment:
  RESPONSE_CACHE_MAX (default 512 entries)
  RESPONSE_CACHE_TTL_SEC (default 60)
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

import msgpack  # type: ignore
from fastapi import Request
from fastapi.responses import Response, JSONResponse
from . import cache_metrics

_disabled = os.getenv("RESPONSE_CACHE_DISABLED", "0") in {"1", "true", "yes"}
_max = int(os.getenv("RESPONSE_CACHE_MAX", "512"))
_ttl = int(os.getenv("RESPONSE_CACHE_TTL_SEC", "60"))

_lock = threading.RLock()


class _Entry:  # simple container
    __slots__ = ("created", "data", "msgpack_bytes")

    def __init__(self, data: Any, msgpack_bytes: bytes):
        self.created = time.time()
        self.data = data
        self.msgpack_bytes = msgpack_bytes


_store: "OrderedDict[str, _Entry]" = OrderedDict()


def _evict_if_needed():
    while len(_store) > _max:
        _store.popitem(last=False)


def _is_expired(ent: _Entry) -> bool:
    return (time.time() - ent.created) > _ttl


def _key(method: str, path: str, payload: Any) -> str:
    h = hashlib.sha256()
    h.update(method.encode())
    h.update(b"\n")
    h.update(path.encode())
    h.update(b"\n")
    try:
        h.update(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    except Exception:
        h.update(repr(payload).encode())
    return h.hexdigest()


def get_or_set(method: str, path: str, payload: Any, builder: Callable[[], Any]) -> _Entry:
    if _disabled:
        data = builder()
        return _Entry(data, msgpack.packb(data, use_bin_type=True))
    k = _key(method, path, payload)
    with _lock:
        ent = _store.get(k)
        if ent and not _is_expired(ent):
            _store.move_to_end(k, last=True)
            cache_metrics.increment("response_hits")
            return ent
        else:
            cache_metrics.increment("response_misses")
    # Miss or expired
    data = builder()
    mp = msgpack.packb(data, use_bin_type=True)
    new_ent = _Entry(data, mp)
    if not _disabled:
        with _lock:
            _store[k] = new_ent
            _store.move_to_end(k, last=True)
            _evict_if_needed()
    return new_ent


def respond_cached(request: Request, method: str, path: str, payload: Any, builder: Callable[[], Any]) -> Response:
    ent = get_or_set(method, path, payload, builder)
    accept = request.headers.get("accept", "")
    if "application/msgpack" in accept.lower():
        return Response(content=ent.msgpack_bytes, media_type="application/msgpack")
    return JSONResponse(content=ent.data)


def cache_stats() -> dict[str, Any]:
    if _disabled:
        return {"disabled": True, "size": 0, "max": _max, "ttl_sec": _ttl}
    with _lock:
        base: dict[str, Any] = {"disabled": False, "size": len(_store), "max": _max, "ttl_sec": _ttl}
        try:
            base.update(cache_metrics.snapshot(prefix_filter="response_"))
        except Exception:
            pass
        return base
