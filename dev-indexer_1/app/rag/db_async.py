"""Async DB access layer using asyncpg.

Opt-in via env ASYNC_DB=1. Provides get_pool(), fetch, fetchrow, execute helpers.
"""
from __future__ import annotations
import os
import asyncio
from typing import Any, Sequence

try:
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover
    asyncpg = None  # type: ignore

_pool: Any | None = None
_lock = asyncio.Lock()


async def get_pool():
    global _pool
    if _pool is not None:
        return _pool
    if asyncpg is None:
        raise RuntimeError("asyncpg not installed")
    dsn = os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
    if not dsn:
        raise RuntimeError("DATABASE_URL/DB_DSN missing")
    async with _lock:
        if _pool is None:
            _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=int(os.getenv("DB_POOL_MAX", "5")))  # type: ignore
    return _pool


async def fetch(sql: str, *args) -> Sequence[asyncpg.Record]:  # type: ignore
    pool = await get_pool()
    async with pool.acquire() as conn:  # type: ignore
        return await conn.fetch(sql, *args)


async def fetchrow(sql: str, *args):  # type: ignore
    pool = await get_pool()
    async with pool.acquire() as conn:  # type: ignore
        return await conn.fetchrow(sql, *args)


async def execute(sql: str, *args):  # type: ignore
    pool = await get_pool()
    async with pool.acquire() as conn:  # type: ignore
        return await conn.execute(sql, *args)


__all__ = ["fetch", "fetchrow", "execute", "get_pool"]
