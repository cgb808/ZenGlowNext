# PII Architecture: Vault vs Tokenized References

Goal: Keep raw PII isolated while enabling rich analytics on time-series data. Two options:

## Option A — Separate Timescale PII Vault
- Two TimescaleDB instances: one public (events), one PII vault.
- Pros: uniform time-series features and compression for PII timelines; single engine for all time-based joins.
- Cons: operational overhead, higher risk of cross-contamination, duplication of TS extensions/licenses.
- Use when: you need high-write time-series of PII itself (e.g., vital streams, PHI timelines), or retention transforms that benefit from Timescale compression/chunking.

## Option B — Single PII Postgres + Token Map (Recommended Default)
- Keep PII in a standard Postgres (e.g., Supabase vault DB). Store only pseudonymous tokens in Timescale events.
- Map `token -> identity_id` via `pii_token_map` with rotation + validity window.
- Pros: simpler isolation boundary, less surface area, easy RLS and masking; Timescale only handles pseudonymous metrics.
- Cons: joins requiring PII context require FDW or app-layer joins.
- Use when: PII is relatively static (names, contact info) and events refer via tokens.

## Data Flow
1. Voice recognition (or auth provider) asserts identity → get/create `pii_identity_profiles.id` (UUID).
2. Mint pseudonymous token with `mint_user_token(id, purpose, ttl_days)`.
3. App ingests event to Timescale `events` with `user_token` only.
4. PII stored/updated in Postgres vault (`pii_identity_profiles`).
5. When needed, Supabase (or Edge Functions) join via FDW to `events_remote` filtered by `user_token`, then map to identity via `pii_token_map`.

## Embeddings & PII
- Never embed raw PII. Redact or tokenize before embedding.
- If user-personalization embeddings are required, store in PII DB (`user_embeddings`), not in Timescale.
- For search over PII, create masked views and embed only masked text.

## RLS & Retention
- Enable RLS on PII tables; use policies tied to service roles.
- Schedule token rotation and set `valid_until`; keep audit in `pii_access_log`.
- Redact `events.data_payload_raw` after N days (see `redact_raw_payload_older_than`).

## Decision Tree
- Do you stream high-frequency PII (PHI, vitals)? If yes → Option A.
- Otherwise (mostly identity/contact + occasional references) → Option B.

## Implementation Notes
- FDW lives on Supabase; never expose PII via FDW to external consumers.
- Keep all joins to PII on Supabase side using `events_remote` and `pii_token_map`.
 - Use `rotate_user_token(token, ttl_days)` to expire tokens and re-issue without exposing identity UUIDs.
