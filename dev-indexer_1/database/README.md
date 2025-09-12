# Multi-Database Schema (Cloud + Local)

This folder contains SQL definitions for a 3-database split:

- Supabase Cloud (general, non-PII, RAG-focused)
- Local PII (sensitive personal/medical and session text)
- Local Specialist (domain-specific knowledge stores, e.g., code graph, research fetches)

Each schema file is idempotent and can be applied repeatedly. Namespaces use the public schema by default. Adjust search_path as desired.

## Domain → Database Mapping

Cloud (Supabase):
- RAG core: `doc_embeddings` (768-dim by default) and advanced `chunks` with optional dense/small embeddings
- Interaction analytics: `interaction_events`, `query_performance`, `query_cache`
- Simple events table (no PII): `events` (optional; consider hashing user tokens)
- RPC for similarity search: `match_documents`

Local PII (hardened):
- Family context: `family_people`, `family_artifacts`, `family_health_metrics`
- Conversation/session: `sessions`, `voice_fragments`, `intent_events`
- Any fields containing names, free-form text that may include PII, medical metrics

Local Specialist:
- Development Knowledge Graph: `source_documents`, `code_chunks`, `development_log`
- Medical research fetches: `pubmed_fetches`
- Memory ingestion dedup: `memory_ingest_dedup`

## Vector Dimensions

- Default cloud schema uses `vector(768)`. If your embedder outputs 384-dim vectors, change the column to `vector(384)` and update related indexes and RPC accordingly.

## Applying (Supabase)

- Ensure `pgvector` extension is enabled (included in 00_extensions.sql)
- Apply `supabase_cloud/*.sql` in numeric order
- Optional: Create HNSW indexes if supported by your pgvector version

## Environment Variables (reference)

- DATABASE_URL: local/general
- PII_DATABASE_URL: local hardened
- SPECIALIST_DATABASE_URL: local specialist
- SUPABASE_DB_URL: cloud Postgres (managed by Supabase)
- SUPABASE_URL/SUPABASE_KEY: for RPC access from the app
# Multi-Database Schema (Cloud + Local)

This folder contains SQL definitions for a 3-database split:

- Supabase Cloud (general, non-PII, RAG-focused)
- Local PII (sensitive personal/medical and session text)
- Local Specialist (domain-specific knowledge stores, e.g., code graph, research fetches)

Each schema file is idempotent and can be applied repeatedly. Namespaces use the public schema by default. Adjust search_path as desired.

## Domain → Database Mapping

Cloud (Supabase):
- RAG core: `doc_embeddings` (768-dim by default) and advanced `chunks` with optional dense/small embeddings
- Interaction analytics: `interaction_events`, `query_performance`, `query_cache`
- Simple events table (no PII): `events` (optional; consider hashing user tokens)
- RPC for similarity search: `match_documents`

Local PII (hardened):
- Family context: `family_people`, `family_artifacts`, `family_health_metrics`
- Conversation/session: `sessions`, `voice_fragments`, `intent_events`
- Any fields containing names, free-form text that may include PII, medical metrics

Local Specialist:
- Development Knowledge Graph: `source_documents`, `code_chunks`, `development_log`
- Medical research fetches: `pubmed_fetches`
- Memory ingestion dedup: `memory_ingest_dedup`

## Vector Dimensions

- Default cloud schema uses `vector(768)`. If your embedder outputs 384-dim vectors, change the column to `vector(384)` and update related indexes and RPC accordingly.

## Applying (Supabase)

- Ensure `pgvector` extension is enabled (included in 00_extensions.sql)
- Apply `supabase_cloud/*.sql` in numeric order
- Optional: Create HNSW indexes if supported by your pgvector version

## Environment Variables (reference)

- DATABASE_URL: local/general
- PII_DATABASE_URL: local hardened
- SPECIALIST_DATABASE_URL: local specialist
- SUPABASE_DB_URL: cloud Postgres (managed by Supabase)
- SUPABASE_URL/SUPABASE_KEY: for RPC access from the app
