<!-- Moved from repository root on 2025-08-30; canonical docs index now lives under docs/ -->

# Documentation Index

Central index of major documentation directories and guides.

## Core Guides

- `README.md` (root) – Canonical setup & architecture overview.
- `docs/sop/AI_TERMINAL_SOP.md` – AI terminal operating procedures.
- `docs/devops/DEVOPS.md` – DevOps & operational practices.
- `docs/devops/DEVOPS_TODO_HISTORY.md` – Historical DevOps backlog & completion log.
- `docs/testing/AGENT_TEST_EXECUTION.md` – Agent-oriented test execution instructions.
- `docs/deployment/PRODUCTION_DEPLOYMENT.md` – Deployment & Kong gateway guide.
- `docs/security/RLS_POLICY_REFERENCE.md` – Row-Level Security policy design.
- `docs/workspace/REMOTE_WORKSPACE_LAYOUT.md` – Recommended remote workspace layout.
- `docs/integration/MCP_RAG_INTEGRATION.md` – Memory MCP ↔ RAG ingestion bridge.
- `COPILOT.md` – AI terminal co-pilot SOP.

## Documentation Directories

| Directory                     | Purpose                                                                             |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| `docs/`                       | Core architecture, memory integration, system and task checklists.                  |
| `documentation/architecture/` | Deep architectural narratives (retrieval, fine-tuning integration).                 |
| `documentation/fine_tuning/`  | Fine-tuning strategy & implementation specifics.                                    |
| `documentation/research/`     | Research notes & exploratory findings.                                              |
| `documentation/tutorials/`    | Example-driven guides and educational excellence examples.                          |
| `sql/`                        | Database schema, RLS policies, migrations.                                          |
| `scripts/`                    | Operational utilities, indexing, memory snapshots, setup automation.                |
| `frontend/`                   | React/Vite dashboard source.                                                        |
| `app/`                        | FastAPI service, RAG pipeline, audio, metrics, health, central control scaffolding. |
| `infrastructure/`             | Deployment configs, infra orchestration, environment scripts.                       |
| `knowledge-graph/`            | Knowledge graph artifacts, entities, relations, snapshots.                          |
| `archive/`                    | Deprecated or experimental historical code/assets (excluded from active planning).  |

## Conventions

- New docs: add to appropriate directory and append a bullet/link here.
- Deprecated docs: move to `archive/` and note replacement.
- Root kept lean: only `README.md` remains (other docs now under `docs/`).

Last updated: 2025-08-30
