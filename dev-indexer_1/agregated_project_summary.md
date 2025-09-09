# Aggregated Project Summary

This document gives a concise, factual overview of the ZenGlow Indexer workspace as it exists in this repo. It focuses on what’s present now and how to run it locally.

---

## 1) Core concept

- Purpose: Local-first RAG backend with optional audio/voice helpers. Provides a FastAPI app, a Postgres (pgvector) store, and optional sidecars (Ollama “Leonardo” and Whisper.cpp) for LLM and speech.
- Highlights:
	- FastAPI app with health and metrics routers; tolerant to missing optional deps (stubs in place).
	- Postgres core plus a separate PII database; SQL schemas mounted at init (artifact/rag/indexes/pii, and a dev knowledge-graph schema).
	- Optional Ollama (Mistral) and Whisper.cpp services controlled via Docker Compose profiles.
	- Remote CUDA/inference supported by helper scripts (see docs); app tolerates remote or local-only runs.

---

## 2) Architecture layers

- API layer: FastAPI app in `app/main.py` exposes core routes (e.g., `/health`), metrics, diagnostics, and feature routers that gracefully degrade if modules are missing.
- Service/specialist layer: Feature routers under `app/*` (leonardo audio, discovery, feedback, metrics, RAG embed/probe) are imported conditionally; stubs keep startup resilient.
- RAG/knowledge layer: Postgres with pgvector and Timescale-friendly schemas. Initialization SQL mounted via Compose in `docker-entrypoint-initdb.d`.
- Infrastructure: Docker Compose orchestrates `db`, `db_pii`, `app`, and optional profiles `leonardo` (Ollama) and `whisper` (whisper.cpp HTTP server). Swarm baseline in `deploy/docker-stack.yml` and `docs/SWARM_DEPLOY.md`.

---

## 3) Components & technologies

- `app/main.py`: FastAPI entrypoint with CORS, static files, and routers (many optional). Health stub guarantees `/health` works when features are absent.
- `docker-compose.yml`: Orchestrates services:
	- db (pg + pgvector), db_pii (separate Postgres for PII)
	- app (FastAPI dev container)
	- profiles: `leonardo` (Ollama), `whisper` (whisper.cpp server)
- `compose/embedding-worker.yml`: Separate embedding worker compose (run via `-f compose/embedding-worker.yml`).
- `sql/*.sql`: Core RAG schema, indexes, PII schema, dev knowledge-graph schema; loaded in numeric order on DB init.
- `scripts/`: Dev helpers (env merge/load; schema drift check; prestart).
- `docs/`: Swarm deployment baseline and assorted notes.
- `dashboard/`: Vite React stub present (minimal wiring currently).

---

## 4) Operational notes

- Quick start (local compose):
	1. Copy `.env.example` to `.env` and adjust as needed (e.g., `POSTGRES_PASSWORD`, `API_EXTERNAL_URL`, `JWT_SECRET`).
	2. Start core stack:
		 - `docker compose up -d db db_pii`
		 - `docker compose up app`
	3. App listens on host `http://localhost:8001` (container 8000 mapped to host 8001).

- Optional services:
	- Ollama (Mistral): `docker compose --profile leonardo up -d leonardo`
	- Whisper server: `docker compose --profile whisper up -d whisper`

- Config notes:
	- App reads from `.env` without overwriting existing env; DSNs default to internal service hosts.
	- Notable vars: `DATABASE_URL`, `PII_DATABASE_URL`, `API_EXTERNAL_URL`, `JWT_SECRET`, `LEONARDO_URL`, `LEONARDO_MODEL`, `WHISPER_SERVER_URL`, `OLLAMA_MODEL`.
	- Audio paths can be skipped in tests via `SKIP_AUDIO_TESTS=1`; optional audio imports guarded in app.

- Remote inference:
	- Helper scripts and docs support running on a remote CUDA box; the app can run CPU-only locally while targeting remote services.

---

Notes
- Vendor CI workflows are excluded in editor settings to avoid noise; enabling GitHub Actions locally is optional and not required to run the stack.
- Before production, harden secrets handling and ingress; see `docs/SWARM_DEPLOY.md` for a baseline Swarm deployment.

---

## Try it

1) Prepare env

```bash
cp -n .env.example .env || true
# Edit .env as needed (POSTGRES_PASSWORD, API_EXTERNAL_URL, JWT_SECRET)
```

2) Start core services

```bash
docker compose up -d db db_pii
docker compose up app
```

3) Health check

```bash
curl -sf http://localhost:8001/health | jq .
```

Optional: start sidecars and probe

```bash
# Ollama (Leonardo profile)
docker compose --profile leonardo up -d leonardo
curl -sf http://localhost:11434/api/tags | jq .

# Whisper server (CPU)
docker compose --profile whisper up -d whisper
curl -sf http://localhost:9000 || echo "whisper listening"
```

Troubleshooting

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f db
```
