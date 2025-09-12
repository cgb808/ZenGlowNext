"""Asynchronous DB client & pool (Step 1 migration target).

Centralizes a single AsyncConnectionPool for the application. Provides
`get_async_db_client` FastAPI dependency helper.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List
from psycopg_pool import AsyncConnectionPool  # type: ignore
from psycopg.rows import dict_row  # type: ignore


class AsyncDBClient:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def vector_search(
        self,
        embedding: List[float],
        top_k: int = 5,
        filters: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        if not embedding or not self.pool:
            return []
        where_sql = ""
        params: list[Any] = [embedding, embedding, top_k]
        if filters:
            clauses = []
            for k, v in filters.items():
                clauses.append(f"metadata @> %s")
                params.append(f'{{"{k}": "{v}"}}')
            where_sql = " WHERE " + " AND ".join(clauses)
        sql_query = (
            "SELECT id, chunk AS text, metadata, (embedding <-> %s)::float AS distance "
            "FROM doc_embeddings"
            + where_sql
            + " ORDER BY embedding <-> %s LIMIT %s"
        )
        async with self.pool.connection() as conn:  # type: ignore[attr-defined]
            async with conn.cursor(row_factory=dict_row) as cur:  # type: ignore
                await cur.execute(sql_query, params)
                rows = await cur.fetchall() or []
                return [dict(r) for r in rows]

    async def lexical_search(
        self, query: str, top_k: int = 10, filters: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        # Basic full-text search assuming a tsvector column "chunk_tsv" exists (optional)
        where_sql = ""
        params: list[Any] = [query, top_k]
        if filters:
            clauses = []
            for k, v in filters.items():
                clauses.append("metadata @> %s")
                params.append(f'{{"{k}": "{v}"}}')
            where_sql = " AND " + " AND ".join(clauses)
        sql_query = (
            "SELECT id, chunk AS text, metadata, 0.0::float AS distance, "
            "ts_rank_cd(chunk_tsv, plainto_tsquery(%s)) AS ft_score "
            "FROM doc_embeddings WHERE chunk_tsv @@ plainto_tsquery(%s)"
        )
        # Duplicate query param for both rank + filter; adjust as needed
        params.insert(1, query)
        if where_sql:
            sql_query += where_sql
        sql_query += " ORDER BY ft_score DESC LIMIT %s"
        async with self.pool.connection() as conn:  # type: ignore[attr-defined]
            async with conn.cursor(row_factory=dict_row) as cur:  # type: ignore
                await cur.execute(sql_query, params)
                rows = await cur.fetchall() or []
                return [dict(r) for r in rows]

    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        top_k: int = 10,
        filters: Dict[str, Any] | None = None,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        vec_rows = await self.vector_search(embedding, top_k=top_k, filters=filters)
        lex_rows = await self.lexical_search(query, top_k=top_k, filters=filters)
        # Reciprocal Rank Fusion
        scores: dict[Any, float] = {}
        meta: dict[Any, dict] = {}
        for rank, r in enumerate(vec_rows):
            doc_id = r.get("id")
            if doc_id is None:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            meta.setdefault(doc_id, r)
        for rank, r in enumerate(lex_rows):
            doc_id = r.get("id")
            if doc_id is None:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            if doc_id not in meta:
                meta[doc_id] = r
        fused = [
            {**meta[d], "fusion_score": s} for d, s in scores.items()
        ]
        fused.sort(key=lambda x: x["fusion_score"], reverse=True)
        return fused[:top_k]

    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        async with self.pool.connection() as conn:  # type: ignore[attr-defined]
            async with conn.cursor(row_factory=dict_row) as cur:  # type: ignore
                await cur.execute(query, params)
                return [dict(r) for r in (await cur.fetchall())]


_pool: AsyncConnectionPool | None = None


async def init_async_pool() -> AsyncConnectionPool | None:
    global _pool
    if _pool is not None:
        return _pool
    dsn = (
        os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("SUPABASE_DIRECT_URL")
        or os.getenv("POSTGRES_DSN")
    )
    if not dsn:
        return None
    min_size = int(os.getenv("ASYNC_PG_POOL_MIN", "1"))
    max_size = int(os.getenv("ASYNC_PG_POOL_MAX", "10"))
    _pool = AsyncConnectionPool(dsn, min_size=min_size, max_size=max_size)  # type: ignore[arg-type]
    return _pool


def get_async_db_client() -> AsyncDBClient | None:
    if _pool is None:
        return None
    return AsyncDBClient(_pool)
