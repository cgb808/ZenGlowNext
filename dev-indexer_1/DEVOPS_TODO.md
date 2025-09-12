## A. Embedding Worker & Index Optimization (2025-09-10)

Status: Implemented baseline auto-index (BRIN) & target-store switch.

Features now in repo:
- optional_brin_indexes.sql applied automatically by `db_apply.sh` (core path)
- Worker env flags:
  - EMBED_TARGET=pgvector|chroma|none (default pgvector)
  - BRIN_MIN_ROWS (default 500000) threshold for self-heal BRIN creation
  - SELF_HEAL_INDEXES=1 enables startup check creating `brin_conversation_events_time`
- README updated (Staged Embedding Worker Startup + env table)

Operational Notes:
- BRIN kept even for small DB (cheap metadata); value grows with large append-only volumes.
- Change BRIN_MIN_ROWS to 0 to force immediate index creation.
- Future Chroma path: implement branch in gating worker where EMBED_TARGET=chroma posts embeddings and marks rows embedded (skip pgvector column update).
- Safe to re-run `db_apply.sh core`; IF NOT EXISTS guards prevent duplication.

Action Items:
- [ ] Implement Chroma client branch in worker (EMBED_TARGET=chroma)
- [ ] Add metrics on worker (processed/sec, retry count) exposed via /metrics
- [ ] SECURITY DEFINER functions for any cross-schema token operations (if single-DB mode)
- [ ] Add automated EXPLAIN sampling script to confirm BRIN usage after N rows

## 13. XTTS Voice Cloning (2025-09-04)

- [ ] Support reference wav upload and text synthesis
- [ ] Track future expansion: caching cloned voices, multi-speaker sessions

## 12. Embedding Service (2025-09-04)
- [ ] Integrate /model/embed endpoint using sentence-transformers (configurable
      via EMBED_MODEL)
      transformers
- [ ] Ensure embedding service is available to RAG pipeline and Switchr Router

## 11. Audio/Voice/Chat Features (2025-09-04)
      sounddevice/PyAudio
- [ ] Add TTS/STT endpoints for Leonardo and WhisperCCP (see `/leonardo/speak`,
      extensibility
    - LEONARDO_MODEL (default mistral:7b)
- [x] Compose/db init mounts finalized for local core + pii

Status (2025-09-08):
- Initial Swarm scaffold added:
  - deploy/docker-stack.yml with limits (<=4 CPUs total, ~20GiB RAM split across services), overlay network, volumes.
  - Makefile targets: swarm-init, swarm-deploy, swarm-ps, swarm-rm.
  - VS Code tasks for Swarm operations.
- Next:
  - Secrets/Configs for DB creds and JWT.
  - Healthchecks/depends_on alternatives (Swarm ignores depends_on; rely on retries/backoff in app).
  - Smoke tests for app/db/redis endpoints post-deploy.
  - PII: pii_secure_schema

  Operational ingestion:
  - Spool automation documented in `docs/INGESTION_SPOOL.md` with watcher + orchestrator scripts and a systemd unit template.

## 15. Docker Swarm Light Deploy (Target)

Constraints:
- Max 4 CPU cores, ~20 GiB RAM budget
- No CUDA deployment yet (plan node labels for future GPU worker)

Scope (minimal viable services):
- FastAPI app (core API)
- Postgres core (rag_db) + Postgres pii (rag_pii)
- Redis cache (AOF) with persistent volume (ZFS or swarm volume)
- Whisper service (Alpine-based image, CPU build)
- Indexer model: bsg-small for embedding with sidecar (HTTP/embed API)
- Voice model sidecar: chosen TTS (TBD) with lean footprint
- Phi-3-mini CUDA: define as a separate stack/service with placement label, do not deploy yet

Swarm tasks:
- [ ] Create `docker-stack.yml` with compose v3.8 deploy blocks (replicas=1)
- [ ] Add per-service resource limits/requests (CPU/Memory) to fit budget
- [ ] Define overlay networks: `frontend`, `backend` (db isolated)
- [ ] Convert volumes to swarm-compatible (local driver or nfs) for db/redis
- [ ] Add healthchecks and restart policies to all services
- [ ] Externalize secrets/configs (DB creds, JWT, API keys) via `secrets`/`configs`
- [ ] Whisper CPU image (alpine) – verify size and startup time
- [ ] Indexer sidecar (bsg-small) – HTTP endpoint and env wiring (EMBED_BASE_URL)
- [ ] Voice TTS sidecar – select model and tune resource limits
- [ ] Defer phi-3-mini: add service stub with `deploy.placement.constraints` (node.labels.gpu==true), scale=0
- [ ] Add Makefile targets: `swarm:init`, `swarm:deploy`, `swarm:rm`
- [ ] Smoke tests script: health, db, redis, whisper, embed, tts

Resource baseline (targets):
- db core: 2 CPU, 8 GiB; db pii: 1 CPU, 4 GiB
- whisper (alpine, cpu): 1 CPU, 2 GiB
- indexer sidecar (bsg-small): 1 CPU, 2–4 GiB

      ### 17. Redis cache client wrapper (planned)

      - Preserve legacy keys: `rag:q:<sha1(query)>:<top_k>`.
      - Add namespaced JSON/MsgPack helpers using MD5 for internal key hashing.
      - Pub/Sub: `publish_build_update` envelope compatible with `publish_build_update.py`.
      - Env: REDIS_HOST/PORT/DB/PASSWORD/SSL, DEFAULT_TTL_SECONDS, REDIS_BUILD_CHANNEL.
      - Research: serialization perf (json vs msgpack), retry/backoff strategy, TLS/ACLs for remote Redis, namespace flush cost.

## 16. CUDA Model Services (Planned; do not deploy CUDA yet)

Models:
- Phi-3-mini (inference) – CUDA-ready
- BGE-small (quantized) – embedding sidecar for indexer (HTTP)
- Apple mini “tooling agent” (model TBD; CUDA via vLLM or Ollama CUDA build)

Tasks:
- [ ] Define model images/backends
  - Phi-3-mini: vLLM or Ollama (CUDA build); expose /v1/chat or /generate
  - BGE-small-quant: lightweight embedding server; expose /embed
  - Apple-mini agent: pick model (e.g., OpenELM 3B) + backend (vLLM/Ollama)
- [ ] Standardize env:
  - PHI3_MODEL (default phi3:mini)
  - BGE_EMBED_MODEL (default BAAI/bge-small-en-v1.5)
  - BGE_QUANT (default 8bit)
  - TOOLING_AGENT_MODEL (default TBD), TOOLING_AGENT_BACKEND (vllm|ollama)
- [ ] Add Swarm service stubs with `deploy.placement.constraints` for GPU node
- [ ] Add resource limits (each <=1–2 CPU, 2–6 GiB depending service)
- [ ] Healthchecks + readiness for all model endpoints
- [ ] Do not schedule on non-GPU nodes until GPU label present; keep replicas 0 or stack omitted


**Speaker Recognition & Enrollment Router**

- Provides endpoints for speaker enrollment (/audio/speaker/enroll),
  identification (/audio/speaker/identify), and voice cloning
  (/audio/speaker/identify_clone, /audio/speaker/clone_profile).
- Uses Resemblyzer for voice embeddings (optional), stores profiles in memory
  (future: persist to DB).
- Integrates XTTS for voice cloning from reference audio.
- Dependencies: FastAPI, numpy, Resemblyzer, XTTS, audio file handling.
- Devops: Ensure audio storage directory, optional Resemblyzer install, XTTS
  script availability, and endpoint wiring in main app.
- [ ] Connection middleware: set `SET LOCAL app.current_user` per request
- [ ] Add audit log table (access + denial events)
- [ ] Add health metric upsert endpoint backed by Postgres repo
- [ ] Implement artifact tag search (GIN index already present)
- [ ] PII Vault service design (separate DB) & `PIIRepository` scaffold

## 2. Data Masking & Policy

---

**LLM Backend Probe Endpoint**

- Provides /llm/probe for lightweight diagnostics of LLM backends (Edge, Ollama,
  llama.cpp).
- Attempts short generations to check reachability and error states; helps UI
  explain empty answers.
- No caching; intended for ad-hoc diagnostics.
- Dependencies: FastAPI, LLMClient, environment variables for backend URLs/keys.
- Devops: Ensure backend URLs/keys are set, endpoint wiring in main app, and
  backend services are reachable.

  Current wiring:
  - LLMClient recognizes prefer values: edge, ollama, llama, leonardo/mistral.
    Leonardo backend uses LEONARDO_URL/LEONARDO_MODEL (defaults to Ollama at
    http://leonardo:11434).
  - To keep dev app responsive without GPU: set
    `LLM_DISABLE=ollama,llama,llama.cpp`.

## 3. Dataset / Fine-Tune Pipeline

- [x] Instruction + conversation exporters (`scripts/export_family_dataset.py`,
      `scripts/export_family_conversations.py`)
- [x] Unified build script + manifest (`scripts/build_family_dataset.py`)
- [ ] Add dataset versioning + semantic diff script
- [ ] Add retrieval augmentation (context passages) pre-training
- [ ] Scenario balancing config file (YAML) instead of CLI weights
- [ ] Add negative / refusal examples expansion (more policy edge cases)
- [ ] Generate evaluation set (hold-out) manifest
- [ ] Add license / provenance metadata to manifest

## 4. Testing & CI

---

**Streaming Diff API Scaffold (Artifact D)**

- Provides /rag/stream_query SSE endpoint emitting phased ranking data for RAG
  queries (P0: similarity, P1: LTR, P2: contextual adjustments).
- Event format: SSE lines with phase, provisional flag, results, and optional
  extras.
- Future: dual index routing, memory/source blending, LM-based rescoring, delta
  emission.
- Dependencies: FastAPI, StreamingResponse, DBClient, Embedder, feature
  assembler, LTR model.
- Devops: Ensure DB connectivity, SSE support, endpoint wiring, and environment
  variable configuration.

## 5. Application Refactor

- [ ] Introduce repository abstraction usage in router (switch between in-memory
      and PG)
- [ ] Dependency injection pattern (FastAPI startup deciding backend)
- [ ] Background job: periodic sync (if hybrid mode used) – or remove once PG
      authoritative
- [ ] Event logging table (timeline events persistence)

## 6. Observability

**Leonardo Audio Integration Router**

## 8. Tooling / Dev Experience

---

- Provides /ws/metrics for real-time dashboard monitoring; streams system,
  model, and query stats to connected clients.
- Includes /ws/metrics/status for connection info and update interval.
- Dependencies: FastAPI, WebSocket, health/system metrics modules.
- Devops: Ensure endpoint wiring, dashboard integration, and periodic update
  interval (5s) is configurable if needed.
- [ ] Vault schema (pii_subjects, pii_identifiers)

## 10. Backlog / Ideas

**Operational Diagnostics Endpoints** **Hybrid Router Config & Routing Rules**
**Diagnostics Endpoints** Backend: Add diagnostics endpoints (env snapshot,
import status, TCP probe, summary) via FastAPI router `/diagnostics/*`. Purpose:
Quick operational visibility for triage when system is down; avoids heavy
dependencies. Endpoints: - `/diagnostics/env`: Show selected environment
variables - `/diagnostics/imports`: Show status of key Python imports -
`/diagnostics/tcp`: Probe TCP connectivity to host:port -
`/diagnostics/summary`: Composite view (env, imports, connectivity) Goal:
maximize training richness. Planned quick wins:

## ZenGlow Indexer Health & Metrics Router

    - `/health`, `/health/ollama`, `/health/db`, `/health/models`, `/health/aggregated`

- Add metrics endpoints:
  - `/metrics/json`: key RAG metrics (query stats, model registry, system)
  - `/metrics`: Prometheus metrics (Counter, Histogram)
- Document health/metrics API usage and dashboard wiring

## ZenGlow Gateway API

- Add FastAPI gateway for health, readiness, and admin endpoints:
  - `/health`, `/ready`: system status
  - `/admin/ping`: API key-protected admin ping
  - `/dataset/manifest`: dataset manifest (env/config, key-protected)
  - `/dataset/stream`: dataset streaming (key-protected)
- Track config/env: API_GATEWAY_KEY, CURATED_DATASET_DIR, CURATED_FILE,
  PACKED_FILE, MANIFEST_FILE, DATASET_SHARE_KEY
- Ensure structured logging, global exception handler, audit middleware
- Document dataset distribution flow and security model **In-Memory Rolling Log
  Buffer** Backend: Add in-memory rolling log buffer for ad-hoc debugging in UI
  (not for production/multi-process). Features: - Stores last N log lines (with
  incremental ids, timestamp, level, message) - Frontend polls
  `/logs/recent?since=<last_id>` for new lines - `RollingBuffer` class: append,
  since - `BufferHandler` for logging integration - `install()` to add handler
  to root logger **Central Logging Configuration** Backend: Add central logging
  config module for root logger and format (plain or JSON). Features: - Single
  place to configure root logger, format, and level (via env) - Support
  LOG_JSON=true for JSON logs - LOG_LEVEL env for log level - Per-request
  correlation id support (LOG_REQUEST_IDS) - Helper: `with_ctx()` for structured
  logging with extra fields - `init_logging()` for initialization **Lightweight
  In-Process Metrics** Backend: Add lightweight in-process metrics for local
  observability/debugging (no external deps). Features: - Rolling latency
  samples (capped list, percentiles, avg, max) - Simple counters (requests,
  errors, LLM/retrieval calls) - Thread-safe via basic locking - `inc()` for
  counters, `observe()` for latency, `snapshot()` for metrics view - `Timer`
  class for measuring elapsed ms **Redis Cache & Messaging Utilities** Backend:
  Add Redis cache and messaging utilities (high-level class + functional
  helpers). Features: - Env-driven connection (REDIS_HOST/PORT/DB/PASSWORD/SSL,
  REDIS_URL) - JSON and MessagePack serialization - Namespaced key hashing (MD5)
  to prevent oversized keys - RAG query result caching helpers (msgpack by
  default) - Build update Pub/Sub publishing - Graceful dependency and
  connection handling (no-op fallback) - Functional API: cache_set_json,
  cache_get_json, cache_set_msgpack, cache_get_msgpack, cache_delete,
  cache_rag_query_result, get_cached_rag_query, publish_build_update **Secrets
  Retrieval Utilities (Supabase Indexer Service Key)** Backend: Add secrets
  retrieval utilities for Supabase indexer service key (no hardcoding in .env).
  Features: - Priority: env var SUPABASE_INDEXER_SERVICE_KEY, fallback to
  Postgres Vault extension - Mirrors value into SUPABASE_KEY for downstream
  modules - Caches value for process lifetime - Functions:
  get_supabase_indexer_service_key,
  get_supabase_indexer_service_key_with_source, bootstrap_supabase_key **Config
  Helpers & /config/env Endpoint** Expose FastAPI router `/config/env` for
  operational visibility (excludes secrets). - `/config/env`: Show sanitized
  environment snapshot

      Implemented behavior:
      - Includes prefixes: PG_, RAG_, OLLAMA_, CORS_, EMBED_, ASYN and explicit SUPABASE_URL
      - Excludes keys containing: KEY, TOKEN, SECRET, PASS, PASSWORD
      - Truncates long values (>200 chars) with ellipsis
      - Helper: `get_sanitized_env_snapshot()` in `app/core/config.py`
      - Tests: `tests/test_env_snapshot.py`

- Supports drag/swipe, recording, mute, and volume features; displays active
  model info.
- Devops: Integrate into web dashboard, ensure audio controls and model
  selection are functional, and wire up backend model status.

## System Metrics Collection Module

## WebSocket Metrics Streaming Module & Router

## Similarity Retrieval Logic for RAG Pipeline

## RAG Pipeline Core Logic

## Feature Assembly Scaffold (Artifact B)

## Embedding Generator Module

## Supabase Edge Function Integration

## Pydantic Schemas for RAG API and DB Rows

## Postgres Store Utilities for RAG Pipeline

## Streaming Diff API Scaffold (Artifact D)

## FastAPI Entrypoint for ZenGlow Indexer API

## app/ Service Code Structure & Docs

    - rag/: Retrieval pipeline (retrieval, feature assembly, ranking, fusion, LLM invocation)
    - core/: Config, metrics, logging, diagnostics, caching, secrets
    - audio/: Transcription & TTS endpoints and helpers
    - health/: Health & readiness probes
    - central_control/: (Planned) orchestration / routing logic
    - Project Overview: ../README.md
    - DevOps Practices: ../docs/devops/DEVOPS.md
    - RAG Integration: ../docs/integration/MCP_RAG_INTEGRATION.md

## Missing Documentation & Resource Recovery

- All missing docs/resources are located at:
  https://github.com/cgb808/dev-indexer_1/tree/main/docs
- User will handle authentication for access
- Use this location for recovery, reference, and devops planning

**Switchr Router**
