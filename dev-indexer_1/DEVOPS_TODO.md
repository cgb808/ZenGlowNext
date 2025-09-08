## 13. XTTS Voice Cloning (2025-09-04)
- [ ] Integrate /audio/xtts_clone endpoint for Coqui XTTS v2 voice cloning
- [ ] Support reference wav upload and text synthesis
- [ ] Track future expansion: caching cloned voices, multi-speaker sessions
## 12. Embedding Service (2025-09-04)
- [ ] Integrate /model/embed endpoint using sentence-transformers (configurable via EMBED_MODEL)
- [ ] Add fallback deterministic hash-based embedding for environments without transformers
- [ ] Ensure embedding service is available to RAG pipeline and Switchr Router
## 11. Audio/Voice/Chat Features (2025-09-04)
- [ ] Integrate audio device discovery endpoints (`/audio/devices`) using sounddevice/PyAudio
- [ ] Add TTS/STT endpoints for Leonardo and WhisperCCP (see `/leonardo/speak`, `/leonardo/listen`, `/audio/transcribe`)
- [ ] Dashboard: add chat window, volume/mic controls, plugin hooks for extensibility
- [ ] Ensure proper host device mapping for audio in containers (Docker/Swarm)
- [ ] Track plugin architecture and extensibility for dashboard and backend
# DevOps / Platform TODO (Family Context, Persistence, Datasets)
Last updated: 2025-09-04
---
**Speaker Recognition & Enrollment Router**
- Provides endpoints for speaker enrollment (/audio/speaker/enroll), identification (/audio/speaker/identify), and voice cloning (/audio/speaker/identify_clone, /audio/speaker/clone_profile).
- Uses Resemblyzer for voice embeddings (optional), stores profiles in memory (future: persist to DB).
- Integrates XTTS for voice cloning from reference audio.
- Dependencies: FastAPI, numpy, Resemblyzer, XTTS, audio file handling.
- Devops: Ensure audio storage directory, optional Resemblyzer install, XTTS script availability, and endpoint wiring in main app.
- [ ] Connection middleware: set `SET LOCAL app.current_user` per request
- [ ] Add audit log table (access + denial events)
- [ ] Add health metric upsert endpoint backed by Postgres repo
- [ ] Implement artifact tag search (GIN index already present)
- [ ] PII Vault service design (separate DB) & `PIIRepository` scaffold
## 2. Data Masking & Policy
---
**LLM Backend Probe Endpoint**
- Provides /llm/probe for lightweight diagnostics of LLM backends (Edge, Ollama, llama.cpp).
- Attempts short generations to check reachability and error states; helps UI explain empty answers.
- No caching; intended for ad-hoc diagnostics.
- Dependencies: FastAPI, LLMClient, environment variables for backend URLs/keys.
- Devops: Ensure backend URLs/keys are set, endpoint wiring in main app, and backend services are reachable.
## 3. Dataset / Fine-Tune Pipeline
- [x] Instruction + conversation exporters (`scripts/export_family_dataset.py`, `scripts/export_family_conversations.py`)
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
- Provides /rag/stream_query SSE endpoint emitting phased ranking data for RAG queries (P0: similarity, P1: LTR, P2: contextual adjustments).
- Event format: SSE lines with phase, provisional flag, results, and optional extras.
- Future: dual index routing, memory/source blending, LM-based rescoring, delta emission.
- Dependencies: FastAPI, StreamingResponse, DBClient, Embedder, feature assembler, LTR model.
- Devops: Ensure DB connectivity, SSE support, endpoint wiring, and environment variable configuration.
## 5. Application Refactor
- [ ] Introduce repository abstraction usage in router (switch between in-memory and PG)
- [ ] Dependency injection pattern (FastAPI startup deciding backend)
- [ ] Background job: periodic sync (if hybrid mode used) – or remove once PG authoritative
- [ ] Event logging table (timeline events persistence)
## 6. Observability
**Leonardo Audio Integration Router**
## 8. Tooling / Dev Experience
---
- Provides /ws/metrics for real-time dashboard monitoring; streams system, model, and query stats to connected clients.
- Includes /ws/metrics/status for connection info and update interval.
- Dependencies: FastAPI, WebSocket, health/system metrics modules.
- Devops: Ensure endpoint wiring, dashboard integration, and periodic update interval (5s) is configurable if needed.
- [ ] Vault schema (pii_subjects, pii_identifiers)
## 10. Backlog / Ideas
**Operational Diagnostics Endpoints**
**Hybrid Router Config & Routing Rules**
**Diagnostics Endpoints**
Backend: Add diagnostics endpoints (env snapshot, import status, TCP probe, summary) via FastAPI router `/diagnostics/*`.
Purpose: Quick operational visibility for triage when system is down; avoids heavy dependencies.
Endpoints:
	- `/diagnostics/env`: Show selected environment variables
	- `/diagnostics/imports`: Show status of key Python imports
	- `/diagnostics/tcp`: Probe TCP connectivity to host:port
	- `/diagnostics/summary`: Composite view (env, imports, connectivity)
Goal: maximize training richness.
Planned quick wins:
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
- Track config/env: API_GATEWAY_KEY, CURATED_DATASET_DIR, CURATED_FILE, PACKED_FILE, MANIFEST_FILE, DATASET_SHARE_KEY
- Ensure structured logging, global exception handler, audit middleware
- Document dataset distribution flow and security model
**In-Memory Rolling Log Buffer**
Backend: Add in-memory rolling log buffer for ad-hoc debugging in UI (not for production/multi-process).
Features:
	- Stores last N log lines (with incremental ids, timestamp, level, message)
	- Frontend polls `/logs/recent?since=<last_id>` for new lines
	- `RollingBuffer` class: append, since
	- `BufferHandler` for logging integration
	- `install()` to add handler to root logger
**Central Logging Configuration**
Backend: Add central logging config module for root logger and format (plain or JSON).
Features:
	- Single place to configure root logger, format, and level (via env)
	- Support LOG_JSON=true for JSON logs
	- LOG_LEVEL env for log level
	- Per-request correlation id support (LOG_REQUEST_IDS)
	- Helper: `with_ctx()` for structured logging with extra fields
	- `init_logging()` for initialization
**Lightweight In-Process Metrics**
Backend: Add lightweight in-process metrics for local observability/debugging (no external deps).
Features:
	- Rolling latency samples (capped list, percentiles, avg, max)
	- Simple counters (requests, errors, LLM/retrieval calls)
	- Thread-safe via basic locking
	- `inc()` for counters, `observe()` for latency, `snapshot()` for metrics view
	- `Timer` class for measuring elapsed ms
**Redis Cache & Messaging Utilities**
Backend: Add Redis cache and messaging utilities (high-level class + functional helpers).
Features:
	- Env-driven connection (REDIS_HOST/PORT/DB/PASSWORD/SSL, REDIS_URL)
	- JSON and MessagePack serialization
	- Namespaced key hashing (MD5) to prevent oversized keys
	- RAG query result caching helpers (msgpack by default)
	- Build update Pub/Sub publishing
	- Graceful dependency and connection handling (no-op fallback)
	- Functional API: cache_set_json, cache_get_json, cache_set_msgpack, cache_get_msgpack, cache_delete, cache_rag_query_result, get_cached_rag_query, publish_build_update
**Secrets Retrieval Utilities (Supabase Indexer Service Key)**
Backend: Add secrets retrieval utilities for Supabase indexer service key (no hardcoding in .env).
Features:
	- Priority: env var SUPABASE_INDEXER_SERVICE_KEY, fallback to Postgres Vault extension
	- Mirrors value into SUPABASE_KEY for downstream modules
	- Caches value for process lifetime
	- Functions: get_supabase_indexer_service_key, get_supabase_indexer_service_key_with_source, bootstrap_supabase_key
**Config Helpers & /config/env Endpoint**
Expose FastAPI router `/config/env` for operational visibility (excludes secrets).
	- `/config/env`: Show sanitized environment snapshot
- Supports drag/swipe, recording, mute, and volume features; displays active model info.
- Devops: Integrate into web dashboard, ensure audio controls and model selection are functional, and wire up backend model status.

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
