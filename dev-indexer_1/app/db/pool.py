"""In-process PostgreSQL connection pool.

Lightweight wrapper around psycopg_pool.ConnectionPool with lazy singleton
construction and a minimal DBClient helper. The goal is to keep adoption
friction very low while allowing later swap to an external pooler (pgBouncer)
simply by pointing POSTGRES_DSN at its port.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, Any, Iterable

try:
    from psycopg_pool import ConnectionPool  # type: ignore
except Exception:  # pragma: no cover - library missing
    ConnectionPool = Any  # type: ignore

_pool_lock = threading.Lock()
_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool | None:
    """Return global pool, creating it lazily if dsn is present.

    If POSTGRES_DSN isn't set, returns None so callers can fail soft.
    """
    global _pool
    if _pool is not None:
        return _pool
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        return None
    with _pool_lock:
        if _pool is None:
            # Min conservative defaults; tweak via env if needed
            kwargs: dict[str, Any] = {}
            min_size = os.getenv("PG_POOL_MIN")
            max_size = os.getenv("PG_POOL_MAX")
            if min_size:
                kwargs["min_size"] = int(min_size)
            if max_size:
                kwargs["max_size"] = int(max_size)
            try:
                _pool = ConnectionPool(dsn, **kwargs)  # type: ignore[arg-type]
            except Exception:
                _pool = None
    return _pool


class DBClient:
    """Thin client borrowing connections from the in-process pool.

    Usage:
        from app.db.pool import db
        rows = db.query("SELECT 1")
    """

    def __init__(self, pool_getter: Callable[[], ConnectionPool | None]):
        self._pool_getter = pool_getter

    # Simple query helpers (sync). Extend / wrap for async if needed later.
    def execute(self, sql: str, *params) -> None:
        pool = self._pool_getter()
        if pool is None:  # fail soft
            return None
        with pool.connection() as conn:  # type: ignore[union-attr]
            with conn.cursor() as cur:  # type: ignore[call-arg]
                cur.execute(sql, params)

    def fetchall(self, sql: str, *params) -> list[tuple]:
        pool = self._pool_getter()
        if pool is None:
            return []
        with pool.connection() as conn:  # type: ignore[union-attr]
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def fetchone(self, sql: str, *params):
        pool = self._pool_getter()
        if pool is None:
            return None
        with pool.connection() as conn:  # type: ignore[union-attr]
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()


db = DBClient(get_pool)


def pool_stats() -> dict[str, Any]:  # pragma: no cover - trivial
    pool = get_pool()
    if pool is None:
        return {"enabled": False}
    try:
        return {
            "enabled": True,
            "min_size": getattr(pool, "min_size", None),
            "max_size": getattr(pool, "max_size", None),
            "opened": getattr(pool, "opened", None),
            "checked_out": getattr(pool, "checked_out", None),
        }
    except Exception:
        return {"enabled": True, "error": "stats_unavailable"}
