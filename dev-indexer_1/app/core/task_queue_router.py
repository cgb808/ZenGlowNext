from __future__ import annotations
import os
import json
from fastapi import APIRouter
from . import redis_backend, cache_metrics
from . import task_queue

router = APIRouter(prefix="/internal/taskq", tags=["taskq"])

_redis_key = os.getenv("TASK_QUEUE_KEY", "zenglow:tasks")


@router.get("/dlq")
def dlq_peek(limit: int = 20):  # pragma: no cover - simple
    if not redis_backend.enabled():
        return {"enabled": False, "items": [], "count": 0}
    try:
        from app.core.redis_backend import _client  # type: ignore
        if _client is None:  # type: ignore
            return {"enabled": False, "items": [], "count": 0}
        dlq_key = f"{_redis_key}:dead-letter"
        # Use LRANGE for peek (non-destructive)
        raw_items = _client.lrange(dlq_key, 0, max(0, limit - 1))  # type: ignore[attr-defined]
        items = []
        for r in raw_items:
            try:
                import msgpack  # type: ignore
                try:
                    obj = msgpack.loads(r, raw=False)  # type: ignore
                except Exception:
                    obj = json.loads(r.decode())
                items.append(obj)
            except Exception:
                continue
        count = _client.llen(dlq_key)  # type: ignore[attr-defined]
        return {"enabled": True, "items": items, "count": count}
    except Exception:
        return {"enabled": False, "items": [], "count": 0}

__all__ = ["router"]


@router.post("/dlq/requeue")
def dlq_requeue(limit: int = 10, reset_retries: int = 1):  # pragma: no cover - simple
    if not redis_backend.enabled():
        return {"enabled": False, "requeued": 0, "reason": "redis_disabled"}
    if limit <= 0:
        return {"enabled": True, "requeued": 0, "reason": "limit_le_zero"}
    try:
        from app.core.redis_backend import _client  # type: ignore
        if _client is None:  # type: ignore
            return {"enabled": False, "requeued": 0, "reason": "client_none"}
        dlq_key = f"{_redis_key}:dead-letter"
        requeued = 0
        # Since failures were LPUSHed, oldest are at tail; pop from tail for fairness
        import msgpack  # type: ignore
        for _ in range(limit):
            raw = _client.rpop(dlq_key)  # type: ignore[attr-defined]
            if not raw:
                break
            obj = None
            try:
                try:
                    obj = msgpack.loads(raw, raw=False)  # type: ignore
                except Exception:
                    obj = json.loads(raw.decode())
            except Exception:
                obj = None
            if not isinstance(obj, dict):
                continue
            # Re-enqueue with optional retry reset
            payload = obj.get("payload") or {}
            ttype = obj.get("type") or "unknown"
            retries = reset_retries if reset_retries >= 0 else obj.get("initial_retries", 1)
            task_queue.enqueue(ttype, payload, retries=retries)
            requeued += 1
        if requeued:
            try:
                cache_metrics.increment("taskq_dlq_requeue")
            except Exception:
                pass
        remaining = _client.llen(dlq_key)  # type: ignore[attr-defined]
        return {"enabled": True, "requeued": requeued, "remaining": remaining}
    except Exception as e:  # noqa: BLE001
        return {"enabled": False, "requeued": 0, "error": str(e)}


@router.post("/dlq/purge")
def dlq_purge(confirm: bool = False):  # pragma: no cover - simple
    if not confirm:
        return {"enabled": True, "purged": 0, "required": "confirm=true"}
    if not redis_backend.enabled():
        return {"enabled": False, "purged": 0, "reason": "redis_disabled"}
    try:
        from app.core.redis_backend import _client  # type: ignore
        if _client is None:  # type: ignore
            return {"enabled": False, "purged": 0, "reason": "client_none"}
        dlq_key = f"{_redis_key}:dead-letter"
        count = _client.llen(dlq_key)  # type: ignore[attr-defined]
        if count:
            _client.delete(dlq_key)  # type: ignore[attr-defined]
            try:
                cache_metrics.increment("taskq_dlq_purge")
            except Exception:
                pass
        return {"enabled": True, "purged": int(count)}
    except Exception as e:  # noqa: BLE001
        return {"enabled": False, "purged": 0, "error": str(e)}
