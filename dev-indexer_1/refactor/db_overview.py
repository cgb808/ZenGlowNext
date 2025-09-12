#!/usr/bin/env python
"""Lightweight DB overview utility.

Prints present RAG / personalization tables and approximate row counts.
Respects DSN precedence: DATABASE_URL > SUPABASE_DB_URL > PG_* pieces.

Usage:
  python scripts/db_overview.py            # all tables
  python scripts/db_overview.py --tables documents,chunks,user_memory_items

Safe: read-only SELECT COUNT(*) queries.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List

import psycopg  # v3
from psycopg.rows import dict_row

DEFAULT_TABLES = [
    "documents",
    "chunks",
    "chunk_features",
    "doc_embeddings",  # legacy
    "interaction_events",
    "chunk_engagement_stats",  # mat view
    "scoring_experiments",
    "query_performance",
    "ann_runtime_config",
    "model_registry",
    "scoring_weights",
    "feature_snapshots",
    "users",
    "groups",
    "group_memberships",
    "user_persona_prefs",
    "conversation_sessions",
    "user_embeddings",
    "user_traits",
    "user_memory_items",
    "tags",
    "tag_assignments",
    "finetune_examples",
]


def connect():
    dsn = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if dsn:
        return psycopg.connect(dsn)
    return psycopg.connect(
        dbname=os.getenv("PG_DB", "rag_db"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "password"),
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
    )


def table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_name = %s
        UNION ALL
        SELECT 1 FROM pg_matviews WHERE matviewname = %s
        LIMIT 1
        """,
        (name, name),
    )
    return cur.fetchone() is not None


def count_rows(cur, name: str) -> int | None:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {name};")
        return int(cur.fetchone()[0])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tables", help="Comma separated explicit tables list", default=None
    )
    args = ap.parse_args()
    if args.tables:
        targets: List[str] = [t.strip() for t in args.tables.split(",") if t.strip()]
    else:
        targets = DEFAULT_TABLES
    try:
        with connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                rows = []
                for t in targets:
                    present = table_exists(cur, t)
                    if not present:
                        rows.append({"table": t, "present": False, "count": None})
                        continue
                    cnt = count_rows(cur, t)
                    rows.append({"table": t, "present": True, "count": cnt})
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    # Pretty print
    width = max(len(r["table"]) for r in rows) + 2
    print(f"{'TABLE'.ljust(width)} PRESENT COUNT")
    for r in rows:
        present = "Y" if r["present"] else "N"
        count = "-" if r["count"] is None else str(r["count"])
        print(f"{r['table'].ljust(width)} {present}       {count}")


if __name__ == "__main__":
    main()
