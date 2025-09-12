"""
DB Client for Vector Search (pgvector).

Notes:
    - Timescale dependency removed; plain Postgres with pgvector.
    - Recommended production layout: partition `doc_embeddings` by RANGE (created_at) or
        HASH (id) depending on pruning vs. uniform distribution needs.
    - Maintain ANN index (ivfflat or hnsw) plus BRIN on created_at for recency filters.
"""

import os
from typing import Any, Dict, List

import psycopg  # psycopg3
from psycopg.rows import dict_row
from psycopg import sql


class DBClient:
    def __init__(self):
        """Connection strategy priority:
        1. DATABASE_URL (full DSN)
        2. SUPABASE_DB_URL (alias for hosted Postgres)
        3. Legacy discrete PG_* env vars
        Skips when APP_TEST_MODE=1 & SKIP_DB=1.
        """
        if os.getenv("APP_TEST_MODE") == "1" and os.getenv("SKIP_DB", "1") == "1":
            self.conn = None  # type: ignore
            return
        dsn = (
            os.getenv("DATABASE_URL")
            or os.getenv("SUPABASE_DB_URL")
            or os.getenv("SUPABASE_DIRECT_URL")
        )
        try:
            if dsn:
                self.conn = psycopg.connect(dsn)
            else:
                self.conn = psycopg.connect(
                    dbname=os.getenv("PG_DB", "rag_db"),
                    user=os.getenv("PG_USER", "postgres"),
                    password=os.getenv("PG_PASSWORD", "password"),
                    host=os.getenv("PG_HOST", "localhost"),
                    port=int(os.getenv("PG_PORT", "5432")),
                )
            self.conn.autocommit = True
            search_path = os.getenv("DB_SEARCH_PATH")
            if search_path:
                with self.conn.cursor() as cur:
                    try:
                        schemas = [s.strip() for s in search_path.split(",") if s.strip()]
                        if schemas:
                            cur.execute(
                                sql.SQL("SET search_path TO {}" ).format(
                                    sql.SQL(", ").join([sql.Identifier(s) for s in schemas])
                                )
                            )
                    except Exception as e:  # pragma: no cover
                        os.environ["DB_CLIENT_LAST_ERROR"] = (
                            f"search_path error: {e}"  # soft warning
                        )
        except Exception as e:  # pragma: no cover - defensive
            self.conn = None  # type: ignore
            # Keep a soft failure path; retrieval will yield []
            os.environ["DB_CLIENT_LAST_ERROR"] = str(e)

    def close(self):
        try:
            if self.conn and not self.conn.closed:
                self.conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def vector_search(
        self, embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Query pgvector for top-k similar documents.

            Returns list of dicts: {id, text, metadata, distance}
            Score is deliberately NOT computed here so it can be derived conceptually
            at response time based on current recency/weighting strategies.
        Assumes table schema: id, chunk, metadata JSONB (nullable), embedding vector.
        (Earlier code referenced a 'text' column; unified on 'chunk').
        """
        if not embedding or self.conn is None:
            return []
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
        SELECT id, chunk, metadata, (embedding <-> %s)::float AS distance
                FROM doc_embeddings
                ORDER BY embedding <-> %s
                LIMIT %s
                """,
                (embedding, embedding, top_k),
            )
            rows = cur.fetchall() or []
            return [
                {
                    "id": r.get("id"),
                    "text": r.get("chunk"),
                    "metadata": r.get("metadata"),
                    "distance": r.get("distance") or 0.0,
                }
                for r in rows
            ]
