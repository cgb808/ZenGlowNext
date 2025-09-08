# Family Context Persistence & Artifacts

This document outlines how the ephemeral in-memory family context will evolve
to a persistent, queryable domain for orchestration, safety guardrails, and
fine-tuning dataset generation.

## Layers
1. Domain Models (`Person`, `Relationship`, `Artifact`)
2. Repository Interfaces (`repo.py`) for dependency inversion.
3. In-Memory Implementation (`context.py`) – bootstrap & fast iteration.
4. Postgres implementation (`pg_repo.py`) providing durability (initial, time-series ready for metrics).
5. Inference Logging & Gating (see `docs/INFERENCE_LOGGING_DESIGN.md`) for uncertainty-driven guardrails.
6. Dependency Injection (planned) – runtime swap between in-memory and Postgres via `FAMILY_PG_DSN`.

## Guardianship
`Relationship.legal = True` marks persistent legal guardianship (e.g. Charles & Nancy -> Willow).

## Buckets vs Artifacts
- Buckets: lightweight append-only categorized lists (health, documents, media).
- Artifacts: normalized records (id, kind, tags, content_ref) suitable for indexing & fine-tune export.

`content_ref` points to external storage or hashed payload (keeping repository free of large binaries).

## Fine-Tune Extraction
Scripts:
- `scripts/export_family_finetune_dataset.py` (instruction → output pairs)
- `scripts/export_family_conversations.py` (multi-turn chat style samples)
 - `scripts/build_family_dataset.py` (unified build + manifest incl. version field)

Current conversation scenarios:
1. artifact_retrieval – user asks for artifact summary.
2. health_metric – user asks for latest health metric.
3. guardianship_policy – refusal + safe alternative.
4. follow_up – multi-turn with coreference.
5. multi_artifact_compare – comparative reasoning.

Add more scenarios by appending a generator in `export_family_conversations.py`.

### Scenario Weights
Use `scripts/export_family_dataset.py --mode conversation --scenario-weights artifact_retrieval=3,follow_up=2` to oversample specific scenarios during dataset generation.

## Next Steps (Planned)
- Wire API to optionally use Postgres repository when `FAMILY_PG_DSN` present.
- Add age-based PII masking in API responses (e.g., omit exact birthdates for non-guardian viewers).
- Introduce tag-based search index (PG GIN / Trigram) for artifacts.
- Media pipeline: upload endpoint -> virus scan -> object storage -> persist `content_ref` + resolution metadata.
- Integrate inference gating (reflect/retrieve/abstain) before returning sensitive answers.
- Dashboard inference ticker & aggregates for live uncertainty telemetry.

## Security / Privacy Considerations
- Birthdates stored only for adults in seed; children computed age only.
- Add access scopes later (guardian, extended_family, public_summary).

## Versioning
Include a dataset manifest (future) enumerating counts & checksum for reproducibility.

## Persistence Quick Start
1. Set env `FAMILY_PG_DSN=postgresql://user:pass@localhost:5432/db`.
2. Install deps (psycopg2-binary now in requirements).
3. Run: `python scripts/family_persist_sync.py --apply` (creates schema + syncs seed).
4. (Future) Enable API wiring to read from DB instead of in-memory.

### Row Level Security (RLS) & Masking
File: `sql/family_rls.sql`
Principles:
- Admins (role `family_admin`) see everything (e.g., users `charles`, `nancy`).
- Non-admin users only see rows where they are the person (`family_people.id`) or are the entity owner (artifacts / health metrics entity_id) or involved in a relationship.
- Session variable `app.current_user` is set per request for RLS evaluation.
- Masked view `family_people_masked` nulls `birthdate` unless admin or self.
- Highly sensitive identifiers (e.g., SSN) are NOT stored at rest.

To apply:
1. Grant roles: `CREATE ROLE family_admin; GRANT family_admin TO charles; GRANT family_admin TO nancy;`
2. Execute schema then RLS: `psql -f sql/family_schema.sql && psql -f sql/family_rls.sql`
3. Ensure application sets `SET LOCAL app.current_user = '<person_id>'` each connection.

At-rest masking approach: omit high-risk fields entirely; for moderate sensitivity (birthdate) provide view-level masking rather than on-the-fly string replacement, ensuring no raw exposure from accidental SELECT * queries.

### Inference Logging (Cross-Cutting)
Inference events (avg_logprob, entropy, decision) stored in `model_inference_events` enable feedback loops: low-confidence family answers trigger retrieval or refusal scenarios. Endpoints: `/inference/ticker`, `/inference/realtime`, `/inference/aggregate`.
