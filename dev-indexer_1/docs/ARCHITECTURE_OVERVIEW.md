# Architecture Overview

This repo implements a local-first ingestion and retrieval stack that can bridge to Supabase services.

## High-level components

- App API: FastAPI app (minimal endpoints and health checks)
- Ingestion spool: filesystem-based batching of .msgpack frames
- Embedding: external service (or local mock) producing vectors
- Databases: Postgres (partitioned + BRIN for time-series) and Chroma for vector search (pgvector optional)
- Caching: Redis (optional) for queues and signals
- Go Notifier: templated HTTP notifier invoked at critical lifecycle points

## Ingestion pipeline (spool → gate → ingest)

1. Writers produce .msgpack segments (optionally compressed) and land them in `spool/incoming/`.
2. A watcher opens the gate: when thresholds are met it triggers `scripts/process_spool.sh`.
3. The orchestrator atomically moves files to `spool/processing/` and marks a manifest row.
4. The Go Notifier fires a templated HTTP request (gate.open) to an external endpoint.
5. The Python replayer (`scripts/rag_replay_msgpack.py`) ingests data into Postgres (partitioned metrics/events).
6. On success: files move to `spool/archive/`; notifier sends gate.done(status=success).
7. On failure: files move to `spool/failed/`; notifier sends gate.done(status=failed).

## Ingestion manifest

- Table: `ingestion_manifest` (status, files jsonb, totals, timestamps)
- Helper: `scripts/ingestion_manifest.py` provides `create_or_update_manifest()` and `finish_manifest()`
- Purpose: track batches and emit NOTIFYs (if enabled) for observability.

## Notifications (Go templated HTTP)

- Binary: `tools/notifier` (tiny CLI)
- Templates:
  - `tools/notifier/templates/gate_open.json.tmpl`
  - `tools/notifier/templates/gate_done.json.tmpl`
- Trigger points:
  - Gate open: after moving files → processing, before ingest.
  - Gate done: after ingest success/failure.
- Why Go: static binary, fast startup, simple templating and HTTP client.

## Edge/Cloud compatibility

- Supabase Edge functions can still be used for other flows.
- For Redis in Edge, prefer `npm:redis` or Upstash HTTP client.
- This architecture decouples on-prem ingestion from Edge listeners via HTTP notifications.

## Security notes

- Keep Redis and Postgres non-public or locked down; prefer TLS.
- Gate webhook endpoints should validate tokens (Bearer) and rate-limit.
- Ingestion manifest data can include non-PII metadata for observability.
# ZenGlow AI Workspace - Architecture Overview

_Last Updated: August 29, 2025_

## Project Structure

```
ZenGlowAIWorkspace/
├── 🪜 Core Application
│   ├── app/                     # Main FastAPI application
│   │   ├── core/               # Core services (config, metrics, cache)
│   │   ├── rag/                # RAG pipeline & retrieval
│   │   ├── leonardo/           # Voice-enabled Leonardo assistant
│   │   ├── audio/              # TTS/STT integration
## Go Components (Current)

- Notifier (`tools/notifier`): Templated HTTP event publisher (`gate.open`, `gate.done`, `embed.start`).
- Ingestion gRPC scaffold (`cmd/ingester/`, `internal/ingester`): Client-streaming RPC for record ingestion (post-spool replay / embedding pipeline). Currently a stub awaiting codegen + COPY/embedding logic.
- Canonical query service (`internal/canonical` + client example `cmd/topk-client`): Provides `TopKEvents` (semantic lookup; embedding stub today) — candidate to refresh after successful `embed.start` batches.
- gRPC router (`grpc-router/`): General routing & future cross-service coordination (hot cache, logging services scaffolded).

All Go binaries are optional; Python spool + FastAPI API function without them. They convert critical paths (notifications, ingestion, semantic query) into fast-start static binaries.

## Dual Database Alignment

The current model: Core DB (non-PII events/metrics/embeddings) + PII Vault DB (identity, token map, audit). Go services should avoid direct PII access; pass only `user_token` or anonymized fields. See `docs/PII_ARCHITECTURE.md`.

Recommended environment usage inside Go services:
```
DATABASE_URL      # core
PII_DATABASE_URL  # vault (only if absolutely required; prefer service boundary)
```

## Event-Driven Hooks

Pattern for integrating Go services with notifier events:
1. Subscribe to `ingest_updates` + `embed_updates` (Redis / Edge relay).
2. Cache `gate.open` metadata by `batch_tag`.
3. On `gate.done success` schedule embedding & ingest RPC.
4. On `embed.start` notify canonical service to warm caches or queue vector refresh.

### Embedding Workers (Transition)

Two embedding worker variants exist during migration:
- `app/inference/gating.py` (psycopg v3, per-row updates, correct SKIP LOCKED order) — forward path.
- `archive/async_embedding_worker_legacy.py` (legacy psycopg2 bulk UPDATE, archived) — kept only for benchmarking.

Plan: Enhance v3 worker with bulk UPDATE / COPY, then remove legacy script and drop psycopg2-binary.

## Roadmap (Condensed)

- Flesh out ingestion gRPC: dedupe, batch COPY, embedding integration.
- Replace embedding stub with real model (local or external) & distance queries via pgvector/Chroma.
- Add RLS-aware reporting (vault-limited) through narrow FDW or service façade.
- Introduce retry/backoff + idempotency keys for notifier consumers.
### � Privacy & Access

- PII vault with token map (mint/resolve/rotate) — see `docs/PII_ARCHITECTURE.md`
- RLS policies: users self-only, dev cross-user, guardianship access — `docs/RLS_SEED_EXAMPLE.sql`
- Swarm tables carry `owner_identity_id` for logical linkage without joining PII

### �📊 Current Capabilities

**Operational:**

- ✅ Docker Compose stack (backend, ollama, redis, webui)
- ✅ Leonardo voice integration (TTS/Whisper)
- ✅ RAG pipeline with Chroma (pgvector optional)
- ✅ Metrics & health monitoring

**Training Infrastructure:**

- ✅ Organized fine-tuning workspace
- ✅ 4 specialized training datasets ready
- ✅ LLM-as-Judge validation framework (Mistral7b)
- ✅ Base + specialization training strategy

**Memory Management:**

- ✅ Versioned knowledge graph snapshots
- ✅ MCP Memory → RAG integration bridge
- ✅ Automated project indexing

### �️ Services

- gRPC Router contract (`services/router/v1/router.proto`)
- gRPC Ingestion (client-streaming) (`services/ingestion/v1/ingestion.proto`)
- Go ingester scaffold (`cmd/ingester/`) — register service after codegen

### 🚀 Next Phase

**Priority Queue:**

1. **Model Training Pipeline**: Automate base + specialization training
2. **Deployment Integration**: Deploy specialists alongside RAG
3. **Model Router**: Implement specialist selection logic
6. **Ingestion Service**: Embed/dedupe/COPY batch insert with health + metrics
4. **Performance Monitoring**: Track specialist effectiveness
5. **Continuous Learning**: Feedback loops for model improvement

---

_This architecture enables domain experts (Socratic tutors, drill-down questioners) to leverage contextual knowledge (RAG) for specialized, intelligent interactions._
