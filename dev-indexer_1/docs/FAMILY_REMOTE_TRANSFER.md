# Family Context & Dataset Generator – Remote Transfer Guide

Purpose: Minimal, integrity-verifiable bundle so a remote (curated) repo or host can: (1) apply schema + RLS, (2) seed in‑memory context, (3) generate instruction + conversation datasets.

## Included Components

Domain / API (in‑memory):
- `app/family/context.py` – domain models + seed loader
- `app/family/router.py` – FastAPI endpoints (people, artifacts, buckets, guardrails)
- `app/family/repo.py` – repository protocol placeholders
- `app/family/pg_repo.py` – Postgres persistence implementation (not yet wired to API)
- `app/family/seed_data.json` – canonical seed dataset

Persistence / Security:
- `sql/family_schema.sql` – tables & indexes
- `sql/family_rls.sql` – RLS policies + masked view

Dataset Generation:
- `scripts/export_family_finetune_dataset.py` – instruction (single‑turn) examples
- `scripts/export_family_conversations.py` – multi‑turn chat scenarios
- `scripts/build_family_dataset.py` – unified builder + manifest
- `scripts/package_family_context.py` – creates portable tarball (this guide’s scope)

Tests:
- `tests/test_conversation_generators.py` – ensures each scenario yields samples

Docs:
- `docs/DATASET_EXPORT.md`
- `docs/FAMILY_CONTEXT_DESIGN.md` (architectural reference)
- `docs/FAMILY_REMOTE_TRANSFER.md` (this file)
- `docs/INFERENCE_LOGGING_DESIGN.md` (uncertainty & gating)

## Environment Variables
```
FAMILY_PG_DSN=postgresql://user:pass@host:5432/db
FAMILY_ADMIN_USERS=charles,nancy  # when later wiring runtime auth
ENABLE_GPU_PROBE=0               # keep off in minimal environments
```

## One‑Time Remote Setup
1. Install Python deps (subset): fastapi, uvicorn, psycopg2-binary, pytest.
2. Apply schema: `psql "$FAMILY_PG_DSN" -f sql/family_schema.sql`
3. (Optional now) Apply RLS: `psql "$FAMILY_PG_DSN" -f sql/family_rls.sql`
4. (Future) Grant `family_admin` to admin DB roles.

## Building Datasets Remotely
```
python scripts/build_family_dataset.py --out datasets/family \
  --conversation-weights artifact_retrieval=2,follow_up=1
cat datasets/family/manifest.json
```

## Packaging (Local → Remote)
Create tarball containing only required files + integrity manifest:
```
python scripts/package_family_context.py --out dist
ls dist/*.tar.gz
```
Manifest inside tarball: `family_package_manifest.json` (paths + sha256 + created_ts).

## Verification After Transfer
1. Extract tarball.
2. Run: `python scripts/package_family_context.py --verify family_package_manifest.json` (in extracted root) – exits non‑zero on mismatch.
3. Execute dataset build (see above) and optionally run tests: `pytest -k conversation_generators -q`.

## Minimal API Smoke (In‑Memory)
```
uvicorn app.main:app --reload --port 8001
curl localhost:8001/family/people
```

## Postgres Wiring (Deferred)
Add dependency injection selecting `PgFamilyRepo` when `FAMILY_PG_DSN` is set; set `SET LOCAL app.current_user` per request for RLS. (Not shipped yet—see `DEVOPS_TODO.md`).

## Security Notes
- Sensitive identifiers intentionally excluded (no SSN storage).
- Masking handled in SQL view (`family_people_masked`) once API consumes it.
- Refusal examples present in conversation dataset (scenario: `guardianship_policy`).

## Next Increment (Suggested)
- Add repository DI + request user context.
- Add dataset version bump in `build_family_dataset.py` manifest meta.
- Expand refusal scenarios & evaluation hold‑out split.

---
Generated: keep concise; update only when file list changes.
