"""Async DB Client & Pool Lifecycle (Feature-Flagged)

Enabled when DB_ASYNC_POOL=1 (default off). Provides an AsyncConnectionPool-based
vector search client for pgvector. Keeps legacy sync DBClient available until
migration completes.
"""
from __future__ import annotations
import os
from typing import Any, List, Dict, AsyncIterator

from fastapi import FastAPI, HTTPException
try:  # optional dependency
    from psycopg_pool import AsyncConnectionPool
except Exception:  # pragma: no cover - optional
    AsyncConnectionPool = None  # type: ignore
from psycopg.rows import dict_row

_POOL_ATTR = "db_pool"

class AsyncDBClient:
    def __init__(self, pool):  # type: ignore[no-untyped-def]
        self.pool = pool

    async def execute_query(self, sql: Any, params: Any = None, fetch: str = "none") -> Any:
        """Execute an arbitrary SQL against the pool.

        Args:
            sql: SQL statement to run.
            params: Optional parameters for the SQL.
            fetch: one|all|none controls what is returned.

        Returns:
            Depending on `fetch`, returns a single row (tuple or dict_row), a list of rows,
            or None. This is intended for light-weight admin/health queries.
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if fetch == "one":
                    return await cur.fetchone()
                if fetch == "all":
                    return await cur.fetchall()
                return None

    async def vector_search(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not embedding:
            return []
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT id, chunk, metadata, (embedding <-> %s)::float AS distance
                    FROM doc_embeddings
                    ORDER BY embedding <-> %s
                    LIMIT %s
                    """,
                    (embedding, embedding, top_k),
                )
                rows = await cur.fetchall() or []
                return [
                    {
                        "id": r.get("id"),
                        "text": r.get("chunk"),
                        "metadata": r.get("metadata"),
                        "distance": r.get("distance") or 0.0,
                    }
                    for r in rows
                ]

    async def stats(self) -> Dict[str, Any]:
        pool = self.pool
        q = getattr(pool, "_queue", None)
        try:
            qsize = q.qsize() if q else None
        except Exception:
            qsize = None
        return {
            "min_size": getattr(pool, "min_size", None),
            "max_size": getattr(pool, "max_size", None),
            "open": getattr(pool, "open", None),
            "running": getattr(pool, "running", None),
            "queue_size": qsize,
        }

async def pooled_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan handler that conditionally creates an AsyncConnectionPool.

    Implemented as an async generator function (no decorator) to satisfy FastAPI's
    expected signature and allow `await` usage correctly.
    """
    pool = None
    try:
        if os.getenv("APP_TEST_MODE") == "1" and os.getenv("SKIP_DB", "1") == "1":
            yield
            return
        if os.getenv("DB_ASYNC_POOL", "0") == "1" and AsyncConnectionPool is not None:
            pool = AsyncConnectionPool(
                conninfo=os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_db"),
                min_size=int(os.getenv("DB_POOL_MIN", 2)),
                max_size=int(os.getenv("DB_POOL_MAX", 10)),
                timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
            )
            setattr(app.state, _POOL_ATTR, pool)
        yield
    finally:
        if pool is not None:
            await pool.close()

# Dependency provider (FastAPI) style helper

def get_async_db_client(app: FastAPI) -> AsyncDBClient:
    pool = getattr(app.state, _POOL_ATTR, None)
    if not pool:
        raise HTTPException(status_code=503, detail="DB pool unavailable")
    return AsyncDBClient(pool)

__all__ = ["AsyncDBClient", "pooled_lifespan", "get_async_db_client"]
