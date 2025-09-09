Back to Docs Index

RLS Policy Reference (Pre-Supabase)
Design goals: multi-tenant isolation via tenant_id, open dev mode by default, roles: rag_read, rag_write, rag_admin.

Tables
doc_embeddings, device_metrics, memory_ingest_dedup (optional tenant).

Session GUCs
app.current_tenant, app.require_tenant (toggle enforcement).

Helper Functions
app_set_tenant, app_current_tenant, app_row_visible(row_tenant) central predicate.

Modes
Mode	require_tenant	Visibility
Open	off	All rows
Enforcing	on	Matching tenant + NULL (admin)
Policy Summary
SELECT allowed if app_row_visible(tenant_id). INSERT/UPDATE require tenant match in enforcing mode. DELETE restricted to admin.

Typical Session
SELECT app_set_tenant('tenant_a');
SELECT set_config('app.require_tenant','on', false);
SELECT id FROM doc_embeddings LIMIT 5;
Backfill Steps
Tag NULL tenants, then enable enforcement.

Soft Deletes
Add deleted_at TIMESTAMPTZ; extend predicate with deleted_at IS NULL.

Apply
psql ... -f sql/init.sql then -f sql/rls_policies.sql.

Verify
Check pg_class.relrowsecurity and diagnostic view if present.

Future
JWT claim → tenant mapping; audit trail; soft-delete adoption.