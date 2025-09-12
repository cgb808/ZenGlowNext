# PII Architecture (Dual DB Model)

Goal: Isolate raw PII while enabling analytics on tokenized events. We standardize on two Postgres DBs:

1. Core DB (non-PII): events, metrics (partitioned + BRIN), embeddings (Chroma/pgvector), knowledge graph.
2. PII Vault DB: identity profiles, token map, optional user-personal embeddings, access/audit log.

Events store only `user_token` references; vault resolves token → identity via `pii_token_map` with rotation windows.

## Data Flow
1. Voice recognition (or auth provider) asserts identity → get/create `pii_identity_profiles.id` (UUID).
2. Mint pseudonymous token with `mint_user_token(id, purpose, ttl_days)`.
3. App ingests event to Postgres `events` (partitioned) with `user_token` only.
4. PII stored/updated in Postgres vault (`pii_identity_profiles`).
5. When needed, Supabase (or Edge Functions) join via FDW to `events_remote` filtered by `user_token`, then map to identity via `pii_token_map`.

## Embeddings & PII
- Never embed raw PII. Redact or tokenize before embedding.
- If user-personalization embeddings are required, store in PII DB (`user_embeddings`), not in the public vector store.
- For search over PII, create masked views and embed only masked text.

## RLS & Retention
- Enable RLS on PII tables; use policies tied to service roles.
- Schedule token rotation and set `valid_until`; keep audit in `pii_access_log`.
- Redact `events.data_payload_raw` after N days (see `redact_raw_payload_older_than`).

## Rationale
- Keeps application code simple (clear DSN split).
- Allows aggressive partition pruning + BRIN in core DB without RLS overhead on every table.
- Vault enforces RLS, masking, and token lifecycle separately.

## Implementation Notes
- Optional FDW from core → vault (read-only) kept narrow if needed for reporting.
- Never embed raw PII; store personalization embeddings only in vault (`user_embeddings`).
- Use `rotate_user_token(token, ttl_days)` to re-issue without leaking identity UUIDs.
