# Embedding Pipeline (CCE)

Composite Contextual Embedding (CCE) generates robust vectors by fusing multiple signals (content, metadata, structure).

## What it does
- Accept canonical Events from `/events/ingest` or the gRPC ingester
- Compute embeddings (content + light metadata) with weighted fusion
- Persist to Timescale `events` hypertable with pgvector column

## Where things live
- API entrypoints: `app/main.py` (diagnostics, ingest)
- Worker scripts: `scripts/generate_vector_batch.py`, `scripts/ingest_batch.py`
- Schema: `sql/events_unified_schema.sql`
- FDW bridge: `docs/FDW_BRIDGE.md`

## Run locally
1) Start stack: `docker-compose up -d` (uses Dockerfile + requirements)
2) Post a few events to the ingest route or use the batch scripts
3) Verify vectors exist via `/vector/ping` and DB count via `/index`

## Notes
- Keep env vars minimal; mirror only used vars into `.env.example`
- Prefer idempotent SQL: all schema files use IF NOT EXISTS
- Batch inserts (COPY) and small vector dims keep ingestion snappy

## Next steps
- Add embedder client abstraction and unit tests for fusion weights
- Wire COPY-based insert in gRPC ingester once codegen is in place
