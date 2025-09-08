"""Lightweight task queue abstraction (in-proc or Redis list) for fire-and-forget work.

Env:
  TASK_QUEUE_REDIS=1 enables Redis list at key TASK_QUEUE_KEY (default zenglow:tasks)
  REDIS_URL must be set for Redis mode.

Fallback: in-memory deque processed by a background thread.
This is intentionally minimal (not a full Celery replacement).
"""
from __future__ import annotations
import os
import threading
import time
import json
import logging
from collections import deque
from typing import Callable, Dict, Any
from . import redis_backend, cache_metrics

_queue = deque()
_lock = threading.RLock()
_stop = False
_worker_started = False
_handlers: Dict[str, Callable[[dict[str, Any]], None]] = {}
_redis_mode = False
_redis_key = os.getenv("TASK_QUEUE_KEY", "zenglow:tasks")
_logger = logging.getLogger("task_queue")
_base_backoff = float(os.getenv("TASK_QUEUE_BACKOFF_BASE", "0.25"))
_backoff_factor = float(os.getenv("TASK_QUEUE_BACKOFF_FACTOR", "2.0"))
_max_backoff = float(os.getenv("TASK_QUEUE_BACKOFF_MAX", "10.0"))


def register(task_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
    _handlers[task_type] = handler


def enqueue(task_type: str, payload: dict[str, Any], retries: int = 3, next_attempt: float | None = None) -> None:
    """Enqueue a task.

    retries: number of attempts (initial). On handler failure we decrement and requeue
    until it reaches 0, then send to dead-letter queue.
    """
    item = {
        "type": task_type,
        "payload": payload,
        "ts": time.time(),
        "retries": int(retries),
        "next_attempt": float(next_attempt) if next_attempt else time.time(),
        "initial_retries": int(retries),
    }
    if _redis_mode and redis_backend.enabled():
        try:
            from app.core.redis_backend import _serialize  # type: ignore
        except Exception:
            _serialize = lambda v: json.dumps(v).encode()
        try:
            redis_backend.set(f"task:last:{task_type}", payload, ttl=600)  # lightweight marker
            # push to list via low-level client if available
            from app.core.redis_backend import _client  # type: ignore
            if _client is not None:  # type: ignore
                _client.lpush(_redis_key, _serialize(item))  # type: ignore[attr-defined]
                return
        except Exception:
            pass  # fallback to memory
    with _lock:
        _queue.append(item)
        cache_metrics.increment("taskq_enqueued")
    _logger.debug("task_enqueued", extra={"task_type": task_type, "retries": retries})


def _to_dead_letter(item: dict[str, Any]):
    # Redis-backed DLQ else drop into in-proc queue (not processed) for optional later inspection
    if _redis_mode and redis_backend.enabled():
        try:
            from app.core.redis_backend import _client, _serialize  # type: ignore
            if _client is not None:  # type: ignore
                dlq_key = f"{_redis_key}:dead-letter"
                _client.lpush(dlq_key, _serialize(item))  # type: ignore[attr-defined]
                cache_metrics.increment("taskq_dlq")
                return
        except Exception:
            pass
    # fallback: metric only
    try:
        cache_metrics.increment("taskq_dlq")
    except Exception:
        pass


def _requeue(item: dict[str, Any]):
    if _redis_mode and redis_backend.enabled():
        try:
            from app.core.redis_backend import _client, _serialize  # type: ignore
            if _client is not None:  # type: ignore
                _client.lpush(_redis_key, _serialize(item))  # type: ignore[attr-defined]
                cache_metrics.increment("taskq_requeue")
                return
        except Exception:
            pass
    with _lock:
        _queue.append(item)
        cache_metrics.increment("taskq_requeue")
    _logger.debug("task_requeued", extra={"task_type": item.get("type"), "retries": item.get("retries")})


def _compute_backoff(item: dict[str, Any]) -> float:
    # Exponential based on attempts used
    init = max(1, int(item.get("initial_retries", 1)))
    remaining = int(item.get("retries", 0))
    used = init - remaining
    delay = _base_backoff * (_backoff_factor ** max(0, used - 1))
    return min(delay, _max_backoff)


def _process_item(item: dict[str, Any]):
    t = item.get("type")
    handler = _handlers.get(t)
    if not handler:
        return
    try:
        handler(item.get("payload") or {})
    except Exception as e:  # noqa: BLE001
        _logger.warning("task_failed", extra={"task_type": t, "error": str(e)})
        try:
            cache_metrics.increment("taskq_fail")
        except Exception:
            pass
        retries = int(item.get("retries", 0)) - 1
        item["retries"] = retries
        if retries > 0:
            delay = _compute_backoff(item)
            item["next_attempt"] = time.time() + delay
            _requeue(item)
        else:
            _logger.error("task_dlq", extra={"task_type": t})
            _to_dead_letter(item)


def _thread_loop():  # in-proc worker
    while not _stop:
        item = None
        if _redis_mode and redis_backend.enabled():
            try:
                from app.core.redis_backend import _client, _deserialize  # type: ignore
                if _client is not None:
                    raw = _client.rpop(_redis_key)  # type: ignore[attr-defined]
                    if raw:
                        try:
                            import msgpack  # type: ignore
                            obj = msgpack.loads(raw, raw=False)  # type: ignore
                        except Exception:
                            try:
                                obj = json.loads(raw.decode())
                            except Exception:
                                obj = None
                        if isinstance(obj, dict):
                            item = obj
            except Exception:
                pass
        if item is None:
            with _lock:
                if _queue:
                    # Peek first item; if next_attempt in future, skip processing
                    if _queue[0].get("next_attempt", 0) > time.time():
                        pass
                    else:
                        item = _queue.popleft()
        if item is None:
            time.sleep(0.05)
            continue
    _process_item(item)
        try:
            cache_metrics.increment("taskq_processed")
        except Exception:
            pass


def start():
    global _worker_started, _redis_mode
    if _worker_started:
        return
    _redis_mode = os.getenv("TASK_QUEUE_REDIS", "0").lower() in {"1", "true", "yes"}
    th = threading.Thread(target=_thread_loop, name="taskq-worker", daemon=True)
    th.start()
    _worker_started = True


__all__ = ["enqueue", "register", "start"]
