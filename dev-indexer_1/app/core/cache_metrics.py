"""Simple in-process integer counters for cache-related metrics."""
from __future__ import annotations
import threading
from typing import Dict

_lock = threading.Lock()
_counters: Dict[str, int] = {}


def increment(name: str, value: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + value


def snapshot(prefix_filter: str | None = None) -> dict[str, int]:
    with _lock:
        if prefix_filter is None:
            return dict(_counters)
        return {k: v for k, v in _counters.items() if k.startswith(prefix_filter)}
