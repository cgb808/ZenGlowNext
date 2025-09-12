"""In-memory rolling log buffer for ad-hoc debugging in UI.

Stores last N log lines (formatted) with incremental ids. Frontend polls
`/logs/recent?since=<last_id>` to fetch new lines. Not suitable for multi-
process or production usage.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from threading import RLock
from typing import Any, Dict, List


@dataclass
class LogEntry:
    id: int
    ts: float
    level: str
    msg: str


class RollingBuffer:
    def __init__(self, capacity: int = 2000) -> None:
        self.capacity = capacity
        self._dq: deque[LogEntry] = deque(maxlen=capacity)
        self._lock = RLock()
        self._next = 1

    def append(self, level: str, msg: str) -> None:
        with self._lock:
            self._dq.append(
                LogEntry(id=self._next, ts=time.time(), level=level, msg=msg)
            )
            self._next += 1

    def since(self, last_id: int, limit: int = 500) -> List[Dict[str, Any]]:
        with self._lock:
            if last_id <= 0:
                items = list(self._dq)[-limit:]
            else:
                items = [e for e in self._dq if e.id > last_id][:limit]
            return [asdict(e) for e in items]


_BUF: RollingBuffer | None = None
_INSTALLED = False


def get_buffer() -> RollingBuffer:
    global _BUF
    if _BUF is None:
        _BUF = RollingBuffer()
    return _BUF


class BufferHandler(logging.Handler):  # pragma: no cover (side-effects)
    def emit(self, record: logging.LogRecord) -> None:
        try:
            buf = get_buffer()
            msg = self.format(record)
            buf.append(record.levelname, msg)
        except Exception:
            pass


def install(level: int = logging.INFO) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    h = BufferHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(h)
    if root.level > level:
        root.setLevel(level)
    _INSTALLED = True
