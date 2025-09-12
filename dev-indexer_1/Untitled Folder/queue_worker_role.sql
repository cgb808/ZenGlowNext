-- queue_worker_role.sql
-- Purpose: Create a least-privilege database role for the embedding queue worker
-- that runs on an external (edge) machine. This role only needs:
--   * SELECT + UPDATE (status/error_message) on the ingestion queue table
--   * INSERT (and optional SELECT) on doc_embeddings
--   * INSERT on code_chunk_ingest_log (if logging desired)
--   * USAGE on required schemas & extensions (vector)
-- It should NOT have: ability to alter schema, delete unrelated data, or access other tables.
-- Run this in psql (with a superuser or owner) after queue + tables exist.

-- CONFIG (edit if you changed names)
\set queue_table        code_chunk_ingest_queue
\set log_table          code_chunk_ingest_log
\set embeddings_table   doc_embeddings
\set worker_role        queue_worker
\set worker_password    'REPLACE_WITH_STRONG_PASSWORD'

-- 1. Create role (LOGIN)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'worker_role') THEN
    EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L NOINHERIT', :'worker_role', :'worker_password');
  END IF;
END $$;

-- 2. Ensure vector extension USAGE (Supabase normally pre-installs; safe if exists)
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. Basic schema usage
GRANT USAGE ON SCHEMA public TO :worker_role;

-- 4. Grant on queue table
GRANT SELECT, UPDATE ON TABLE :queue_table TO :worker_role;
-- Limit UPDATE to columns actually needed (optional stricter variant):
-- ALTER TABLE :queue_table FORCE ROW LEVEL SECURITY; (if using RLS)
-- Create a policy to allow update of status/error_message by this role.

-- 5. Grant on embeddings table (insert + read for sanity)
GRANT SELECT, INSERT ON TABLE :embeddings_table TO :worker_role;

-- 6. Grant on log table (only INSERT required)
GRANT INSERT ON TABLE :log_table TO :worker_role;

-- 7. (Optional) Future: If you add RLS, define policies similar to:
-- CREATE POLICY p_queue_select ON :queue_table FOR SELECT TO :worker_role USING (true);
-- CREATE POLICY p_queue_update ON :queue_table FOR UPDATE TO :worker_role USING (true) WITH CHECK (true);
-- CREATE POLICY p_embeddings_insert ON :embeddings_table FOR INSERT TO :worker_role WITH CHECK (true);

-- 8. Revoke broader defaults just in case (idempotent)
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM :worker_role;
-- Re-apply granular grants (order matters)
GRANT SELECT, UPDATE ON TABLE :queue_table TO :worker_role;
GRANT SELECT, INSERT ON TABLE :embeddings_table TO :worker_role;
GRANT INSERT ON TABLE :log_table TO :worker_role;

-- 9. Privilege inspection helper (run manually):
-- \dp :queue_table
-- \dp :embeddings_table
-- \dp :log_table

-- 10. Connection string sample (replace password placeholder):
--   postgresql://queue_worker:REPLACE_WITH_STRONG_PASSWORD@HOST:5432/postgres

-- SECURITY NOTES:
-- * Rotate the password periodically; consider SCRAM auth (default in modern Postgres).
-- * Restrict network ingress (VPC / firewall) to the edge machine IP(s).
-- * Consider a connection pooler (pgbouncer) if running multiple workers.
