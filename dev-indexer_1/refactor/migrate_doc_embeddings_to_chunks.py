#!/usr/bin/env python
"""Migrate legacy doc_embeddings rows into documents + chunks tables.

Strategy (minimal viable):
  - For each doc_embeddings row, create (or reuse) a synthetic document per batch_tag (or 'legacy') and source.
  - Insert a chunk row with text=chunk, checksum=hash(text), embedding_small=embedding (dimension 384 expected), ordinal incremental.

Idempotent-ish: stores a checksum uniqueness constraint prevents duplicates (ux_chunks_checksum).

Prereqs: artifact_a_schema applied and legacy table present.
"""
from __future__ import annotations

import hashlib
import os

import psycopg  # v3

DSN = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
if not DSN:
    raise SystemExit("Set DATABASE_URL or SUPABASE_DB_URL")

conn = psycopg.connect(DSN)
cur = conn.cursor()

cur.execute("SELECT to_regclass('public.doc_embeddings')")
res = cur.fetchone()
if not res or res[0] is None:
    raise SystemExit("No legacy doc_embeddings table found")

# Ensure target tables exist
cur.execute("SELECT to_regclass('public.documents'), to_regclass('public.chunks')")
res = cur.fetchone()
if not res or any(r is None for r in res):
    raise SystemExit("documents/chunks tables missing - apply schema first")

print("Scanning legacy rows...")
cur.execute(
    "SELECT id, source, chunk, embedding, batch_tag FROM doc_embeddings ORDER BY id"
)
rows = cur.fetchall()
print(f"Found {len(rows)} legacy rows")

# Map (source,batch_tag) -> document_id
cache = {}
inserted_chunks = 0


def get_doc_id(source, batch_tag):
    key = (source or "unknown", batch_tag or "legacy")
    if key in cache:
        return cache[key]
    content_hash = hashlib.sha1(f"{key[0]}::{key[1]}".encode()).hexdigest()
    cur.execute(
        "SELECT id FROM documents WHERE content_hash=%s AND version=1", (content_hash,)
    )
    r = cur.fetchone()
    if r:
        cache[key] = r[0]
        return r[0]
    cur.execute(
        "INSERT INTO documents (content_hash, title, source_type, raw_text) VALUES (%s,%s,%s,%s) RETURNING id",
        (content_hash, key[0][:200], "legacy", None),
    )
    fetched = cur.fetchone()
    if not fetched:
        raise RuntimeError("Failed to insert document")
    doc_id = fetched[0]
    cache[key] = doc_id
    return doc_id


chunk_inserts = []
for _id, source, text, embedding, batch_tag in rows:
    if text is None:
        continue
    checksum = hashlib.sha1(text.encode()).hexdigest()
    doc_id = get_doc_id(source, batch_tag)
    # ordinal approximate by current count for doc
    cur.execute(
        "SELECT COALESCE(MAX(ordinal),0)+1 FROM chunks WHERE document_id=%s", (doc_id,)
    )
    fetched = cur.fetchone()
    ordinal = fetched[0] if fetched else 1
    chunk_inserts.append((doc_id, ordinal, text, checksum, embedding))

print(f"Prepared {len(chunk_inserts)} chunk inserts (dedupe may drop some)")

sql = """INSERT INTO chunks (document_id, ordinal, text, checksum, embedding_small)
VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING"""
if chunk_inserts:
    cur.executemany(sql, chunk_inserts)
    inserted_chunks = cur.rowcount

conn.commit()
print(f"Inserted ~{inserted_chunks} new chunk rows")
print("Done.")
