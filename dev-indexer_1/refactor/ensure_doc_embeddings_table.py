"""Ensure `doc_embeddings` table (and pgvector extension) exists in target Postgres (Supabase or local).

DSN precedence (first non-empty env):
  1. DATABASE_URL
  2. SUPABASE_DIRECT_URL
  3. SUPABASE_DB_URL
  4. SUPABASE_POOLER_URL

Usage (safe):
  set -a; source .env; set +a  # if your .env contains the DSN vars (avoid committing secrets!)
  python scripts/ensure_doc_embeddings_table.py --dim 768

The script will:
  * Connect (read-only checks first)
  * Verify / create extension vector
  * Inspect existing doc_embeddings table if present; validate dimension
  * Create table + indexes if absent
  * Output masked DSN (password hidden)

No secrets are printed beyond masked DSN. Errors are concise.
"""
from __future__ import annotations

import os
import argparse
import re
import sys
from typing import Optional

import psycopg  # v3


DSN_ENV_ORDER = [
    "DATABASE_URL",
    "SUPABASE_DIRECT_URL",
    "SUPABASE_DB_URL",
    "SUPABASE_POOLER_URL",
]


def pick_dsn() -> Optional[str]:
    for k in DSN_ENV_ORDER:
        v = os.getenv(k)
        if v:
            return v
    return None


def mask_dsn(dsn: str) -> str:
    # Basic masking: replace :password@ with :***@
    return re.sub(r":([^:@/]+)@", ":***@", dsn)


def get_existing_dimension(cur) -> Optional[int]:
    cur.execute(
        """
        SELECT atttypmod
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        WHERE c.relname = 'doc_embeddings' AND a.attname = 'embedding'
        """
    )
    row = cur.fetchone()
    if not row:
        return None
    # pgvector stores dimension in atttypmod - 4
    return row[0] - 4 if row[0] is not None else None


def ensure(cur, dim: int, create: bool) -> str:
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute(
        "SELECT to_regclass('public.doc_embeddings') IS NOT NULL AS exists"
    )
    exists = cur.fetchone()[0]
    if exists:
        existing_dim = get_existing_dimension(cur)
        if existing_dim and existing_dim != dim:
            return f"EXISTS dimension={existing_dim} (requested {dim}) -- NO CHANGE"
        return f"EXISTS dimension={existing_dim or '?'} -- OK"
    if not create:
        return "MISSING (dry-run)"
    cur.execute(
        f"""
        CREATE TABLE public.doc_embeddings (
            id BIGSERIAL PRIMARY KEY,
            source TEXT,
            chunk TEXT NOT NULL,
            embedding vector({dim}) NOT NULL,
            metadata JSONB,
            batch_tag TEXT,
            created_at timestamptz DEFAULT now()
        )
        """
    )
    # HNSW index (if supported; ignore failure fallback)
    try:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_doc_embeddings_embedding ON public.doc_embeddings USING hnsw (embedding vector_l2_ops)"
        )
    except Exception:  # pragma: no cover - optional path
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_doc_embeddings_embedding_ivf ON public.doc_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)"
        )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_doc_embeddings_source ON public.doc_embeddings(source)"
    )
    return f"CREATED dimension={dim}"


def main():  # pragma: no cover (network side-effects)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True, help="Expected embedding dimension")
    ap.add_argument("--dry-run", action="store_true", help="Only report; do not create")
    args = ap.parse_args()

    dsn = pick_dsn()
    if not dsn:
        print("ERROR: Set one of DATABASE_URL / SUPABASE_DIRECT_URL / SUPABASE_DB_URL / SUPABASE_POOLER_URL", file=sys.stderr)
        sys.exit(2)
    masked = mask_dsn(dsn)
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                status = ensure(cur, args.dim, not args.dry_run)
        print(f"doc_embeddings: {status} | DSN={masked}")
    except Exception as e:  # noqa
        print(f"ERROR connecting or ensuring table: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
