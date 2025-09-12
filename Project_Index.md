# Project Index (Comprehensive)

## Core Directories
- `app/` FastAPI application code.
- `api/` Lightweight API entrypoints (health, vector ping, counts).
- `sql/` All database DDL (core RAG, knowledge graph, metrics, swarm, legacy, deprecated).
- `scripts/` Operational, ingestion, embedding, maintenance, verification & tooling.
- `dashboard/` React/Vite dashboard scaffold (future metrics & KG UI).
- `nginx/` Reverse proxy configuration.
- `whisper.cpp/` Whisper server build assets.

## Schemas (sql/)
| File | Summary |
|------|---------|
| `00_init_extensions.sql` | Core extensions bootstrap (pgvector & optional) |
| `rag_core_schema.sql` | Core RAG retrieval entities & embeddings base |
| `dev_knowledge_graph_schema.sql` | Dev knowledge graph: events, code chunks, narrative search fns |
| `unified_knowledge_graph_schema.sql` | Consolidated minimal KG (v6) |
| `events_unified_schema.sql` | Unified events ingestion layer |
| `metrics_timeseries.sql` | Daily partitioned metrics + helpers (BRIN, RLS) |
| `metrics_cron.sql` | pg_cron jobs (partition automation) |
| `inference_logging.sql` | LLM inference logging (time-series) |
| `swarm_schema.sql` | Swarm lifecycle + knowledge artifacts |
| `swarm_repo_schema.sql` / `_v6` | Legacy/alt swarm repo schemas |
| `colony_swarm_schema.sql` | Colony swarm variant |
| `artifact_a_schema.sql` | Legacy artifact retrieval (v1) |
| `hybrid_retrieval_schema.sql` | Hybrid retrieval extension (Artifact A) |
| `rag_indexes.sql` | Canonical indexes (vector + btree) idempotent |
| `pgvector_indexes.sql` | (Deprecated) superseded by `rag_indexes.sql` |
| `add_vector_indexes.sql` | (Deprecated) prior add-on vector indexes |
| `optional_brin_indexes.sql` | Optional BRIN pruning indexes |
| `timescale_artifacts.sql` | Legacy Timescale objects (removal path) |
| `pii_secure_schema.sql` | PII split (deprecated via consolidation) |
| `pii_vector_schema.sql` | PII vector portion (deprecated) |
| `roles_privileges.sql` | Roles & privileges (partial duplication) |
| `rls_policies.sql` | RLS policy definitions (expand soon) |
| `user_session_state.sql` | Session continuity / resume tables |
| `ingest_events_schema.sql` | Ingest events journal |
| `ingest_events_cron.sql` | Cron definitions for ingestion jobs |
| `ingestion_manifest.sql` | Manifest placeholder header |
| `family_schema.sql` | Family context persistence |
| `family_rls.sql` | RLS & masking for family context |
| `farmily_context_and_inference_log.sql` | Combined family + inference (legacy) |
| `unified_discovery_schema.sql` | Unified discovery constructs |
| `create_test_tables.sql` | Test support tables |
| `init.sql` | Convenience init for vector |

Notes:
- Partitioned tables: PK must include partition key (e.g. metrics uses `(id, recorded_at)`).
- Deprecated files retained only to ease transition; prefer consolidated/unified forms moving forward.

## Script Inventory (Grouped)
### Schema & DB Ops
`supabase_full_sync.sh`, `supabase_core_sync.sh`, `db_apply.sh`, `db_dump.sh`, `db_smoke.sh`, `db_reset.py`, `db_ssh_tunnel.sh`, `schema_drift_check.py`, `schema_export_sanitized.py`.
### Verification / Maintenance
`metrics_schema_verify.sh`, `dev_kg_schema_verify.sh`, `root_hygiene_check.py`, `validate_env.py`.
### Secrets / Env
`collect_secrets.sh`, `generate_redacted_env.py`, `merge_env.py`, `env_bootstrap.py`, `env_load.py`, `fetch_supabase_secrets.sh`.
### Ingestion & Pipelines
`ingest_batch.py`, `ingest_curated_dataset.py`, `ingestion_manifest.py`, `intake_to_redis.py`, `enhanced_intake_to_redis.py`, `batch_writer_from_redis.py`, `append_log_writer.py`, `append_log_reader.py`.
### Embeddings & Vector
`async_embedding_worker.py`, `embedding_worker_stub.py`, `generate_vector_batch.py`, `serve_embedding_model.py`, `vector_index_tuner.py`, `quantize_embedding_model.py`, `mock_embed_server.py`.
### Retrieval / RAG Utilities
`rag_manifest_generator.py`, `retrieval_union.py`, `rag_replay_msgpack.py`, `rag_replay_watch.py`, `rag_training_example_builder.py`.
### Swarm / Orchestration
`swarm_simulator.py`, `colony_router.py`, `colony_db.py`, `sidecar_manager.py`.
### Family / Context
`build_family_dataset.py`, `family_persist_sync.py`, `export_family_dataset.py`, `export_family_artifact_corpus.py`, `export_family_conversations.py`, `seed_family.py`.
### Data Prep / Datasets
`build_clarify_priority_dataset.py`, `clarify_backfill.py`, `jeeves_dataset_augment_merge.py`, `jeeves_data_audit.py`, `generate_hybrid_dataset.py`, `package_family_context.py`.
### Training / Models
`train_embedding_model.py`, `jeeves_training_runner.py`, `hybrid_hybrid_trainer.py`, `bge_embed.py`, `generate_openelm.py`.
### Monitoring & Health
`worker_health_api.py`, `process_spool.sh`, `spool_watcher.py`, `spool_poll_watcher.py`, `profile_change_watcher.py`.
### Infra / Runtime
`new_consolidated_bootstrap.sh`, `remote_cuda_probe.sh`, `remote_ollama_bootstrap.sh`, `ollama_setup.sh`, `ollama_steps.sh`, `redis_zfs_up.sh`, `rotate_role_passwords.sh`.
### Security / Compliance
`precommit_pii_guard.sh`, `pii_gate.py`.
### Misc Utilities
`token_tools.py`, `quality_demo.py`, `scaffold.py`, `memory_rag_bridge.py`, `publish_build_update.py`, `run_api.py`, `run_router.sh`, `run_logservice.sh`.

## Services (docker-compose.yml)
- `db` Postgres core (pgvector enabled after package install).
- `redis` Caching / queue buffer.
- `app` / `app-dev` FastAPI service (prod vs dev targets).
- Profile-driven optional: `leonardo` (Ollama LLM), `whisper`, `router` (gRPC), `logservice`.
- `studio` (override) lightweight Supabase Studio on port 54323.

## Vector & Embeddings
- Exclusive pgvector usage (Chroma optional inactive).
- Current indexes use IVFFlat; HNSW evaluation pending.
- Env: `PG_EMBED_DIM` (default 768).

## Metrics Partitioning
- Table: `metrics` partitioned by `recorded_at`.
- Helpers: `ensure_metrics_partition`, range & hourly variants.
- Indexes: BRIN on `recorded_at`, btree on `device_id`.

## Knowledge Graph
- Event log (`development_log`) + code chunks linking.
- Functions: `search_code_chunks`, `get_narrative_for_complex_code`.
- Potential future: partition strategy for occurred_at high volume.

## Security & RLS
- RLS enabled on metrics (policies TBD).
- Policy & role scaffolds exist; activation gated by auth design.

## Drift & Verification Workflow
1. Apply schema subsets (script or manual psql).
2. Run verifiers: `metrics_schema_verify.sh`, `dev_kg_schema_verify.sh`.
3. Future: `schema_drift_check.py` integrated into CI.

## Environment & Config
- Minimal `.env.example` (only active keys). Add new keys only when used.
- DSN pattern: `postgresql://USER:PASS@HOST:PORT/DB`.
- Consolidated single DB; PII split deprecated (see override removing `db_pii`).
- Supabase Studio optional for inspection.

## Pending / Roadmap
Short-term:
- Complete psycopg v3 migration for embedding worker.
- Author concrete RLS policies.
- Implement drift detection gating CI merges.
- Automate metrics partition creation (cron).
Medium:
- Add HNSW / hybrid index fallback logic & benchmarking.
- Build dashboard UI for metrics/time-series & KG introspection.
- Observability baseline (structured logs, metrics exporter, tracing stub).
Long-term:
- Remove deprecated & legacy schemas.
- Formal ingestion manifest + validation stage.
- Index maintenance & vacuum tuning automation.

## Pipeline Overview
1. Ingestion -> Redis buffer.
2. Batch writers persist raw artifacts.
3. Embedding worker vectorizes & upserts.
4. Partition maintenance (manual/cron).
5. Verification scripts validate structure.
6. Drift + policy enforcement (future CI).

## Key Environment Variables
| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Primary Postgres connection string. |
| `PG_EMBED_DIM` | Embedding dimension. |
| `API_EXTERNAL_URL` | External base URL for API clients. |
| `JWT_SECRET` | JWT signing secret. |
| `LEGACY_JWT` | Backward compatibility token. |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection details. |

## Quick Local Ops
```bash
# Start core services
docker-compose up -d db redis app-dev

# Apply core + metrics schema (example)
psql "$DATABASE_URL" -f sql/rag_core_schema.sql
psql "$DATABASE_URL" -f sql/metrics_timeseries.sql

# Run verifiers
./scripts/metrics_schema_verify.sh
./scripts/dev_kg_schema_verify.sh --recent 5
```

## Troubleshooting Notes
- Missing `supabase db query` -> scripts fallback to `psql`.
- Partitioned table PK must include partition key (metrics fixed with `(id, recorded_at)`).
- Install pgvector on vanilla image: `apt-get install postgresql-16-pgvector` then `CREATE EXTENSION vector;`.

---
Generated: $(date -Iseconds)
