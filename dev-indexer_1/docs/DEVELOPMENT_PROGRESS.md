# Development Progress

## Overview

This document tracks implemented features and pending work for the ZenGlow Indexer / RAG API workspace.

## Current Architecture Update (Aug 2025)

- **Multi-GPU Setup**: RTX 3060 Ti (8GB) + GTX 1660 Super (6GB)
- **AI Personalities**:
  - RTX 3060 Ti: Leonardo (Mistral 7B Q5_K_M) - The analytical thinker
  - GTX 1660 Super: Jarvis (Phi3 quantized) - The conversational assistant
- **Workload Specialization**: Separated deep reasoning from real-time interaction

## Completed

- Project scaffolding and initial FastAPI application (`app/main.py`).
- Health endpoints via `health_router`.
- Legacy `/rag/query` endpoint (embedding + retrieval + edge LLM call).
- RAG core modules: `pipeline.py`, `db_client.py`, `embedder.py`, `llm_client.py`.
- Dependency Injection factory for `RAGPipeline` using FastAPI `Depends`.
- New `/rag/pipeline` endpoint with Pydantic request/response schemas.
- Real embedding integration over HTTP (`Embedder.embed_batch`).
- Real LLM integration: Supabase Edge Function first, Ollama fallback.
- Graceful DB connection handling (context manager + `close`).
- Redis build update publisher with logging and password support.
- Secure Postgres access guide (`docs/REMOTE_DB_ACCESS.md`).
- Linting/formatting setup: Ruff, Black, isort, Flake8, pre-commit (`requirements-dev.txt`, `.pre-commit-config.yaml`).
- Unit test for RAG pipeline logic (`tests/test_rag_pipeline.py`).
- API tests expanded to cover `/rag/pipeline` including validation error path.
- Added runtime dependencies (`requirements.txt`).
- Multi-GPU Ollama setup with specialized model deployment.

## In Progress / Next

- Update backend routing to utilize Leonardo and Jarvis personality endpoints.
- Configure Jarvis (Phi3) TTS integration on secondary GPU.
- Provide retrieval scores in `/rag/pipeline` response (extend `DBClient.vector_search`).
- Replace legacy `/rag/query` or refactor to reuse `RAGPipeline`.
- Add structured logging and request tracing middleware.
- Add metrics/observability (Prometheus / OpenTelemetry) instrumentation.
- Streaming responses for LLM generation.
- Enhanced error handling & custom exception handlers.
- Authentication / API key guard for RAG endpoints.
- Caching layer for repeated queries (Redis integration for RAG results).
- Add ingestion/refresh triggers reacting to Redis Pub/Sub messages.
- More comprehensive test coverage (edge cases, failure simulations, timeout handling).
- CI workflow integration for lint + tests.

## Technical Notes

- `RAGPipeline` uses protocol-based abstractions for embedder, vector search client, and LLM allowing easy substitution.
- Embedding and LLM calls are synchronous; consider async adaptation with httpx.
- Type checker unknown warnings will clear when dependencies are installed in the environment.
- Fallback zero-vector embedding only when `ALLOW_EMBED_FALLBACK=true`.
- Supabase Edge Function configurable via `SUPABASE_EDGE_FUNCTION` env var.

## Environment Variables (Current Usage)

- EMBED_ENDPOINT
- EMBED_FALLBACK_DIM
- ALLOW_EMBED_FALLBACK
- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_EDGE_FUNCTION
- OLLAMA_URL
- OLLAMA_MODEL
- PG_DB / PG_USER / PG_PASSWORD / PG_HOST / PG_PORT
- DATABASE_URL (legacy retrieval path)
- REDIS_HOST / REDIS_PORT / REDIS_PASSWORD / REDIS_BUILD_CHANNEL

## Suggested Ordering of Upcoming Work

1. Extend `DBClient` to return similarity scores & metadata.
2. Refactor `/rag/query` to wrap `RAGPipeline` or deprecate.
3. Add caching + error handling middleware.
4. Implement streaming generation (Server-Sent Events or websockets).
5. Instrument metrics.
6. Add auth.
7. Flesh out ingestion + Pub/Sub consumer.
8. Expand tests & CI workflow.

## Changelog Snippet (Recent)

- Added `/rag/pipeline` endpoint with typed schemas.
- Integrated real HTTP embedding and LLM fallback logic.
- Added progress documentation file (this document).

---

(Keep this file updated as new features land.)
