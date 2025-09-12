"""Replay previously exported RAG MsgPack batches into Postgres.

Accepts one or many .msgpack files produced by rag_ingest.py --msgpack-out ...
If embeddings are present in records they are inserted directly.
If missing (empty list or key absent) the script re-embeds text via /model/embed.

Usage:
  python scripts/replay_msgpack_ingest.py --files data/msgpack/rag_batch_*.msgpack
"""
from __future__ import annotations
import argparse, glob, os, msgpack, requests, psycopg2  # type: ignore
from psycopg2.extras import execute_values, Json  # type: ignore

EMBED_ENDPOINT = os.getenv('EMBED_ENDPOINT', 'http://127.0.0.1:8000/model/embed')
DSN = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')

def embed(texts):
    if not texts: return []
    r = requests.post(EMBED_ENDPOINT, json={'texts': texts}, timeout=180)
    r.raise_for_status(); return r.json()['embeddings']

def load_msgpack(path: str):
    with open(path,'rb') as f:
        return msgpack.unpackb(f.read(), raw=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--files', nargs='+', required=True, help='MsgPack files or globs')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    paths=[]
    for pattern in args.files:
        paths.extend(glob.glob(pattern))
    if not paths: raise SystemExit('No files matched')
    if not DSN: raise SystemExit('Set DATABASE_URL or SUPABASE_DB_URL')
    total=0
    with psycopg2.connect(DSN) as conn:
        with conn.cursor() as cur:
            for p in sorted(paths):
                data=load_msgpack(p)
                recs=data.get('records', [])
                if not recs: continue
                need_embed=[]; idx_map=[]
                for i,r in enumerate(recs):
                    emb=r.get('embedding')
                    if not emb:
                        need_embed.append(r['text'])
                        idx_map.append(i)
                if need_embed:
                    new_embs=embed(need_embed)
                    for i,(vec) in enumerate(new_embs):
                        recs[idx_map[i]]['embedding']=vec
                rows=[]
                for r in recs:
                    rows.append((r.get('source'), r.get('text'), r['embedding'], Json(r.get('metadata')), r.get('batch_tag')))
                if args.dry_run:
                    print(f"[dry-run] Would insert {len(rows)} from {p}")
                else:
                    execute_values(cur, "INSERT INTO doc_embeddings (source, chunk, embedding, metadata, batch_tag) VALUES %s", rows)
                    print(f"Inserted {len(rows)} from {p}")
                    total+=len(rows)
    print(f"Done. Inserted={total}")

if __name__=='__main__':
    main()