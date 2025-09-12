#!/usr/bin/env python3
"""Async Embedding Worker for conversation_events

Polls Postgres for unembedded conversation events (embedded = FALSE, embedding IS NULL),
locks a batch with FOR UPDATE SKIP LOCKED, calls embedding service, and updates rows.

Environment / CLI:
  --db-url / DATABASE_URL          Postgres connection string
  --embed-endpoint / EMBED_ENDPOINT  HTTP endpoint accepting {texts:[...]} -> {embeddings:[[...]]}
  --batch-size / BATCH_SIZE        Number of events per embedding batch (default 32)
  --poll-interval / POLL_INTERVAL  Seconds to sleep when no work (default 5)
  --max-loop                       Optional max loop iterations (test / CI)
  --hash-content                   Compute sha256 content_hash if missing
  --dry-run                        Do not persist updates (log only)

Safety:
  * Uses SELECT ... FOR UPDATE SKIP LOCKED to allow multiple workers.
  * Wraps each batch in its own transaction.
  * Retries embedding request with exponential backoff.

Future extensions:
  * Importance scoring & dynamic retention decisions.
  * Summaries embedding pipeline (scope != session) when added unembedded.
"""
from __future__ import annotations
import os, time, hashlib, json, argparse, sys, math, random
from typing import List, Tuple, Any
from datetime import datetime

try:
    import psycopg  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"psycopg import failed: {e}", file=sys.stderr)
    raise

try:
    import requests  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"requests import failed: {e}", file=sys.stderr)
    raise

DEF_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
DEF_POLL = float(os.getenv("POLL_INTERVAL", "5"))
DEF_EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")
EMBED_TARGET = os.getenv("EMBED_TARGET", "pgvector")  # pgvector|chroma|none (future chroma impl)
BRIN_MIN_ROWS = int(os.getenv("BRIN_MIN_ROWS", "500000"))
SELF_HEAL_INDEXES = os.getenv("SELF_HEAL_INDEXES", "1") == "1"

class EmbedClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip('/')
    def embed(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        delay = 1.0
        for attempt in range(max_retries+1):
            try:
                r = requests.post(self.endpoint, json={"texts": texts}, timeout=60)
                if r.status_code != 200:
                    raise RuntimeError(f"bad status {r.status_code}: {r.text[:200]}")
                data = r.json()
                embs = data.get("embeddings")
                if not isinstance(embs, list):
                    raise RuntimeError("missing embeddings in response")
                return embs  # assume list[list[float]]
            except Exception as e:  # noqa: BLE001
                if attempt == max_retries:
                    raise
                sleep_for = delay * (0.5 + random.random())
                print(f"[embed] retry {attempt+1}/{max_retries} after error: {e}; sleep {sleep_for:.2f}s")
                time.sleep(sleep_for)
                delay = min(delay*2, 30)
        raise RuntimeError("unreachable")

def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode('utf-8')).hexdigest()

def fetch_batch(conn, batch_size: int) -> List[Tuple[Any, Any, str, str]]:
    """Return list of (time, id, content, existing_hash). Locks rows."""
    # Correct ordering: LIMIT precedes FOR UPDATE SKIP LOCKED in Postgres grammar.
    # Previous variant had incorrect placement; fixed for psycopg v3 worker.
    sql = (
        "SELECT time, id, content, content_hash FROM conversation_events "
        "WHERE embedded=FALSE AND embedding IS NULL "
        "ORDER BY time ASC LIMIT %s FOR UPDATE SKIP LOCKED"
    )
    with conn.cursor() as cur:
        cur.execute(sql, (batch_size,))
        rows = cur.fetchall()
    return rows

def update_batch(conn, rows: List[Tuple[Any, Any, str, str]], embeddings: List[List[float]], hash_content: bool, dry_run: bool):
    if not rows:
        return
    # Per-row UPDATE to avoid extras/adapter requirements; fine for small batches
    sql = (
        "UPDATE conversation_events SET embedding = %s::vector, embedded = TRUE, "
        "content_hash = COALESCE(content_hash, %s) WHERE time = %s AND id = %s"
    )
    count = 0
    with conn.cursor() as cur:
        for (time_val, id_val, content, existing_hash), emb in zip(rows, embeddings):
            chash = existing_hash
            if hash_content and not existing_hash:
                chash = sha256_text(content)
            # Cast embedding via %s::vector using pgvector's vector input from Python list repr
            cur.execute(sql, (emb, chash, time_val, id_val))
            count += 1
    if dry_run:
        print(f"[dry-run] would update {count} rows")


def worker_loop(args):
    db_url = args.db_url or os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    embed_client = EmbedClient(args.embed_endpoint or DEF_EMBED_ENDPOINT)
    print(
        f"[worker] start db={db_url.split('@')[-1] if '@' in db_url else db_url} "
        f"endpoint={embed_client.endpoint} batch={args.batch_size} poll={args.poll_interval}s"
    )
    # Optional lightweight index self-heal / creation (BRIN) when table large enough
    if SELF_HEAL_INDEXES and EMBED_TARGET == "pgvector":
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT reltuples::bigint FROM pg_class WHERE relname='conversation_events'")
                    row = cur.fetchone()
                    if row and row[0] and row[0] >= BRIN_MIN_ROWS:
                        print(f"[indexes] conversation_events rows~{row[0]} >= {BRIN_MIN_ROWS}; ensuring BRIN")
                        cur.execute("CREATE INDEX IF NOT EXISTS brin_conversation_events_time ON conversation_events USING brin (time)")
                        conn.commit()
        except Exception as ie:  # noqa: BLE001
            print(f"[indexes] skip self-heal: {ie}")
    loops = 0
    while True:
        loops += 1
        start = time.time()
        try:
            with psycopg.connect(db_url) as conn:
                conn.autocommit = False
                rows = fetch_batch(conn, args.batch_size)
                if not rows:
                    conn.rollback()
                    idle = args.poll_interval
                    print(f"[idle] no work; sleeping {idle:.1f}s")
                    if args.max_loop and loops >= args.max_loop:
                        print("[done] max_loop reached with no work")
                        return 0
                    time.sleep(idle)
                    continue
                texts = [r[2] for r in rows]
                embeddings = embed_client.embed(texts)
                if len(embeddings) != len(rows):
                    raise RuntimeError("embedding count mismatch")
                if EMBED_TARGET == "pgvector":
                    update_batch(conn, rows, embeddings, args.hash_content, args.dry_run)
                elif EMBED_TARGET == "none":
                    print("[target] EMBED_TARGET=none; skipping persistence (dry compute)")
                else:
                    # Future: chroma or other vector store integration
                    print(f"[target] EMBED_TARGET={EMBED_TARGET} not implemented; skipping")
                if not args.dry_run:
                    conn.commit()
                took = time.time() - start
                print(f"[batch] rows={len(rows)} took={took:.2f}s emb_dim={len(embeddings[0]) if embeddings else 'n/a'}")
        except KeyboardInterrupt:
            print("[signal] interrupt; exiting")
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"[error] batch failed: {e}")
            time.sleep(min(args.poll_interval, 10))
        if args.max_loop and loops >= args.max_loop:
            print("[done] max_loop reached")
            return 0


def parse_args():
    ap = argparse.ArgumentParser(description="Async embedding worker for conversation events")
    ap.add_argument('--db-url')
    ap.add_argument('--embed-endpoint', default=DEF_EMBED_ENDPOINT)
    ap.add_argument('--batch-size', type=int, default=DEF_BATCH_SIZE)
    ap.add_argument('--poll-interval', type=float, default=DEF_POLL)
    ap.add_argument('--max-loop', type=int)
    ap.add_argument('--hash-content', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    return ap.parse_args()

if __name__ == '__main__':
    args = parse_args()
    rc = worker_loop(args)
    raise SystemExit(rc)
