#!/usr/bin/env python3
"""LEGACY (Archived) Async Embedding Worker (psycopg2)

Original implementation retained for benchmarking only.
Forward worker: app/inference/gating.py (psycopg v3).

Do not modify; delete once v3 worker gains bulk COPY/UPDATE.
"""
from __future__ import annotations
import os, time, hashlib, json, argparse, sys, math, random
from typing import List, Tuple, Any

try:
    import psycopg2  # type: ignore
    from psycopg2.extras import execute_values  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"psycopg2 import failed: {e}", file=sys.stderr)
    raise

try:
    import requests  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"requests import failed: {e}", file=sys.stderr)
    raise

DEF_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
DEF_POLL = float(os.getenv("POLL_INTERVAL", "5"))
DEF_EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")

def sha256_text(t: str) -> str:
    import hashlib
    return hashlib.sha256(t.encode('utf-8')).hexdigest()

def fetch_batch(conn, batch_size: int):
    sql = (
        "SELECT time, id, content, content_hash FROM conversation_events "
        "WHERE embedded=FALSE AND embedding IS NULL ORDER BY time ASC LIMIT %s FOR UPDATE SKIP LOCKED"
    )
    with conn.cursor() as cur:
        cur.execute(sql, (batch_size,))
        return cur.fetchall()

class EmbedClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip('/')
    def embed(self, texts: List[str], max_retries: int = 3):
        delay = 1.0
        import time, random
        for attempt in range(max_retries+1):
            try:
                import requests
                r = requests.post(self.endpoint, json={"texts": texts}, timeout=60)
                if r.status_code != 200:
                    raise RuntimeError(f"bad status {r.status_code}: {r.text[:200]}")
                data = r.json()
                embs = data.get("embeddings")
                if not isinstance(embs, list):
                    raise RuntimeError("missing embeddings in response")
                return embs
            except Exception as e:  # noqa: BLE001
                if attempt == max_retries:
                    raise
                sleep_for = delay * (0.5 + random.random())
                print(f"[embed] retry {attempt+1}/{max_retries} after error: {e}; sleep {sleep_for:.2f}s")
                time.sleep(sleep_for)
                delay = min(delay*2, 30)
        raise RuntimeError("unreachable")

def update_batch(conn, rows, embeddings, hash_content: bool, dry_run: bool):
    if not rows:
        return
    upd_sql = (
        "UPDATE conversation_events SET embedding = data.embedding, embedded=TRUE, "
        "content_hash = COALESCE(content_hash, data.content_hash) "
        "FROM (VALUES %s) AS data(time,id,embedding,content_hash) "
        "WHERE conversation_events.time = data.time AND conversation_events.id = data.id"
    )
    values = []
    for (time_val, id_val, content, existing_hash), emb in zip(rows, embeddings):
        chash = existing_hash
        if hash_content and not existing_hash:
            chash = sha256_text(content)
        values.append((time_val, id_val, emb, chash))
    if dry_run:
        print(f"[dry-run] would update {len(values)} rows")
        return
    with conn.cursor() as cur:
        execute_values(cur, upd_sql, values)


def main():
    ap = argparse.ArgumentParser(description="LEGACY embedding worker (benchmark only)")
    ap.add_argument('--db-url')
    ap.add_argument('--embed-endpoint', default=DEF_EMBED_ENDPOINT)
    ap.add_argument('--batch-size', type=int, default=DEF_BATCH_SIZE)
    ap.add_argument('--poll-interval', type=float, default=DEF_POLL)
    ap.add_argument('--max-loop', type=int)
    ap.add_argument('--hash-content', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    db_url = args.db_url or os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    client = EmbedClient(args.embed_endpoint)
    loops = 0
    import time
    while True:
        loops += 1
        try:
            with psycopg2.connect(db_url) as conn:
                conn.autocommit = False
                rows = fetch_batch(conn, args.batch_size)
                if not rows:
                    conn.rollback()
                    if args.max_loop and loops >= args.max_loop:
                        print("[done] max_loop reached with no work")
                        return 0
                    time.sleep(args.poll_interval)
                    continue
                texts = [r[2] for r in rows]
                embs = client.embed(texts)
                if len(embs) != len(rows):
                    raise RuntimeError("embedding count mismatch")
                update_batch(conn, rows, embs, args.hash_content, args.dry_run)
                if not args.dry_run:
                    conn.commit()
                print(f"[batch] rows={len(rows)}")
        except KeyboardInterrupt:
            print("[signal] interrupt; exiting")
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"[error] {e}")
            time.sleep(min(args.poll_interval, 10))
        if args.max_loop and loops >= args.max_loop:
            print("[done] max_loop reached")
            return 0

if __name__ == '__main__':
    raise SystemExit(main())
