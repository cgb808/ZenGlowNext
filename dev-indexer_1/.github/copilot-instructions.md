## AI Agent Operating Guide (Scaffold)

Keep only verifiable, present-day facts. Mark unknowns; don't guess.

### 1. Snapshot (Loaded Now)

Dirs: `app/`, `api/` (empty), `nginx/`, `scripts/` (stubs), `dashboard/` (empty),
`ai-agents/` (empty); infra: `docker-compose.yml`, `Dockerfile`, `.devcontainer/`,
`start.sh` (XRDP launcher). API endpoints: `/health`, `/vector/ping` (Chroma reachability),
`/index` (count). Chroma HTTP client init on startup (non-fatal failure tolerated).
Tests: `tests/test_health.py` (health + vector ping). Formatting: Black + Ruff (on save).
Type checking: mypy strict. Lint: Ruff. No multi-root; this repo is now the single source.
Go bins present (optional): notifier (`tools/notifier`), ingestion gRPC scaffold (`cmd/ingester`), canonical TopK service (`internal/canonical` + client), grpc-router (`grpc-router/`).

### 2. Conventions

- Keep endpoints simple dict responses until complexity warrants Pydantic.
- Add env vars only when used; mirror in `.env.example`.
- Centralize constants before first reuse.
- Avoid speculative scaffolding beyond minimal stubs already present.

### 3. Tooling & Tasks

- `pyproject.toml`: mypy strict, Ruff config.
- `settings.json`: YAML validation and formatting are disabled to avoid noisy false positives. Schema Store remains disabled. If re-enabled later, prefer explicit Compose schema mapping and associating `deploy/docker-stack.yml` as `dockercompose`. Vendored CI folders and node_modules are excluded in files/search.
  - Update: Added watcher/search excludes for heavy dirs (`whisper.cpp/`, `pgdata/`, `volumes/`, `logs/`, caches) to reduce file watchers and improve editor responsiveness.
- Run (before commit): tests -> ruff -> mypy.

### 4. Current Tech Debt

| Area                           | Status                            | Next Action                                |
| ------------------------------ | --------------------------------- | ------------------------------------------ |
| `Dockerfile`                   | Dev (XRDP + uvicorn via start.sh) | Add slim prod image later                  |
| `api/` dir                     | Empty                             | Use when versioning routes                 |
| Scripts stubs                  | Empty                             | Implement when ingestion path decided      |
| Postgres usage                 | Unused                            | Add persistence layer when needed          |
| Dashboard                      | Empty                             | Initialize when UI requirements defined    |
| XRDP hardening                 | Basic                             | Tighten & doc before external exposure     |
| Curated subset drift           | Possible                          | Periodic `multi_repo_sync.sh plan` reviews |
| Remote CUDA script duplication | Full + simple variants            | Consolidate if maintenance cost rises      |

### 5. Interaction Protocol

1. Provide actionable next step (edit or single command). Do not self-run
   commands.
2. Wait for user-run output before next command.
3. Group related edits; keep diffs minimal.
4. No speculative deps/services.
5. Update this file minimally alongside code facts.
6. Prefer citing `docs/MULTI_ROOT_WORKSPACE.md` instead of re-explaining
   multi-root or remote GPU flows in long form.

### 6. Planned / Not Implemented

- Embedding generation path (local vs external) – undecided.
- Batch scripts logic for ingestion.
- Postgres data access layer.
- Dashboard React/Vite implementation.
- XRDP security hardening docs (password rotation, restricting port).
- Observability baseline (metrics/traces unification).
- Dual-DB consolidation tasks (ensure clear separation non-PII vs PII) pending.
- AoS predictive match outcome modeling pipeline (current script `scripts/aos_predict.py` is exploratory only; future: persistence, coefficients exposure, calibration, matchup interaction features).

### 7. Open Questions

- Embedding strategy?
- Auth / API keys?
- Observability (logging / metrics)?
- Remote artifact storage strategy (model checkpoints lifecycle)?
- How to standardize embedding pipeline invocation across local & remote?

### 8. Multi-Root & Remote CUDA Quick Facts

- Primary (this repo) = source of truth; heavy training runs remote.
- Curated repo excludes large / transient artifacts (datasets, model weights).
- Add new share-worthy doc: update `[includes]` in `repo_sync_manifest.txt` then
  run `multi_repo_sync.sh plan` → `push`.
- Remote aliases (`cudapy`, `cudatrain`, `cudamonitor`) require
  `source cuda_aliases.sh`.
- Prefer `zpush` (quick alias) before remote execution to keep code in sync.

### 9. Assistant Guardrails

- Do NOT introduce new root files outside allowlist (see `settings.json`)
  without explicit justification.
- For ambiguous GPU vs CPU placement: default CPU locally unless workload
  clearly requires GPU.
- If requested to add large binary asset: recommend documenting retrieval
  instead.

Update answers only when evidence appears.
