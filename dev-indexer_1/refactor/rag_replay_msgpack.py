#!/usr/bin/env python3
"""Replay offline RAG MessagePack artifacts into Postgres (doc_embeddings).

Supports artifacts produced by `rag_ingest.py --offline` (which may omit
embeddings) or normal artifacts (which may include embeddings when
--include-embeddings was used).

Behavior:
  * Loads one or many .msgpack files (via --file / --glob)
  * Ensures doc_embeddings has required columns (batch_tag, metadata)
  * If embedding missing or --reembed specified, calls EMBED_ENDPOINT
    with the chunk text; batches calls respecting --embed-batch-size.
  * If embedding needed but EMBED_ENDPOINT fails and --dummy-fill provided,
    inserts zero vectors of the specified dimension (vector(768) default).
  * Skips duplicates inside a replay batch using content hash (metadata.content_hash
    if present else sha256 of text). Optional --skip-existing to query DB
    for hashes already present (requires metadata column and JSONB @>). 
    NOTE: This is heuristic; for large volumes pre-compute externally.

Usage examples:
  python scripts/rag_replay_msgpack.py --file data/msgpack/rag_batch_docs_manual_*.msgpack
  python scripts/rag_replay_msgpack.py --glob 'data/msgpack/*.msgpack' --reembed
  python scripts/rag_replay_msgpack.py --file batch.msgpack --dummy-fill 768 --dry-run

Env Vars:
  DATABASE_URL / SUPABASE_DB_URL    Postgres DSN
  EMBED_ENDPOINT                    HTTP endpoint for embeddings (POST {texts: []})

Exit codes:
  0 success; 2 misuse / config error
"""
from __future__ import annotations

import argparse, os, glob, sys, hashlib, json, math, time
from pathlib import Path
from typing import List, Dict, Any, Optional, Sequence
from datetime import datetime, UTC

try:
    import msgpack  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"[fatal] msgpack not installed: {e}", file=sys.stderr)
    raise SystemExit(2)

import requests
import psycopg  # v3
from psycopg.types.json import Jsonb

DSN = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")


def sha256_text(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_msgpack(path: Path) -> Dict[str, Any]:
    with path.open('rb') as f:
        return msgpack.unpackb(f.read(), raw=False)


def ensure_columns(cur) -> Dict[str, bool]:
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='doc_embeddings'")
    cols = {r[0] for r in cur.fetchall()}
    needed_alters = []
    if 'batch_tag' not in cols:
        needed_alters.append("ALTER TABLE doc_embeddings ADD COLUMN IF NOT EXISTS batch_tag TEXT")
    if 'metadata' not in cols:
        needed_alters.append("ALTER TABLE doc_embeddings ADD COLUMN IF NOT EXISTS metadata JSONB")
    for stmt in needed_alters:
        cur.execute(stmt)
    return {'batch_tag': 'batch_tag' in cols or any('batch_tag' in s for s in needed_alters),
            'metadata': 'metadata' in cols or any('metadata' in s for s in needed_alters)}


def embed_texts(texts: Sequence[str], batch_size: int, sleep: float = 0.0) -> List[List[float]]:
    out: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i+batch_size]
        r = requests.post(EMBED_ENDPOINT, json={"texts": list(chunk)}, timeout=300)
        r.raise_for_status()
        data = r.json()
        embs = data.get("embeddings")
        if not isinstance(embs, list) or len(embs) != len(chunk):
            raise RuntimeError("Embedding endpoint returned unexpected shape")
        out.extend(embs)
        if sleep:
            time.sleep(sleep)
    return out


def fetch_existing_hashes(cur, hashes: List[str]) -> set[str]:
    if not hashes:
        return set()
    cur.execute("SELECT metadata->>'content_hash' FROM doc_embeddings WHERE metadata ? 'content_hash' AND metadata->>'content_hash' = ANY(%s)", (hashes,))
    return {r[0] for r in cur.fetchall()}


def replay(paths: List[Path], reembed: bool, dummy_fill: Optional[int], batch_tag_override: Optional[str], embed_batch_size: int, dry_run: bool, skip_existing: bool, sleep: float):
    if not DSN:
        raise SystemExit("DATABASE_URL / SUPABASE_DB_URL not set")
    # psycopg v3 migration: use psycopg and executemany; Jsonb wrapper for metadata

    total_files = 0
    total_rows = 0
    inserted = 0
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            flags = ensure_columns(cur)
            conn.commit()
            print(f"[info] Column availability: {flags}")
        for path in paths:
            total_files += 1
            try:
                payload = load_msgpack(path)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] Failed to load {path}: {e}")
                continue
            records = payload.get('records') or payload.get('examples') or []
            if not isinstance(records, list):
                print(f"[warn] Unexpected records format in {path}")
                continue
            print(f"[file] {path} records={len(records)}")
            total_rows += len(records)
            texts: List[str] = []
            need_embed_indices: List[int] = []
            embeddings: List[Optional[List[float]]] = []
            sources: List[str] = []
            metas: List[Dict[str, Any]] = []
            batch_tags: List[str] = []
            hashes: List[str] = []
            for i, rec in enumerate(records):
                text = rec.get('text') or rec.get('instruction') or rec.get('chunk') or rec.get('source_text')
                if not text:
                    continue
                emb = rec.get('embedding')
                if reembed or not emb:
                    need_embed_indices.append(i)
                    embeddings.append(None)
                    texts.append(text)
                else:
                    embeddings.append(emb)
                meta = rec.get('metadata') or {}
                if not isinstance(meta, dict):
                    meta = {}
                if 'content_hash' in meta:
                    h = meta['content_hash']
                else:
                    h = sha256_text(text)
                    meta['content_hash'] = h
                hashes.append(h)
                metas.append(meta)
                sources.append(rec.get('source') or payload.get('source') or 'replay')
                bt = batch_tag_override or rec.get('batch_tag') or payload.get('batch_tag') or 'replay_batch'
                batch_tags.append(bt)
            seen = set()
            keep_indices = [i for i,h in enumerate(hashes) if not (h in seen or seen.add(h))]
            if len(keep_indices) != len(hashes):
                print(f"[dedupe] Dropped {len(hashes)-len(keep_indices)} duplicate hashes inside batch")
            existing_hashes: set[str] = set()
            if skip_existing:
                with psycopg.connect(DSN) as conn2, conn2.cursor() as cur2:
                    existing_hashes = fetch_existing_hashes(cur2, [hashes[i] for i in keep_indices])
                if existing_hashes:
                    print(f"[skip-existing] {len(existing_hashes)} already present")
            final_indices = [i for i in keep_indices if hashes[i] not in existing_hashes]
            if not final_indices:
                print("[info] Nothing new to insert after filtering")
                continue
            if need_embed_indices:
                reembed_needed_map = [i for i in final_indices if embeddings[i] is None]
                if reembed_needed_map:
                    try:
                        new_embs = embed_texts([records[i].get('text') or records[i].get('instruction') or records[i].get('chunk') for i in reembed_needed_map], embed_batch_size, sleep)
                        for idx, emb in zip(reembed_needed_map, new_embs):
                            embeddings[idx] = emb
                    except Exception as e:
                        if dummy_fill is not None:
                            print(f"[warn] Embedding request failed; using dummy fill dim={dummy_fill}: {e}")
                            z = [0.0]*dummy_fill
                            for idx in reembed_needed_map:
                                embeddings[idx] = z
                        else:
                            raise
            if any(e is None for e in embeddings):
                if dummy_fill is None:
                    missing = sum(1 for e in embeddings if e is None)
                    raise SystemExit(f"{missing} embeddings missing and no dummy-fill provided")
                z = [0.0]*dummy_fill
                for i,e in enumerate(embeddings):
                    if e is None:
                        embeddings[i] = z
            rows = []
            for i in final_indices:
                rows.append((sources[i], records[i].get('text') or records[i].get('instruction') or records[i].get('chunk'), embeddings[i], metas[i], batch_tags[i]))
            print(f"[prepare] inserting {len(rows)} rows from {path}")
            if dry_run:
                continue
            with psycopg.connect(DSN) as conn3:
                with conn3.cursor() as cur3:
                    cur3.execute("SELECT column_name FROM information_schema.columns WHERE table_name='doc_embeddings'")
                    colset = {r[0] for r in cur3.fetchall()}
                    has_meta = 'metadata' in colset
                    has_batch = 'batch_tag' in colset
                    if has_meta and has_batch:
                        cur3.executemany("INSERT INTO doc_embeddings (source, chunk, embedding, metadata, batch_tag) VALUES (%s, %s, %s::vector, %s, %s)", [(s,t,e,Jsonb(m),b) for (s,t,e,m,b) in rows])
                    elif has_batch and not has_meta:
                        cur3.executemany("INSERT INTO doc_embeddings (source, chunk, embedding, batch_tag) VALUES (%s, %s, %s::vector, %s)", [(s,t,e,b) for (s,t,e,_m,b) in rows])
                    else:
                        cur3.executemany("INSERT INTO doc_embeddings (source, chunk, embedding) VALUES (%s, %s, %s::vector)", [(s,t,e) for (s,t,e,_m,_b) in rows])
                conn3.commit()
            inserted += len(rows)
    print(f"[done] files={total_files} total_records={total_rows} inserted={inserted}")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Replay offline RAG msgpack artifacts into Postgres")
    ap.add_argument('--file', help='Single msgpack file path')
    ap.add_argument('--glob', help='Glob for msgpack files (quotes)')
    ap.add_argument('--reembed', action='store_true', help='Regenerate embeddings even if present')
    ap.add_argument('--dummy-fill', type=int, help='If embedding missing / fails, fill with zero vector of this dim')
    ap.add_argument('--batch-tag', help='Override batch_tag for all rows')
    ap.add_argument('--embed-batch-size', type=int, default=32)
    ap.add_argument('--skip-existing', action='store_true', help='Skip rows whose content_hash already present (needs metadata column)')
    ap.add_argument('--sleep', type=float, default=0.0, help='Sleep seconds between embedding batches')
    ap.add_argument('--dry-run', action='store_true')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    paths: List[Path] = []
    if args.file:
        paths.append(Path(args.file))
    if args.glob:
        for p in glob.glob(args.glob, recursive=True):
            paths.append(Path(p))
    if not paths:
        print("Provide --file or --glob", file=sys.stderr)
        return 2
    replay(paths, args.reembed, args.dummy_fill, args.batch_tag, args.embed_batch_size, args.dry_run, args.skip_existing, args.sleep)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())