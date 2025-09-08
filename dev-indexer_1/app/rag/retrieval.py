"""
Similarity retrieval logic for RAG pipeline.
TODO: Implement top-k retrieval from doc_embeddings.
"""

import os

import psycopg2

DSN = os.getenv("DATABASE_URL")


def retrieve_similar(query_embedding: list, top_k: int = 5):
    """Return top-k similar chunks from doc_embeddings."""
    if not DSN:
        raise RuntimeError("DATABASE_URL not set")
    with psycopg2.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source, chunk, embedding <-> %s::vector AS dist
                FROM doc_embeddings
                ORDER BY dist ASC
                LIMIT %s
                """,
                (query_embedding, top_k),
            )
            return cur.fetchall()
