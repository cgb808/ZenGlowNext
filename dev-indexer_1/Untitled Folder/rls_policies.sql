-- Row-Level Security (RLS) foundational policies (idempotent).
-- This file can be applied directly to Postgres (local container) BEFORE any Supabase setup.
-- Strategy:
--  1. Add a tenant discriminator column (tenant_id TEXT) if not present.
--  2. Enable RLS on core tables.
--  3. Provide safe baseline policies per role tier (rag_read / rag_write / rag_admin) with OPTIONAL tenant scoping.
--  4. Expose helper function to set a per-session tenant context (pg variable) for multi-tenant isolation.
--  5. Policies are deliberately permissive until a tenant_id is set; tighten by setting REQUIRE_TENANT=on.

-- =====================================================================
-- 0. Helper: create an extension for pgcrypto if future row hashing needed
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================================
-- 1. Add tenant_id column (NULL by default) for each table requiring isolation
-- =====================================================================
ALTER TABLE IF EXISTS doc_embeddings      ADD COLUMN IF NOT EXISTS tenant_id TEXT;
ALTER TABLE IF EXISTS device_metrics      ADD COLUMN IF NOT EXISTS tenant_id TEXT;
ALTER TABLE IF EXISTS memory_ingest_dedup ADD COLUMN IF NOT EXISTS tenant_id TEXT; -- optional (auditing)

-- =====================================================================
-- 2. Session GUC + helper to set current tenant
-- =====================================================================
-- We use a custom GUC (Grand Unified Config) key: app.current_tenant
-- Example usage in session:
--   SELECT set_config('app.current_tenant','tenant_a', false);
-- Retrieve inside policy via current_setting('app.current_tenant', true).

CREATE OR REPLACE FUNCTION app_set_tenant(tid TEXT)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  PERFORM set_config('app.current_tenant', coalesce(tid,''), false);
END;$$;

-- =====================================================================
-- 3. RLS Enablement
-- =====================================================================
ALTER TABLE IF EXISTS doc_embeddings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS device_metrics      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS memory_ingest_dedup ENABLE ROW LEVEL SECURITY;

-- (Optional) Force RLS even for table owners (harder lockdown)
-- ALTER TABLE doc_embeddings FORCE ROW LEVEL SECURITY;

-- =====================================================================
-- 4. Policy Patterns
-- =====================================================================
-- We define a parameter to toggle strict tenant enforcement. If set, rows must match tenant_id.
-- If tenant_id is NULL (legacy rows), admin can still access for migration.
-- To enforce, run: SELECT set_config('app.require_tenant','on', false);

CREATE OR REPLACE FUNCTION app_require_tenant() RETURNS boolean LANGUAGE sql AS $$
  SELECT current_setting('app.require_tenant', true) = 'on';
$$;

CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS TEXT LANGUAGE sql AS $$
  SELECT NULLIF(current_setting('app.current_tenant', true),'');
$$;

-- Core predicate helper (TRUE when not enforcing OR tenant matches OR row has NULL and user is admin)
CREATE OR REPLACE FUNCTION app_row_visible(row_tenant TEXT) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE
  ct TEXT := app_current_tenant();
  enforcing BOOLEAN := app_require_tenant();
  is_admin BOOLEAN := (SELECT current_user IN ('rag_admin')); -- Adjust if more admin roles added
BEGIN
  IF NOT enforcing THEN
    RETURN TRUE; -- open mode
  END IF;
  IF ct IS NULL THEN
    RETURN is_admin; -- no tenant set: only admin can see when enforcing
  END IF;
  IF row_tenant IS NULL THEN
    RETURN is_admin; -- untagged legacy row visible only to admin during enforcement
  END IF;
  RETURN row_tenant = ct;
END;$$;

-- ===================== doc_embeddings =====================
DROP POLICY IF EXISTS p_doc_embeddings_select ON doc_embeddings;
CREATE POLICY p_doc_embeddings_select ON doc_embeddings
  FOR SELECT
  USING (app_row_visible(tenant_id));

DROP POLICY IF EXISTS p_doc_embeddings_insert ON doc_embeddings;
CREATE POLICY p_doc_embeddings_insert ON doc_embeddings
  FOR INSERT
  WITH CHECK (
    -- allow writes for write/admin roles; enforce tenant match if required
    (current_user IN ('rag_write','rag_admin'))
    AND (
      NOT app_require_tenant() OR
      (tenant_id = app_current_tenant())
    )
  );

DROP POLICY IF EXISTS p_doc_embeddings_update ON doc_embeddings;
CREATE POLICY p_doc_embeddings_update ON doc_embeddings
  FOR UPDATE
  USING (app_row_visible(tenant_id))
  WITH CHECK (
    (current_user IN ('rag_write','rag_admin')) AND
    (
      NOT app_require_tenant() OR
      (tenant_id = app_current_tenant())
    )
  );

DROP POLICY IF EXISTS p_doc_embeddings_delete ON doc_embeddings;
CREATE POLICY p_doc_embeddings_delete ON doc_embeddings
  FOR DELETE
  USING (
    (current_user = 'rag_admin') AND app_row_visible(tenant_id)
  );

-- ===================== device_metrics =====================
DROP POLICY IF EXISTS p_device_metrics_select ON device_metrics;
CREATE POLICY p_device_metrics_select ON device_metrics
  FOR SELECT USING (app_row_visible(tenant_id));

DROP POLICY IF EXISTS p_device_metrics_write ON device_metrics;
CREATE POLICY p_device_metrics_write ON device_metrics
  FOR INSERT WITH CHECK (
    (current_user IN ('rag_write','rag_admin')) AND
    (NOT app_require_tenant() OR tenant_id = app_current_tenant())
  );

-- ===================== memory_ingest_dedup =====================
-- Typically internal: read needed for duplication checks, writes by ingestion process.
DROP POLICY IF EXISTS p_mem_dedup_select ON memory_ingest_dedup;
CREATE POLICY p_mem_dedup_select ON memory_ingest_dedup
  FOR SELECT USING (
    (current_user IN ('rag_read','rag_write','rag_admin')) AND app_row_visible(tenant_id)
  );

DROP POLICY IF EXISTS p_mem_dedup_insert ON memory_ingest_dedup;
CREATE POLICY p_mem_dedup_insert ON memory_ingest_dedup
  FOR INSERT WITH CHECK (
    (current_user IN ('rag_write','rag_admin')) AND (NOT app_require_tenant() OR tenant_id = app_current_tenant())
  );

-- =====================================================================
-- 5. Visibility / Debug Helpers
-- =====================================================================
CREATE OR REPLACE VIEW rls_debug_effective AS
SELECT current_user            AS who,
       app_current_tenant()    AS session_tenant,
       app_require_tenant()    AS enforcing,
       now()                   AS at;

-- =====================================================================
-- 6. Notes
-- =====================================================================
-- To enable enforcement mode:
--   SELECT set_config('app.require_tenant','on', false);
-- To set tenant for a session:
--   SELECT app_set_tenant('tenant_a');
-- To tag pre-existing rows (one-time backfill):
--   UPDATE doc_embeddings SET tenant_id='tenant_a' WHERE tenant_id IS NULL;
--   UPDATE device_metrics SET tenant_id='tenant_a' WHERE tenant_id IS NULL;
--   UPDATE memory_ingest_dedup SET tenant_id='tenant_a' WHERE tenant_id IS NULL;
-- After backfill, enable enforcement.

-- End of rls_policies.sql
