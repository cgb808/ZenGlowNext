"""Redis Streams helper utilities for distributed RAG pipeline.

Provides minimal publish and consume helpers with lazy Redis client creation.
"""
from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, List, Optional, Iterable

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None  # type: ignore

_client: Any = None


def _get_client():  # pragma: no cover - thin
    global _client
    if _client is not None:
        return _client
    if redis is None:
        return None
    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        _client = redis.Redis(host=host, port=port, decode_responses=True)
    except Exception:
        _client = None
    return _client


def publish(stream: str, data: Dict[str, Any]) -> Optional[str]:
    c = _get_client()
    if c is None:
        return None
    try:
        return c.xadd(stream, {"data": json.dumps(data)})  # type: ignore
    except Exception:
        return None


def read_blocks(stream: str, last_id: str = "$", block_ms: int = 1000):
    """Blocking read yielding new entries after last_id.

    Caller supplies last_id = '0' to read from beginning, or uses the id of last
    processed entry. Uses XREAD with block.
    """
    c = _get_client()
    if c is None:
        return
    current_id = last_id
    while True:
        try:
            res = c.xread({stream: current_id}, block=block_ms, count=10)
            if not res:
                yield None
                continue
            for _stream_name, entries in res:
                for entry_id, fields in entries:
                    current_id = entry_id
                    raw = fields.get("data")
                    try:
                        obj = json.loads(raw) if raw else None
                    except Exception:
                        obj = None
                    yield {"id": entry_id, "data": obj}
        except Exception:
            yield None
            time.sleep(0.5)
