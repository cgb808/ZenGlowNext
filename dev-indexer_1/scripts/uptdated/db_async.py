"""Async DB Client & Pool Lifecycle (Feature-Flagged)

Enabled when DB_ASYNC_POOL=1 (default off). Provides an AsyncConnectionPool-based
vector search client for pgvector. Keeps legacy sync DBClient available until
migration completes.
"""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import Any, List, Dict, AsyncIterator

from fastapi import FastAPI, HTTPException
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

_POOL_ATTR = "db_pool"

class AsyncDBClient:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

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

@asynccontextmanager
def pooled_lifespan(app: FastAPI) -> AsyncIterator[None]:
    if os.getenv("APP_TEST_MODE") == "1" and os.getenv("SKIP_DB", "1") == "1":
        yield
        return
    use_async = os.getenv("DB_ASYNC_POOL", "0") == "1"
    pool = None
    if use_async:
        pool = AsyncConnectionPool(
            conninfo=os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/rag_db"),
            min_size=int(os.getenv("DB_POOL_MIN", 2)),
            max_size=int(os.getenv("DB_POOL_MAX", 10)),
            timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
        )
        setattr(app.state, _POOL_ATTR, pool)
    try:
        yield
    finally:
        if pool:
            await pool.close()

# Dependency provider (FastAPI) style helper

def get_async_db_client(app: FastAPI) -> AsyncDBClient:
    pool = getattr(app.state, _POOL_ATTR, None)
    if not pool:
        raise HTTPException(status_code=503, detail="DB pool unavailable")
    return AsyncDBClient(pool)

__all__ = ["AsyncDBClient", "pooled_lifespan", "get_async_db_client"]
