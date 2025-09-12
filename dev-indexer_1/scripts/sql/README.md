# Database Split Plan and Schemas

This folder contains initial SQL schemas for a three-database split:

- Cloud (Supabase): `supabase/schema.sql` — non-PII general data (RAG index, sanitized telemetry)
- Local PII: `local_pii/schema.sql` — user-facing sensitive entities (people, relationships, health, conversations)
- Local Specialist: `local_specialist/schema.sql` — detailed agent/inference logs and raw swarm telemetry

Notes
- Dimensions for vectors default to 384 to match current embedder. Adjust if your embedder uses a different size.
- Supabase policies assume UUID-based auth. If your app does not use Supabase Auth, keep RLS enabled but grant a service role for backfill/maintenance.
- All schemas are idempotent where practical. Apply via psql or Supabase SQL editor.

---

## Data Domain → Database Mapping

- PII/local-hardened (Local PII DB)
  - family_people, family_relationships, family_artifacts, family_health_metrics
  - conversation_events (content, embeddings, status flags)
  - transcription jobs and audio-related job metadata
- Specialist/Agent (Local Specialist DB)
  - model_inference_events (per-inference metrics)
  - model_inference_token_stats (token-level stats)
  - swarm_events (full detail, includes query_text and optional event_embedding)
- General Cloud (Supabase)
  - doc_embeddings (RAG index for public/general docs, optional user_id for RLS)
  - match_documents RPC for vector similarity
  - swarm_events_sanitized (no raw query_text)
  - Optional model_inference_events_sanitized (without raw prompts/completions) if needed later

---

## Environment variables

- SUPABASE_URL, SUPABASE_KEY (or SERVICE_ROLE/ANON): required for RPC calls
- SUPABASE_SIM_SEARCH_RPC: RPC function name (default: match_documents)
- SUPABASE_SIM_RPC_*: override payload/field names if your RPC differs

---

## Apply

- Cloud: Paste `supabase/schema.sql` into Supabase SQL editor (or use `psql`).
- Local: `psql "$PII_DATABASE_URL" -f scripts/sql/local_pii/schema.sql`
- Specialist: `psql "$SPECIALIST_DATABASE_URL" -f scripts/sql/local_specialist/schema.sql`

Adjust DSNs according to your environment.
