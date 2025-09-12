-- metrics_writer_role.sql
-- Purpose: Dedicated role with INSERT privilege only on runtime_metrics table
-- for external collectors (no read necessary unless debugging).

\set metrics_table runtime_metrics
\set metrics_role  metrics_writer
\set metrics_password 'REPLACE_WITH_STRONG_PASSWORD'

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'metrics_role') THEN
    EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L NOINHERIT', :'metrics_role', :'metrics_password');
  END IF;
END $$;

GRANT USAGE ON SCHEMA public TO :metrics_role;
GRANT INSERT ON TABLE :metrics_table TO :metrics_role;

-- Optional: allow reads for debugging
-- GRANT SELECT ON TABLE :metrics_table TO :metrics_role;

-- Connection string example:
--  postgresql://metrics_writer:REPLACE_WITH_STRONG_PASSWORD@host:5432/postgres
