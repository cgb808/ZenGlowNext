## Embedding worker compose (moved)

To keep the root clean, the embedding worker compose file was moved to
`compose/embedding-worker.yml`.

Run it with:

```
docker compose -f compose/embedding-worker.yml up -d
```

It uses `API_EXTERNAL_URL` and `JWT_SECRET` from your `.env` (see `.env.example`
for defaults). Change `API_EXTERNAL_URL` in production.

<!-- Directory Index: supabase/ -->

Quick refs:

- Architecture Overview: `docs/ARCHITECTURE_OVERVIEW.md` (spool/gate, ingestion_manifest, Go notifier)
- DevOps TODO: `docs/DEVOPS_TODO.md` (wiring, systemd, env, security)

# supabase/ Supabase Integration Assets

## Indexed Docs Quick Links

| Area                           | Doc                            |
| ------------------------------ | ------------------------------ |
| Swarm Exploratory Engine       | `app/swarm/README.md`          |
| Multi-Root Workspace           | `docs/MULTI_ROOT_WORKSPACE.md` |
| CUDA Remote Guide              | `CUDA_REMOTE_GUIDE.md`         |
| File Transfer / Sync           | `FILE_TRANSFER_README.md`      |
| PII Tagging & Sanitized Export | `docs/PII_TAGGING.md`          |
| Governance & RAG (coming)      | `docs/` (see future index)     |

> Tip: Swarm endpoints (e.g. `/swarm/metrics`) are served by the main FastAPI
> app; when running via docker-compose use
> `http://localhost:8001/swarm/metrics`.

Intended for SQL policies, edge functions, or auth integration scaffolding.

Related Docs:

- RLS / security: `../docs/security/RLS_POLICY_REFERENCE.md`

## Caching architecture (L1 / L2 / L3)

- L1: Hot Cache (In-Memory)
  - Fastest layer inside the router/process, acting as working memory.
  - Tech: in-memory LRU with TTL. In this repo, Python-side helpers live in `app/core/response_cache.py` and `app/core/embedding_cache.py`. The planned Go gRPC router keeps its own LRU.
  - Purpose: zero-network-hop access to the most critical, frequently used data.

- L2: Warm Cache (Shared Cache)
  - System-wide shared cache for quick access across services.
  - Tech: Redis. Canonical wrapper is `app/core/redis_cache.py`.
  - Purpose: reduce DB load; promote/demote data between L1 and L3.
  - Serialization: configurable via env for cross-language consistency:
    - `REDIS_SERIALIZATION_FORMAT` = `json` | `msgpack` (default `json`) used by `cache_set_auto`/`cache_get_auto`.
    - `REDIS_PUBSUB_FORMAT` = `json` | `msgpack` (default `json`) used by `publish_build_update` (messages include an `encoding` field).

- L3: Cold Storage (Source of Truth)
  - Durable, authoritative databases.
  - Tech: PostgreSQL family (Supabase Postgres + self-hosted TimescaleDB on ZFS with pgvector).
  - Purpose: accessed on cache miss or for authoritative reads/writes.

### gRPC + MessagePack wrapper

For Go gRPC services, consider a thin envelope for cross-language payloads:

- Define a protobuf message with `bytes payload` and metadata like `encoding` (e.g., `json`|`msgpack`).
- Server/clients agree on `encoding`; wrap/unwrap MessagePack at the boundary while keeping protobuf transport stable.
- Align with Redis settings above so services can reuse the same serialization choice.

## Added Integrations

- OpenWeatherMap API: endpoints `/weather/current` and `/weather/onecall`
  (requires `OPENWEATHER_API_KEY`).
- Tool Specs endpoint: `/tools/spec` provides machine-readable tool definitions
  (weather tools) for agent/function-calling models.

### Ingestion Spool Automation

Batch .msgpack artifacts via a filesystem spool with an orchestrator script and a size-threshold watcher service. See `docs/INGESTION_SPOOL.md` for setup.

## Troubleshooting (Quick Wins)

| Issue                          | Symptom                            | Resolution                                                                                                                                      |
| ------------------------------ | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------ | ---------- |
| Missing DB URL                 | `/ready` shows db.fail or disabled | Set `DATABASE_URL` (or `SUPABASE_DB_URL`), restart.                                                                                             |
| Embed service offline          | `/ready` embed.embed_service=fail  | Set `EMBED_BASE_URL` or disable retrieval with `RAG_RETRIEVAL_MODE=disabled` temporarily.                                                       |
| Invalid retrieval mode         | Startup exits config guard         | Choose one of `pgvector                                                                                                                         | weaviate | supabase_rpc | disabled`. |
| Deprecated /model/embed call   | 410 Gone                           | Point clients to remote embed service at `EMBED_BASE_URL`. Enable legacy fallback only with `LEGACY_EMBED=1` + `DEV_LOCAL_EMBED=1` (temporary). |
| Health passes but queries slow | p95 high in logs                   | Check DB indexing & embedding service latency; inspect `/metrics` counters and add indexing where needed.                                       |

### Environment Validation

Startup config guard fails fast when `STRICT_ENV=true`. To allow degraded
startup (dev), set `STRICT_ENV=false`.

### Metrics

Prometheus-style counters available at `/metrics` (minimal scaffold). Future
histograms will extend this endpoint without breaking current format.

### Retention & Maintenance Placeholders

Add to your environment (no logic yet—documentation only):

```
RETENTION_DAYS=30        # Planned: prune old ingestion batches beyond this window
VACUUM_NIGHTLY=true      # Planned: schedule nightly maintenance (pg_cron or external)
```

PostgreSQL maintenance recommendation: run `VACUUM (ANALYZE)` for high-churn
tables daily and before large batch ingest jobs.

## Bring up the stack and push schema

1) Start core databases and app (dev):

```
docker compose up -d db db_pii
docker compose up app
```

2) Push core schema to Supabase (optional):

- With DB URL (recommended in CI or when CLI unavailable):

```
SUPABASE_DB_URL=postgresql://postgres:***@db.<project>.supabase.co:6543/postgres \
  ./scripts/supabase_core_sync.sh
```

- Or using Supabase CLI inside a Supabase project dir:

```
./scripts/supabase_core_sync.sh
```

This applies, in order, `artifact_a_schema.sql`, `rag_core_schema.sql`, `rag_indexes.sql`,
and optionally `dev_knowledge_graph_schema.sql`, `inference_logging.sql`, and `pii_vector_schema.sql` if present.

## Redis cache client wrapper (planned)

We will add a class-based Redis cache wrapper that keeps the existing key patterns and adds namespaced JSON/MsgPack helpers:

- Legacy pattern preserved: `rag:q:<sha1(query)>:<top_k>` for RAG query results.
- New helpers: `set_json_namespace/get_json_namespace` and MessagePack variants with MD5-internal hashing to keep keys small.
- Build updates: `publish_build_update` will publish envelopes to `REDIS_BUILD_CHANNEL` (default `build_updates`).
- Env: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL`, `DEFAULT_TTL_SECONDS`.

Example (coming soon):

```
from app.core.redis_cache_client import create_cache
c = create_cache()
c.set_json_namespace('example', 'user_profile:42', {'x': 1})
print(c.get_json_namespace('example', 'user_profile:42'))
```

This will coexist with current functional helpers in `app/core/redis_cache.py` and `app/cache/redis_supabase_cache.py`.


## 3D Tooling (Streamlit + Three.js)

Experimental lightweight 3D sandbox for Jarvis-style commands lives at
`app/tooling/streamlit_threejs_component.py` and Phi demo
`app/tooling/streamlit_threejs_phi_demo.py`.

Tool Comparison (lightweight options):

- Three.js (via Streamlit component): Instant, highly interactive, primitives
  only.
- OpenSCAD: Script-based parametric, needs local binary.
- CADQuery: Pure Python parametric models, good for programmatic assembly.

Run Three.js Phi demo:

```
streamlit run app/tooling/streamlit_threejs_phi_demo.py
```

Planned enhancements:

- Real Phi-3-mini parsing endpoint (extract type/color/size/position)
- Audio (Whisper) -> command pipeline
- Scene export (GLTF/SCAD) and persistence

### Optional Coqui TTS

Install audio extras:

```
pip install -r requirements-audio.txt
```

Endpoints (after install):

- POST /audio/coqui_tts { text, voice?, speaker? }
- GET /audio/coqui_voices

Env vars:

````
COQUI_VOICE=tts_models/en/vctk/vits
COQUI_SPEAKER_ID=\n```
## Hybrid DB Model (Supabase + Timescale on ZFS)

- Supabase (Engagement): swarms, agents, missions, performance, ancestry, knowledge_graph, users, pii_token_map.
- Timescale (Data Engine): events hypertable, activity_log (partitioned).
- Bridge: postgres_fdw on Supabase to `events_remote` and `remote_activity_log`.
## Centralized gRPC Logging Service

We’re migrating from per-process, lock-based file logging to a centralized Go gRPC Log Service that agents stream frames to. This removes cross-process file lock contention and centralizes rotation/compression and shipping. See `docs/logging-service.md` for the contract and architecture.


See also: docs/DB_2x2_LAYOUT.md for the finalized "2x2" layout (non-PII vs PII × vector vs timeseries) and environment variables.

Docs:
- Data Placement: `docs/DATA_PLACEMENT.md`
- FDW Bridge: `docs/FDW_BRIDGE.md` (includes federated join example)
- PII Architecture: `docs/PII_ARCHITECTURE.md`

## Token tools (PII vault)

CLI: `scripts/token_tools.py` (uses `PII_DATABASE_URL`).

Examples:

```
# Mint a 30-day token after voice auth creates identity UUID
./scripts/token_tools.py mint --identity <uuid> --purpose voice_auth --ttl 30

# Resolve
./scripts/token_tools.py resolve --token <token>

# Rotate
./scripts/token_tools.py rotate --token <token> --ttl 30
```

## gRPC Services

- Router contract: `services/router/v1/router.proto`
- Ingestion contract: `services/ingestion/v1/ingestion.proto`
- Go ingester scaffold: `cmd/ingester/` (server skeleton)
- Codegen & run: `services/ingestion/README.md`

## RLS Seed Example

See `docs/RLS_SEED_EXAMPLE.sql` for example identities (Charles, Nancy, Willow) and guardianship links, plus session settings for testing RLS.

## Initialize DB schema and seed family data

If your Postgres volumes already exist and init scripts didn't run, apply the schema in-place:

1) Start the stack (db, db_pii, redis at minimum)

2) Apply core + PII schemas

- This runs a minimal set: events, family, inference logs, and PII vault.

```
./scripts/db_apply.sh both
```

3) Seed sample family data (edit your own copy first)

```
cp scripts/family_seed.sample.yaml scripts/family_seed.yaml
# Edit scripts/family_seed.yaml with real names (local only)
python3 scripts/seed_family.py --yaml scripts/family_seed.yaml \
  --core-dsn "postgresql://postgres:your-super-strong-and-secret-password@localhost:5432/rag_db" \
  --pii-dsn  "postgresql://postgres:your-super-strong-and-secret-password@localhost:5433/rag_pii"
```

Notes:
- The seed script creates PII identity rows and mints pseudonymous tokens in `pii_token_map`.
- Keep real data only on your home machines. Do not commit your YAML file.
- You can re-run the seed; inserts are idempotent (upserts on keys).

### Quick mock embedding server (dev)

If your embed backend isn’t ready, run a stdlib-only mock server that returns deterministic random vectors by text length:

```
python3 scripts/mock_embed_server.py  # serves on http://127.0.0.1:8000
```

Point the app at it by setting `EMBED_BASE_URL=http://127.0.0.1:8000`.
You can adjust `EMBED_DIM`, `EMBED_HOST`, and `EMBED_PORT` via env.
