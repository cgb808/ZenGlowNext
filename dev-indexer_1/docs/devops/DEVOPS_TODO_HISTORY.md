<!-- Relocated from repository root on 2025-08-30 -->
<!-- Relocated from repository root on 2025-08-30; canonical now under docs/devops/ -->
[Back to Docs Index](../DOCS_INDEX.md) | [DevOps Overview](./DEVOPS.md)

# DevOps Operational TODO & History
Last Updated: 2025-08-31

Purpose:
Single pane for (a) active DevOps / platform engineering backlog, (b) recently completed infrastructure & operations work, and (c) timeline context so new contributors (or automation) can understand why things exist.

---
## 1. Active Backlog (Canonical)
Legend: [P]=Planned / not started, [WIP]=In progress, [BLK]=Blocked, [R]=Research, [D]=Done (awaiting verification)

### 1.1 Instrumentation & Observability
- [P] Stage timing instrumentation (retrieve_ms, feature_ms, ltr_ms, fusion_ms) in pipeline; surface via answer_meta.timings & /metrics/json
- [P] Prometheus histograms for each stage latency
- [P] OpenTelemetry tracing spans (ingress -> retrieve -> features -> ltr -> fusion -> generate)
- [P] Structured JSON logging w/ request_id + correlation_id headers
- [R] Persistent performance store (TimescaleDB hypertable query_performance)
- [P] Extended /metrics/json: token usage, backend selection counts, TTS/STT request counts
- [P] Predictive model metrics aggregation task (daily histogram of route adjustments & fallback deltas)

### 1.2 Retrieval & Fusion
- [P] Fusion weights endpoint (GET/PUT /rag/fusion/weights) + in-memory cache + optimistic reload
- [P] Retrieval mode branching (env RAG_RETRIEVAL_MODE: pgvector | supabase_rpc) with health preflight on startup
- [R] ANN strategy table (future HNSW / IVF) behind feature flag

### 1.3 Security & Governance
- [P] API key middleware toggle (ENABLE_API_KEYS) + key hash storage
- [P] Redis token bucket rate limiting for /rag/*
- [P] PII / secrets scrub filter for logs & /config/env output
- [R] mTLS / Zero-Trust ingress (stretch)

### 1.4 Model & Audio Ops
- [P] Dynamic model registry refresh (hot add/remove) + readiness state
- [P] Per-model rolling throughput & latency samples (tokens/sec, p95)
- [P] TTS voice registry endpoint exposure
- [R] Automatic selection heuristic: choose backend by size + latency SLO
- [P] Predictive anomaly detector (fallback oscillation) model
- [P] Vector param selector model (embed model / top_k tuning)

### 1.5 Data & Caching
- [P] Feature cache hit/miss metrics with reason codes
- [P] Response cache invalidation hooks (doc updates, fusion weight change)
- [R] Vector store abstraction adapter layer
- [P] Predictive signals schema + storage (aggregated only, no raw text)

### 1.6 Fine-Tuning & Training Infrastructure
- [P] Base model + specialization training pipeline automation
- [P] Mistral7b LLM-as-Judge integration for dataset validation
- [P] Training data quality scoring and confidence thresholds
- [P] Model versioning and artifact management for specialized models
- [P] Interruption handling model deployment pipeline
- [P] Post-finetune Jarvis inference deployment automation (export -> registry update -> gated logprob smoke test)
- [R] Multi-GPU training orchestration for larger models

### 1.7 CI / Release
- [P] GitHub Actions CI: lint + tests + coverage badge publish
- [P] Cache Python deps keyed by requirements hash
- [P] Make target: make freeze ( lockfile & diff guard )
- [P] Release tagging script: derive semantic pre-release from short commit & date

### 1.8 Automation & Memory
- [P] Auto-run scripts/index_codebase.py post-merge; if diff significant -> run memory-save snapshot
- [P] Persist model registry + fusion weights snapshot into Memory MCP
- [P] Knowledge graph enrichment with new entities on major feature add

### 1.9 Developer Experience
- [P] Local smoke command (make smoke) hitting /health, /rag/query, /audio/tts, /audio/transcribe
- [P] Onboard script printing missing env & suggested defaults
- [R] Pre-commit hook: black + isort + pyright subset

### 1.10 Ingestion Reliability & RAG Bridge
- [D] Embedding / DB retry & backoff implementation (memory_rag_bridge)
- [D] Offset persistence sidecar (resume after restart) w/ CLI --reset-offset
- [D] Unit tests for memory_rag_bridge (offset resume, retry failure path, search)
- [P] Additional tests: DB transient error simulation path
- [P] Periodic metrics for ingestion (ingested_count, retry_count, last_offset)
- [P] Sidecar compaction / rotation strategy (large file lifecycle)
- [P] Replay pipeline integration test (msgpack -> embeddings -> search sanity)
- [R] Auto-ingest canary verification (sample search queries post-restart)

### 1.11 Predictive Layer (New)
- [D] Predictive controller scaffolding (route_calibration model)
- [D] Router integration via ENABLE_ROUTE_CALIB flag (confidence adjustment + reasons)
- [D] Health endpoint predictive stats (cache hits/misses, models list, fallback rate)
- [P] Session id plumbed into predictive context (voice + text routes)
- [P] Daily aggregation script: persist histogram (adjustment buckets, fallback deltas)
- [P] Anomaly detection micro-model (fallback oscillation)
- [P] Vector parameter selection micro-model (embedding model / top_k tuning)
- [P] Predictive signals store schema & ETL (aggregated only)
- [R] Cache hit forecast model (pre-warm strategy)

---
## 2. Recently Completed (Chronological)
2025-08-31
- **RAG Bridge Reliability Tests**: Added `tests/test_memory_rag_bridge.py` covering offset persistence, retry failure, and search path.
- **Offset Persistence Implementation**: Sidecar JSON with atomic writes + CLI reset flag integrated into memory bridge.
- **Retry/Backoff Operationalized**: Exponential backoff w/ jitter for embedding & DB operations (configurable env tunables).
- **Docs Updated**: MEMORY_RAG_INTEGRATION.md, MCP_RAG_INTEGRATION.md, RAG_REPLAY_PIPELINE.md reflect persistence & replay.
- **Pre-commit Hygiene**: Enforced ruff/black/isort/mypy + size & root hygiene guards (earlier; now validated in tests context).
- **Predictive Controller Integration**: Added `ENABLE_ROUTE_CALIB` gated route calibration adjustment + health stats (cache metrics, fallback rate) and documentation `app/predictive/PREDICTIVE_CONTROLLER.md`.

2025-08-28
- **Leonardo Voice Integration**: Connected TTS (Piper) and Whisper speech recognition to Leonardo (Mistral 7B)
- **Model Upgrade**: Successfully migrated Leonardo from smaller models to Mistral 7B (4.4GB) in Docker environment
- **Voice Architecture**: Created comprehensive app/leonardo/audio_router.py with speak, listen, think, analyze endpoints
- **Setup Automation**: Built scripts/setup_leonardo_voice.sh with complete voice capability installation framework
- **Environment Resolution**: Resolved Docker vs host confusion - confirmed Leonardo operational in containerized environment
- **Voice Framework**: Integrated British analytical TTS voice, Whisper speech recognition, complete testing suite ready for deployment
- Complete Docker Compose stack deployment with 4 services (backend, ollama, redis, webui)
- Docker Compose YAML syntax debugging and port conflict resolution
- Ollama LLM service integration with gemma:2b model installation and validation
- Service networking and health check validation (backend healthy, LLM functional)
- Makefile automation targets: compose-up, compose-restart with automated cleanup
- Docker Compose documentation with troubleshooting guide and operational nuances
- Container orchestration with proper service dependencies and health verification

2025-08-27
- Dual-agent React chat UI (Gemma / Edge / Ollama / Llama backends selectable) with persona selector
- Integrated Piper TTS playback & Whisper.cpp STT recording workflow
- Cleaned duplicate experimental UI & model folders -> archived (reduces index noise)
- Memory snapshot tooling (memory-save.mjs, memory-restore.mjs) with atomic latest pointer
- Knowledge graph artifacts (entities, relations, Mermaid diagram, narrative) exported & versioned
- Indexing script enhancement: archive/ exclusion + diff (added/removed/changed) output
- Refactored GemmaPhi.tsx after duplication; consolidated to single component
- Frontend metrics polling controls (env vars: VITE_DISABLE_METRICS*, cooldown & polling disable) documented in README and added to `.env.example` (network chatter mitigation)

2025-08-26
- Backcompat env variable shim (legacy FUSION_* -> RAG_FUSION_*) & required env validation
- Sanitized /config/env endpoint (excludes secrets)
- Basic Prometheus & JSON metrics endpoints (system + query counters)
- Feature + full response cache layers (Redis)
- Workspace cleanup & venv normalization

---
## 3. Timeline (High-Level)
- Phase 1 (Foundations): Env validation, metrics scaffolding, caching, configuration hygiene
- Phase 2 (Context Capture): Indexing script, knowledge graph & memory snapshots
- Phase 3 (UI & Interaction): Dual-agent chat, audio (TTS/STT), persona integration
- Phase 4 (Container Orchestration): Docker Compose stack, service discovery, health monitoring
- Phase 5 (Planned Next): Deep instrumentation + fusion/retrieval configurability + CI hardening

---
## 4. Dependency & Config Touchpoints
- scripts/index_codebase.py drives structural inventory; triggers memory-save on meaningful diffs (planned)
- answer_meta.timings schema placeholder already consumed by UI (needs backend implementation)
- RAG_RETRIEVAL_MODE env will gate retrieval pipeline selection; default pgvector until alt path ready
- Fusion weights future source-of-truth: in-memory + optional persisted JSON snapshot

---
## 5. Update Procedure
1. Implement change
2. Run: `python scripts/index_codebase.py` (ensure archive excluded)
3. If diff shows added/removed/changed > threshold (TBD), execute: `node scripts/memory-save.mjs` (or make target)
4. Append succinct entry to Section 2 with date & bullets (avoid prose) – keep most recent at top by date groups
5. If new task emerges, add to Active Backlog with [P] and remove once [D] then migrate to Section 2

---
## 6. Risk / Watch List
- Lack of stage timing obscures optimization targets (mitigation: prioritize instrumentation next)
- Manual memory snapshot risk of drift (mitigation: automate post-merge hook)
- Fusion weights opaque until endpoint exists (mitigation: environment documentation + early endpoint)  
- No rate limiting exposes abuse vector (mitigation: introduce token bucket soon after instrumentation)
- Ollama health check intermittent (mitigation: model loading complete, functional verification passed)

---
## 7. Current Environment State (2025-08-28)

### Infrastructure Status
- **Docker Stack**: Fully operational 4-service architecture
	- Backend (FastAPI): localhost:8000 - HEALTHY
	- Ollama (LLM): localhost:11435 - RUNNING with mistral:7b (4.4GB) and gemma:2b models
	- Redis (Cache): localhost:6379 - RUNNING  
	- WebUI: localhost:3000 - HEALTHY
- **Service Discovery**: Backend ↔ Ollama communication validated
- **Health Endpoints**: /health responding {"status":"ok"}
- **LLM Functionality**: Ollama backend operational, 3+ second latency for Mistral 7B
- **Security**: Outbound blocking policy functional (edge blocked as expected)
- **Voice Integration**: Leonardo TTS/Whisper framework ready for deployment

### Available Endpoints
- Main API: http://localhost:8000
- Health Check: http://localhost:8000/health  
- LLM Probe: http://localhost:8000/llm/probe
- Ollama Direct: http://localhost:11435
- Chat UI: http://localhost:3000

### Automation
- Makefile targets: `make compose-up`, `make compose-restart`
- Docker Compose with proper dependencies and health checks
- Automated port conflict resolution and cleanup workflows
- Container orchestration with service networking validation

### Documentation
- README.md: Docker Compose usage and troubleshooting
- Port mapping documentation (ollama conflict resolution)
- Service dependency and networking guides

---
## 8. Fast Status Summary (Today)
Focus: Memory ↔ RAG ingestion reliability (offset + retries) achieved & tested. Next: Instrumentation (stage timings export), fusion configurability, CI pipeline. Blockers: None; prepare for controlled service reboot incorporating new offset persistence.

---
## 9. Glossary (Ops-Focused Additions)
- Memory MCP: Externalized knowledge graph + snapshots enabling context recall & diff-aware enrichment
- Snapshot Run: Timestamped capture of entities/relations for reproducibility & drift analysis
- Stage Timing: Micro-latency metrics per pipeline phase enabling targeted optimization
- Docker Stack: Containerized 4-service architecture (backend, ollama, redis, webui) with orchestration
- Service Discovery: Container-to-container networking via internal DNS (redis, ollama service names)
- Health Verification: Automated endpoint testing and service readiness validation

---
---
## 10. Reboot Preparation Checklist (Ephemeral – remove after completion)
Goal: Safe platform reboot ensuring state continuity & rapid health validation.

Pre-Reboot (T-30m):
- [ ] Capture current memory bridge sidecar offset value
- [ ] Run `make smoke` (once implemented) or manual smoke: /health, /rag/query test, /metrics/basic
- [ ] Persist knowledge graph + model registry snapshot (memory-save) if diff since last snapshot
- [ ] Verify no in-flight fine-tuning or replay tasks (queue empty)
- [ ] Confirm Redis hit rate stable (> threshold) – optional note

Shutdown Sequence:
- [ ] Disable ingestion loop (send SIGINT or stop process) – confirm sidecar final flush
- [ ] Stop Docker services (compose-down) or orchestrator equivalent
- [ ] Archive logs (rotate if > size threshold)

Startup Sequence:
- [ ] Start core services (DB/Redis/Ollama/backend) – verify health checks
- [ ] Launch memory_rag_bridge (observe: “Resuming from offset <prev>” in logs)
- [ ] Run semantic canary queries (predefined N queries) – compare latency & top doc hash set vs. stored baseline
- [ ] Check `/metrics/json` for non-zero ingestion lag & retry counters
- [ ] Validate fusion weights endpoint still returns expected active weights

Post-Reboot Verification (T+15m):
- [ ] Confirm no unexpected retry spikes in logs
- [ ] Snapshot new system metrics baseline (persist to doc or dashboard)
- [ ] Update this checklist status & remove once stable

Rollback (If Needed):
- [ ] Revert to prior container image tag
- [ ] Restore previous fusion weights snapshot
- [ ] Re-run canary queries to confirm recovery

Remove this section after successful reboot & incorporation into standard runbook.

---
Evolves with each significant operational change. Keep terse, actionable, and chronologically truthful.
