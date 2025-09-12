"""Binary presence detection with lightweight metadata caching.

Purpose (Task 6): Avoid repeated ``shutil.which`` probes (costly on some container images)
and expose an introspection endpoint (/config/binaries) for ops / UI.

API (public):
    ensure_cached(name: str) -> bool
            Populate / refresh cache entry (subject to TTL) and return availability.
    have(name: str) -> bool
            Convenience alias (calls ensure_cached).
    get_all() -> dict[str, dict]
            Shallow copy of internal cache mapping name -> metadata.

Cache entry shape (values are simple JSON-serialisable types):
    {
        'found': bool,
        'path': str | None,
        'checked_at': float,   # epoch seconds
        'attempts': int        # number of detection attempts (>=1 when present)
    }

TTL Strategy:
    Binary presence rarely changes at runtime, but allow a small TTL so that
    newly installed sidecars (e.g. via package manager inside container) can be
    detected without restart. Defaults to 30s (configurable by BIN_CACHE_TTL env).
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from typing import Dict, Any

_cache: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

try:
    _TTL_DEFAULT = int(os.getenv("BIN_CACHE_TTL", "30"))
except Exception:  # pragma: no cover - defensive
    _TTL_DEFAULT = 30


def _stale(entry: Dict[str, Any]) -> bool:
    return (time.time() - entry.get("checked_at", 0)) > _TTL_DEFAULT


def _detect(name: str) -> Dict[str, Any]:
    path = shutil.which(name)
    return {
        "found": path is not None,
        "path": path,
        "checked_at": time.time(),
        "attempts": 1,
    }


def ensure_cached(name: str) -> bool:
    """Ensure metadata for ``name`` exists (refreshing if stale); return availability."""
    entry = _cache.get(name)
    if entry is not None and not _stale(entry):
        return bool(entry["found"])  # fast path
    with _lock:
        entry = _cache.get(name)
        if entry is None:
            _cache[name] = _detect(name)
        else:
            if _stale(entry):
                new_path = shutil.which(name)
                entry.update(
                    {
                        "found": new_path is not None,
                        "path": new_path,
                        "checked_at": time.time(),
                        "attempts": int(entry.get("attempts", 0)) + 1,
                    }
                )
        return bool(_cache[name]["found"])  # type: ignore[index]


def have(name: str) -> bool:
    return ensure_cached(name)


def get_all() -> Dict[str, Dict[str, Any]]:
    with _lock:
        # shallow copy of each entry to avoid external mutation
        return {k: v.copy() for k, v in _cache.items()}
