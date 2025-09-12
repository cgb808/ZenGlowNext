"""Typed metrics facade (Task 7).

Goals:
  * Provide minimal, typed, dependency-light API for counters, histograms, and timers.
  * Allow seamless no-op operation when a real backend (Prometheus, StatsD, OTEL) is absent.
  * Keep in-memory aggregates for tests and lightweight introspection.

Public API:
  counter(name: str, inc: float = 1.0, **labels) -> None
  observe(name: str, value: float, **labels) -> None   # histogram/summary style
  timer(name: str, **labels) -> TimerContext            # with .stop() / context manager

Implementation notes:
  * For simplicity we aggregate by (name, sorted(labels.items())) key.
  * Counters: stored cumulative value.
  * Observations: stored list of values (bounded by MAX_OBS_PER_KEY for memory safety).
  * Timers: record elapsed ms (float) via observe(name, ms, kind="timer").

Future extensions (not implemented now):
  * Exposition format conversion (Prometheus text format) via an exporter.
  * Bucketing / quantiles summarization.
  * Async flush hooks.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

__all__ = ["counter", "observe", "timer", "snapshot", "TimerContext"]

_LOCK = threading.Lock()
_COUNTERS: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], float] = {}
_OBS: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], List[float]] = {}
_MAX_OBS_PER_KEY = int(os.getenv("METRICS_MAX_OBS", "500"))


def _k(name: str, labels: Dict[str, Any]) -> Tuple[str, Tuple[Tuple[str, Any], ...]]:
    return name, tuple(sorted(labels.items()))


def counter(name: str, inc: float = 1.0, **labels) -> None:
    with _LOCK:
        key = _k(name, labels)
        _COUNTERS[key] = _COUNTERS.get(key, 0.0) + inc


def observe(name: str, value: float, **labels) -> None:
    with _LOCK:
        key = _k(name, labels)
        arr = _OBS.get(key)
        if arr is None:
            arr = []
            _OBS[key] = arr
        arr.append(value)
        if len(arr) > _MAX_OBS_PER_KEY:
            # Drop oldest half to curb unbounded growth
            del arr[: len(arr) // 2]


@dataclass
class TimerContext:
    name: str
    labels: Dict[str, Any]
    start: float
    stopped: bool = False

    def stop(self) -> float:
        if not self.stopped:
            self.stopped = True
            elapsed_ms = (time.time() - self.start) * 1000.0
            observe(self.name, elapsed_ms, **self.labels)
            return elapsed_ms
        return 0.0

    # Context manager protocol
    def __enter__(self) -> "TimerContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple
        self.stop()

    # Convenience accessor for immediate ms (even if not stopped)
    def ms(self) -> float:
        return (time.time() - self.start) * 1000.0


def timer(name: str, **labels) -> TimerContext:
    return TimerContext(name=name, labels=labels, start=time.time())


def snapshot() -> dict:
    with _LOCK:
        counters = {
            f"{n}|{dict(lbls)}": v for (n, lbls), v in _COUNTERS.items()
        }
        observations = {
            f"{n}|{dict(lbls)}": list(vals) for (n, lbls), vals in _OBS.items()
        }
    return {"counters": counters, "observations": observations}
