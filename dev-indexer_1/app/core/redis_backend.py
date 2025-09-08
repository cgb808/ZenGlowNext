"""Thin async Redis backend helper with graceful fallback.

Environment flags:
  REDIS_URL: if set, enables redis usage.
  REDIS_DISABLED: if '1' forces disable even if URL present.

Provides minimal get/set, mget, set_with_ttl with msgpack serialization.
Falls back to in-process operations when redis not available or errors occur.
"""
from __future__ import annotations
import os
import threading
import time
from typing import Any, Iterable, Sequence

try:  # optional dependency pattern
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional
    redis = None  # type: ignore

try:
    import msgpack  # type: ignore
except Exception:  # pragma: no cover
    msgpack = None  # type: ignore

_lock = threading.RLock()
_client: Any | None = None
_enabled = False
_had_error = False
_circuit_open_until = 0.0
_circuit_backoff_sec = 15.0


def _init() -> None:
    global _client, _enabled
    if _client or _enabled:  # already attempted
        return
    if os.getenv("REDIS_DISABLED") in {"1", "true", "yes"}:
        return
    url = os.getenv("REDIS_URL")
    if not url or redis is None:
        return
    try:
        _client = redis.Redis.from_url(url, socket_timeout=0.25, socket_connect_timeout=0.25)  # type: ignore
        # lightweight ping
        _client.ping()  # type: ignore
        _enabled = True
    except Exception:
        _client = None
        _enabled = False


def enabled() -> bool:
    if not _enabled:
        return False
    if _circuit_open_until and time.time() < _circuit_open_until:
        return False
    return True


def _serialize(value: Any) -> bytes:
    if msgpack is None:
        # Fallback simplistic; rely on str repr
        return str(value).encode()
    return msgpack.dumps(value, use_bin_type=True)  # type: ignore


def _deserialize(b: bytes | None) -> Any:
    if b is None:
        return None
    if msgpack is None:
        return b.decode(errors="ignore")
    try:
        return msgpack.loads(b, raw=False)  # type: ignore
    except Exception:
        return None


def get(key: str) -> Any:
    _init()
    if not enabled():
        return None
    try:
        v = _client.get(key)  # type: ignore[attr-defined]
        return _deserialize(v) if v is not None else None
    except Exception:
        _trip_circuit()
        return None


def set(key: str, value: Any, ttl: int | None = None) -> None:
    _init()
    if not enabled():
        return
    try:
        data = _serialize(value)
        if ttl is not None:
            _client.setex(key, ttl, data)  # type: ignore[attr-defined]
        else:
            _client.set(key, data)  # type: ignore[attr-defined]
    except Exception:
        _trip_circuit()


def mget(keys: Sequence[str]) -> list[Any | None]:
    _init()
    if not enabled():
        return [None] * len(keys)
    try:
        raw = _client.mget(list(keys))  # type: ignore[attr-defined]
        return [_deserialize(v) if v is not None else None for v in raw]
    except Exception:
        _trip_circuit()
        return [None] * len(keys)


def get_or_set(key: str, builder, ttl: int | None = None):
    v = get(key)
    if v is not None:
        return v
    v = builder()
    set(key, v, ttl=ttl)
    return v


def _trip_circuit():
    global _circuit_open_until
    _circuit_open_until = time.time() + _circuit_backoff_sec


__all__ = [
    "enabled",
    "get",
    "set",
    "mget",
    "get_or_set",
]
