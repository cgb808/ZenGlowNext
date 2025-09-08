"""In-memory log buffer for lightweight UI/debug polling.

This module intentionally keeps a tiny surface:
- install(): attach a logging.Handler that writes to a ring buffer
- get_buffer(): return an object exposing since(since:int, limit:int)

The app expects each line to be a dict with an incrementing "id" field.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, List, Dict


class _RingBuffer:
    def __init__(self, capacity: int = 2000) -> None:
        self._cap = max(100, capacity)
        self._buf: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._next_id = 1

    def append(self, rec: logging.LogRecord) -> None:
        with self._lock:
            item: Dict[str, Any] = {
                "id": self._next_id,
                "ts": int(time.time() * 1000),
                "level": rec.levelname,
                "logger": rec.name,
                "msg": rec.getMessage(),
            }
            self._next_id += 1
            self._buf.append(item)
            if len(self._buf) > self._cap:
                # simple ring by trimming head
                overflow = len(self._buf) - self._cap
                if overflow > 0:
                    del self._buf[:overflow]

    def since(self, since_id: int = 0, limit: int = 400) -> List[Dict[str, Any]]:
        with self._lock:
            if since_id <= 0:
                return self._buf[-limit:].copy()
            # find first index with id > since_id
            # list is ordered by id asc
            start = 0
            for i in range(len(self._buf)):
                if self._buf[i]["id"] > since_id:
                    start = i
                    break
            return self._buf[start : start + max(0, limit)].copy()


class _BufferingHandler(logging.Handler):
    def __init__(self, buf: _RingBuffer) -> None:
        super().__init__()
        self._buf = buf

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - trivial
        try:
            self._buf.append(record)
        except Exception:
            # Avoid breaking logging on buffer issues
            pass


_GLOBAL_BUF = _RingBuffer()
_installed = False
_INSTALLED_LOCK = threading.Lock()


def install(level: int | None = None) -> None:
    """Install a global handler once.

    Safe to call multiple times.
    """
    global _installed
    with _INSTALLED_LOCK:
        if _installed:
            return
        handler = _BufferingHandler(_GLOBAL_BUF)
        handler.setLevel(level or logging.DEBUG)
        root = logging.getLogger()
        root.addHandler(handler)
        # Do not override existing level if already set by app
        if level is not None and root.level == logging.NOTSET:
            root.setLevel(level)
    _installed = True


def get_buffer() -> _RingBuffer:
    """Return the global ring buffer instance."""
    return _GLOBAL_BUF

