## Embedding worker compose (moved)

To keep the root clean, the embedding worker compose file was moved to
`compose/embedding-worker.yml`.

Run it with:

```
docker compose -f compose/embedding-worker.yml up -d
```

It uses `API_EXTERNAL_URL` and `JWT_SECRET` from your `.env` (see `.env.example`
for defaults). Change `API_EXTERNAL_URL` in production.

## Staged Embedding Worker Startup (Low-Churn Mode)

For deliberate, longer warm-up (DB, API, optional embed service) use the staged script:

```
chmod +x scripts/start_embedding_worker.sh  # one-time
DATABASE_URL=postgresql://user:pass@db/core \
  scripts/start_embedding_worker.sh
```

Environment knobs:

| Variable | Default | Purpose |
|----------|---------|---------|
| STARTUP_WAIT_DB | 30 | Initial unconditional settle sleep (seconds) |
| STARTUP_WAIT_APP | 30 | Interval between FastAPI health polls |
| STARTUP_WAIT_EMBED | 45 | Interval between embedding endpoint polls |
| EXTRA_SLEEP_AFTER | 20 | Final buffer after readiness before exec |
| MAX_RETRIES | 20 | Max poll attempts for each dependency |
| APP_HEALTH_URL | http://app:8000/health | App health endpoint |
| EMBED_HEALTH_URL | (unset) | Optional embedding service health URL |
| DATABASE_URL | (required) | Postgres DSN passed to worker |

Embedding worker additional env:

| Variable | Default | Purpose |
|----------|---------|---------|
| EMBED_TARGET | pgvector | Where to persist embeddings (pgvector|chroma|none) |
| BRIN_MIN_ROWS | 500000 | Auto-create BRIN on conversation_events when row estimate exceeds threshold |
| SELF_HEAL_INDEXES | 1 | Enable index self-heal logic at worker start |

Notes:

Behavior: exits non‑zero if a required dependency never becomes ready (app, db env var). Embedding health is only enforced when EMBED_HEALTH_URL is set.


### Environment Configuration & Cloud Deployment Prep

We keep three environment artifacts:

### Database Connection Pooling (In-Process)

The API now ships with a lightweight in-process PostgreSQL connection pool wrapper (`psycopg_pool`).

Key points:
* Enabled automatically when `POSTGRES_DSN` is set (e.g. `postgresql://user:pass@host:5432/db`).
* Pool constructed lazily on first use; if unset, calls fail soft (returning empty results / no-ops) so non-DB features still boot.
* Optional sizing via `PG_POOL_MIN` / `PG_POOL_MAX` env vars (both optional; defaults come from library).
* Health endpoint `/health` now includes a `db_pool` object: `{ "enabled": true, "opened": ..., "checked_out": ... }`.

Usage example:
```python
from app.db.pool import db
rows = db.fetchall("SELECT id, name FROM widgets LIMIT 10")
```

To swap to an external pooler (pgBouncer), just point `POSTGRES_DSN` at the pooler's host:port.

### Async Database Pool Migration (Step 1)

An asynchronous PostgreSQL pool (`AsyncConnectionPool`) is now initialized during app lifespan when any of `DATABASE_URL`, `SUPABASE_DB_URL`, `SUPABASE_DIRECT_URL`, or `POSTGRES_DSN` is set.

Key additions:
* Module: `app/db/async_db.py` with `init_async_pool()` and `AsyncDBClient`.
* Lifespan initializes the pool once; closed cleanly on shutdown.
* Dependency accessor: `from app.main import get_async_db_client_dep` returns `AsyncDBClient | None`.
* Transitional: synchronous `DBClient` still exists; migrate callers incrementally by switching to `await client.vector_search(...)`.

Env vars:
* `ASYNC_PG_POOL_MIN` (default 1)
* `ASYNC_PG_POOL_MAX` (default 10)

Sample use inside an async route:
```python
from fastapi import Depends
from app.main import get_async_db_client_dep

@router.get("/vector/sample")
async def sample(q: str, db = Depends(get_async_db_client_dep)):
  if not db:
    return {"results": []}
  # embed query separately to produce `vec`
  vec = embedder.embed_batch([q])[0]
  rows = await db.vector_search(vec, top_k=5)
  return {"results": rows}
```

TinyToolController (optional) is loaded during lifespan if `app.audio.integrated_audio_pipeline.TinyToolController` is present and can be retrieved via `from app.main import get_tiny_controller`.

### Vector Search Enhancements

Added capabilities in `AsyncDBClient`:
* Metadata filtering for vector search via JSONB `metadata @>` clauses.
* `lexical_search` leveraging PostgreSQL full-text (expects `chunk_tsv` column if enabled).
* `hybrid_search` combining vector + lexical results using Reciprocal Rank Fusion (RRF).

Endpoints:
* `GET /vector/search_async?q=...&top_k=5` – pure vector.
* `GET /vector/search_hybrid?q=...&user_id=abc&top_k=10` – hybrid with optional `user_id` metadata filter.

Env (optional future): create GIN index on `metadata` and a `chunk_tsv` tsvector column for performance.
1. `.env` (local only, git-ignored) – your real secrets.
2. `.env.example` – checked in; contains documented variables plus a generated section with placeholders or redacted values.
3. `.env.redacted` – a manually curated minimal snapshot for onboarding docs.

To regenerate the synchronized section in `.env.example` from your local `.env` and code usages:

```
python scripts/sync_env_example.py          # dry run (shows diff stats)
python scripts/sync_env_example.py --write  # apply updates
```

Safeguards:
- Real secret values are never copied; they are replaced with `__REDACTED__`.
- New variables discovered via `os.getenv` / `os.environ[...]` are appended in a generated block.
- Existing manual comments above the generated marker are preserved.

Cloud deployment guidance:
- Provide production overrides via your orchestrator (Docker Swarm / ECS task env / Kubernetes ConfigMap & Secrets).
- Do NOT bake secrets into images; inject at runtime.
- Rotate `JWT_SECRET`, Supabase keys, and any PAT / tokens before first prod launch.

If you add a new environment variable in code, re-run the sync script so the example stays current.

<!-- Directory Index: supabase/ -->

Quick refs:

- Architecture Overview: `docs/ARCHITECTURE_OVERVIEW.md` (spool/gate, ingestion_manifest, Go notifier)
- Ingest Notifier Contract: `docs/INGEST_NOTIFIER.md` (channels, events, payloads, env)
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

### Unified full sync (local + Supabase)

Use `scripts/supabase_full_sync.sh` for a comprehensive ordered apply, drift check, and optional reset of both local and remote public schemas.

Dry run (plan only):

```bash
./scripts/supabase_full_sync.sh
```

Apply to remote (requires `SUPABASE_DB_URL` or Supabase CLI project context):

```bash
./scripts/supabase_full_sync.sh --apply
```

Reset both schemas then apply (DANGEROUS – drops public schema contents):

```bash
./scripts/supabase_full_sync.sh --reset-local --reset-remote --apply --yes
```

Include a drift check (aborts on drift with code 3):

```bash
./scripts/supabase_full_sync.sh --drift-check --fatal-on-drift --json-drift-out drift.json
```

Destructive statements (DROP/ALTER DROP) are skipped unless `--allow-destructive` is provided.

## Supabase Env + Verification Helper

Use `scripts/supabase_env_sync.sh` to merge secrets and run schema verifiers in one step.

Examples:

Dry-run merge (no file writes) and show metrics SQL only:

```
./scripts/supabase_env_sync.sh \
  --target .env \
  --set SUPABASE_PROJECT_REF=ref123 --set SUPABASE_URL=https://ref123.supabase.co \
  --set SUPABASE_SERVICE_KEY=service_key --set SUPABASE_ANON_KEY=anon_key \
  --validate --run-metrics --metrics-plan --plan-only
```

Pull remote secrets from `app_secrets` then run both verifiers (execute):

```
SUPABASE_URL=https://ref123.supabase.co \
SUPABASE_SERVICE_KEY=service_key \
./scripts/supabase_env_sync.sh --pull-remote-secrets --target .env \
  --run-metrics --run-kg --validate --probe-db
```

Forward partition creation flags to metrics verifier:

```
./scripts/supabase_env_sync.sh --run-metrics --future-days 5 --hourly-today
```

Key flags:

| Flag | Purpose |
|------|---------|
| `--pull-remote-secrets` | Fetch secrets via `fetch_supabase_secrets.sh` and merge |
| `--set KEY=VAL` | Inline additions (repeatable) |
| `--overwrite` | Replace existing values instead of keeping them |
| `--validate` | Enforce required Supabase vars present |
| `--probe-db` | Connectivity check (Supabase CLI or psql) |
| `--run-metrics/--metrics-plan` | Run or plan metrics verifier |
| `--run-kg/--kg-plan` | Run or plan KG verifier |
| `--future-days/--hourly-today` | Partition ensure options (metrics) |
| `--plan-only` | Print resulting env (no write / no verifiers) |

Exit codes: 0 ok | 2 arg | 3 validation | 4 probe fail | 5 verifier fail.


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
## Predictive Micro-Model Controller (Embedded Calibration)

Lightweight in-process host for tiny heuristic or micro-ML models that gently adjust
router confidence or emit advisory signals. Default is inert unless explicitly enabled.

Activation:

```
ENABLE_ROUTE_CALIB=1  # turns on route_calibration model
```

Current model: `route_calibration` (logistic-style score over simple text + context
features) producing a small bounded confidence adjustment (|Δ| <= ~0.05).

Endpoints impact:
- `/switchr/route`: Adds reasons `route_calib_adj:+0.XXX` and `route_calib_applied` when
  active.
- `/switchr/health`: Includes predictive cache stats:
  `{ "predictive_enabled": true, "predictive_cache": { "models": [...], ... } }`.

Environment variables:
| Var | Default | Purpose |
|-----|---------|---------|
| ENABLE_ROUTE_CALIB | 0 | Enable predictive controller + route calibration model |

Design constraints:
- No network I/O; pure Python arithmetic.
- Sub‑millisecond typical latency per model.
- Deterministic feature hashing -> in-memory cache (hit ratio in stats).

Add a new model:
1. Create `app/predictive/models/<name>.py` exposing a predictor class with `predict(ctx)`.
2. Register in `app/predictive/controller.py` (`_load_models`).
3. Gate behind its own `ENABLE_<FLAG>` or composite flag.
4. Extend `features.py` if new feature extraction needed.
5. Return a dict containing any numeric scores / adjustments.

Failure mode: model exceptions are caught and surfaced as `{"error": "model_error:<Type>"}`
and skipped by the router (no adjustment). Cache remains valid for successes.

### Leonardo Analytical Audio Suite

Endpoints (always mounted when import succeeds):

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/leonardo/speak` | Piper TTS (voices: leonardo, analytical, teaching, encouraging) |
| POST | `/leonardo/think` | Analytical LLM reasoning (Mistral 7B variant) optionally with TTS |
| POST | `/leonardo/listen` | Whisper (CLI) speech-to-text transcription |
| POST | `/leonardo/analyze-and-speak` | Combined think + speak convenience endpoint |
| GET  | `/leonardo/status` | Capability probe (LLM, TTS, STT) |

Env (optional overrides):

| Var | Default | Purpose |
|-----|---------|---------|
| LEONARDO_URL | (falls back to `OLLAMA_URL`) | Base URL for Leonardo (Ollama style) |
| LEONARDO_MODEL | `mistral:7b` | Model name served by Leonardo backend |
| LLM_DEFAULT_PREFER | (unset) | Set to `leonardo` to make it default for /leonardo/think |

Runtime binaries required on PATH:
 - `piper` (for TTS)
 - `whisper` (whisper.cpp CLI build)

Degradation:
 - Missing `piper` only affects `/leonardo/speak` (500) and audio portion of `think`.
 - Missing `whisper` only affects `/leonardo/listen` (500).
 - `/leonardo/status` returns `partial` or `down` instead of raising.

Notes:
 - TTS uses ephemeral temp files; responses default to base64 audio payload.
 - Setting `LLM_FORCE_PREFER=leonardo` will also route general LLM calls to Leonardo unless explicitly overridden per request.


## Hybrid DB Model (Supabase + Pg_Partman/cron)

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

## AoS Match Outcome Predictor (Exploratory)

A lightweight exploratory script (`scripts/aos_predict.py`) trains a logistic regression model
on historical Age of Sigmar match data (`aos_matches` table) using rolling performance,
player streak, faction/opponent categorical features, and simple recency.

Status: experimental (not on an API route / no persistence yet). Intended for quick local
analysis and feature ideation ahead of a more formal predictive layer.

Table expectation (`aos_matches`):
```
ts TIMESTAMPTZ,
season TEXT,
player TEXT,
opponent TEXT,
faction TEXT,
opponent_faction TEXT,
outcome TEXT,         -- 'win' | 'loss' | 'draw'
score INT,            -- optional / unused currently
meta JSONB            -- optional, not modeled yet
```

Features engineered:
- Rolling wins / win-rate over a configurable past-N window (default 10).
- Streak (signed consecutive wins or losses, reset on draw).
- Recency gap (days since prior match per player, fallback 7 days).
- Categorical encoding of season, opponent, faction, opponent_faction.

CLI flags:
```
--dsn          PostgreSQL/Timescale DSN (required)
--schema       Optional schema prefix added to search_path (e.g., pii)
--player       Filter to a single player (personalized model)
--window       Rolling window size (default 10)
--test-size    Holdout fraction (default 0.2)
--random-state RNG seed (default 42)
```

Example:
```bash
./scripts/aos_predict.py \
  --dsn "postgresql://user:pass@localhost:5432/game" \
  --schema pii \
  --player demo_player \
  --window 12
```

Output example:
```
[aos-predict] metrics: {'auc': 0.69, 'accuracy': 0.61}
```
(AUC may be NaN if the holdout contains only one class.)

Future roadmap (see TODOs in script): model persistence, coefficient/odds reporting,
matchup interaction features, calibration curves, time-decay weighting, and opponent
rolling stats.

---
