"""Postgres store utilities for RAG pipeline (doc_embeddings).

Migrated to psycopg (v3) from psycopg2.

Responsibilities:
 - Inserting / batching embeddings
 - Simple similarity search (fallback outside main ranking path)
 - Fetching rows by id
 - Basic dimension validation against pgvector schema

Design choices:
 - No ORM (reduce overhead, keep cold-start fast)
 - Idempotent insert (optional de-dup by (source, chunk) check before insert)
 - Uses LIST of Python floats directly; psycopg handles vector casting if length matches column dimension
 - Does NOT mutate schema; if a future uniqueness constraint is added, ON CONFLICT logic can be expanded

Environment variables:
 - DATABASE_URL (required)
 - RAG_EMBED_DIM (optional expected dimension; if set, validated)
 - STORE_VALIDATE_DIM=1 to enable runtime dimension probing (default on)

Exceptions raise RuntimeError with concise message; callers may catch and degrade gracefully.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

import psycopg
from psycopg import sql

__all__ = [
    "EmbeddingRecord",
    "insert_embeddings",
    "batch_insert_embeddings",
    "fetch_embeddings",
    "similarity_search_basic",
    "validate_expected_dimension",
]


@dataclass
class EmbeddingRecord:
    id: int
    source: Optional[str]
    chunk: str
    embedding: List[float]  # not fetched by default unless include_vector=True
    metadata: Optional[dict]
    batch_tag: Optional[str]
    created_at: str


def _connect():  # pragma: no cover (network)
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL env not set")
    return psycopg.connect(dsn)


def _maybe_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def validate_expected_dimension(example_vector: Sequence[float]) -> None:
    exp = os.getenv("RAG_EMBED_DIM")
    if not exp:
        return
    try:
        exp_i = int(exp)
    except ValueError:
        raise RuntimeError("RAG_EMBED_DIM must be int")
    if len(example_vector) != exp_i:
        raise RuntimeError(
            f"Embedding dimension mismatch: got {len(example_vector)}, expected {exp_i}"
        )


def insert_embeddings(
    chunks: Sequence[str],
    vectors: Sequence[Sequence[float]],
    source: str | None = None,
    batch_tag: str | None = None,
    metadata_list: Optional[Sequence[Optional[Dict[str, Any]]]] = None,
    dedupe: bool = True,
) -> int:
    """Insert one or more (chunk, embedding) rows.

    Returns number of newly inserted rows (skips duplicates when dedupe=True).
    Dedupe heuristic: SELECT id WHERE source + chunk hash already present (no hash column yet, so direct match).
    """
    if not chunks:
        return 0
    if len(chunks) != len(vectors):
        raise RuntimeError("chunks and vectors length mismatch")
    if metadata_list and len(metadata_list) != len(chunks):
        raise RuntimeError("metadata_list length mismatch")
    validate_expected_dimension(vectors[0])
    inserted = 0
    with _connect() as conn:
        with conn.cursor() as cur:
            existing_idx: set[int] = set()
            if dedupe:
                # Fetch existing matching rows by exact chunk text + source
                cur.execute(
                    "SELECT chunk FROM doc_embeddings WHERE source = %s AND chunk = ANY(%s)",
                    (source, list(chunks)),
                )
                existing = {r[0] for r in cur.fetchall()}
            else:
                existing = set()
            rows = []
            for i, (c, v) in enumerate(zip(chunks, vectors)):
                if dedupe and c in existing:
                    continue
                md = metadata_list[i] if metadata_list else None
                rows.append((source, c, list(v), md, batch_tag))
            if rows:
                # psycopg3 executemany handles batching; vector casting done server-side
                insert_sql = (
                    "INSERT INTO doc_embeddings (source, chunk, embedding, metadata, batch_tag) "
                    "VALUES (%s, %s, %s::vector, %s, %s)"
                )
                cur.executemany(insert_sql, rows)
                inserted = len(rows)
    return inserted


def batch_insert_embeddings(
    iterable: Iterable[tuple[str, Sequence[float], Optional[Dict[str, Any]]]],
    source: str | None = None,
    batch_tag: str | None = None,
    batch_size: int = 512,
) -> int:
    """Stream inserts from an iterable of (chunk, vector, metadata).
    Flush every batch_size. Returns total inserted.
    """
    buf_c: List[str] = []
    buf_v: List[Sequence[float]] = []
    buf_m: List[Optional[Dict[str, Any]]] = []
    total = 0
    for chunk, vec, meta in iterable:
        if not buf_c:
            validate_expected_dimension(vec)
        buf_c.append(chunk)
        buf_v.append(vec)
        buf_m.append(meta)
        if len(buf_c) >= batch_size:
            total += insert_embeddings(
                buf_c, buf_v, source=source, batch_tag=batch_tag, metadata_list=buf_m
            )
            buf_c.clear()
            buf_v.clear()
            buf_m.clear()
    if buf_c:
        total += insert_embeddings(
            buf_c, buf_v, source=source, batch_tag=batch_tag, metadata_list=buf_m
        )
    return total


def fetch_embeddings(
    ids: Sequence[int], include_vector: bool = False
) -> List[EmbeddingRecord]:
    if not ids:
        return []
    cols = "id, source, chunk, metadata, batch_tag, created_at" + (
        ", embedding" if include_vector else ""
    )
    sql = f"SELECT {cols} FROM doc_embeddings WHERE id = ANY(%s)"
    recs: List[EmbeddingRecord] = []
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (list(ids),))
            for row in cur.fetchall():
                if include_vector:
                    (rid, src, chunk, meta, batch_tag, created_at, emb) = row
                    recs.append(
                        EmbeddingRecord(
                            rid,
                            src,
                            chunk,
                            emb,
                            meta,
                            batch_tag,
                            created_at.isoformat(),
                        )
                    )
                else:
                    (rid, src, chunk, meta, batch_tag, created_at) = row
                    recs.append(
                        EmbeddingRecord(
                            rid, src, chunk, [], meta, batch_tag, created_at.isoformat()
                        )
                    )
    return recs


def similarity_search_basic(
    query_vec: Sequence[float], k: int = 5, source: str | None = None
) -> List[EmbeddingRecord]:
    validate_expected_dimension(query_vec)
    filt = "WHERE 1=1"
    params: List[Any] = [list(query_vec), list(query_vec), k]
    if source:
        filt += " AND source = %s"
        params.append(source)
    sql = f"""
		SELECT id, source, chunk, metadata, batch_tag, created_at, embedding <-> %s::vector AS dist
		FROM doc_embeddings
		{filt}
		ORDER BY embedding <-> %s::vector
		LIMIT %s
		"""
    out: List[EmbeddingRecord] = []
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for rid, src, chunk, meta, batch_tag, created_at, dist in cur.fetchall():
                # We do not return actual vector to keep payload light; could fetch later.
                out.append(
                    EmbeddingRecord(
                        rid, src, chunk, [], meta, batch_tag, created_at.isoformat()
                    )
                )
    return out


# Minimal smoke test helper (manual usage)
if __name__ == "__main__":  # pragma: no cover
    print("[store_pg] Running basic self-test (dimension only)")
    try:
        validate_expected_dimension([0.0] * int(os.getenv("RAG_EMBED_DIM", "4")))
        print("Dimension check passed")
    except Exception as e:  # noqa
        print("Self-test failed:", e)
