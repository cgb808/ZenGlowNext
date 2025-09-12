# Dual Database Layout (Non-PII & PII)

We simplified the earlier 2x2 matrix into two Postgres databases:

1. Non-PII ("core") – vectors (Chroma or pgvector), events/time-series (range partitions + BRIN), knowledge graph, artifact/rag schemas.
2. PII vault – identity & token map, optional user-personal embeddings, access log, RLS enforced.

Local defaults (docker compose):
- core db: `db` (rag_db) on 127.0.0.1:5432
- pii db: `db_pii` (rag_pii) on 127.0.0.1:5433

Environment variables (current usage):
- `DATABASE_URL` → core database
- `PII_DATABASE_URL` → pii database
- `RAG_EMBED_DIM` (unified embedding dimension)

We no longer require the verbose *_VEC / *_TS variants. If they appear in legacy scripts they fall back to the unified DSNs.

## Quick start

1. Copy `.env.example` to `.env` and set passwords/secrets.
2. `docker compose up -d db db_pii` (or deploy stack).
3. Core schema + indexes mount automatically via bind-mounted SQL.
4. PII schema (`pii_secure_schema.sql`) initializes token map + RLS.

## Time-series & Vector

- Time-series tables (events/metrics) live in core DB with daily partitions + BRIN.
- Chroma (separate container) default for vector search; optional pgvector extension can coexist in core DB for consolidation.

## Service expectations

- FastAPI app reads `DATABASE_URL` and `PII_DATABASE_URL` directly.
- Background workers / embedding services only need `DATABASE_URL` unless performing PII enrichment (rare; keep separation).

## Future

- Optional FDW from core → pii for controlled joins (read-only).
- Potential consolidation of vector + structured retrieval onto pgvector if performance matches Chroma baseline.

Keep new variables minimal; add only when a real divergent backend appears.
