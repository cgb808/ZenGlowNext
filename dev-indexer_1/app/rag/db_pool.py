"""Very small DB client pool stub (sync placeholder).

Future: replace DBClient with async driver + real pool.
"""
from __future__ import annotations
import threading
from typing import List
from .db_client import DBClient

_lock = threading.RLock()
_pool: List[DBClient] = []
_max = 4


def acquire() -> DBClient:
    with _lock:
        if _pool:
            return _pool.pop()
    return DBClient()


def release(client: DBClient) -> None:
    try:
        with _lock:
            if len(_pool) < _max:
                _pool.append(client)
                return
        client.close()
    except Exception:
        pass

__all__ = ["acquire", "release"]
