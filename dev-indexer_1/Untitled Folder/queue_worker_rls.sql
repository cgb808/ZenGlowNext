-- queue_worker_rls.sql
-- Optional RLS hardening for queue + embeddings tables.
-- Assumes role `queue_worker` (created via queue_worker_role.sql) and that you
-- want to restrict its visibility to only necessary columns/rows.
-- NOTE: Supabase enables RLS per table; ensure you've audited other policies.

ALTER TABLE IF EXISTS public.code_chunk_ingest_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.code_chunk_ingest_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.doc_embeddings ENABLE ROW LEVEL SECURITY;

-- Queue: allow worker to select pending/processing rows & update its locked rows.
DROP POLICY IF EXISTS p_queue_select_worker ON public.code_chunk_ingest_queue;
CREATE POLICY p_queue_select_worker ON public.code_chunk_ingest_queue
  FOR SELECT TO queue_worker
  USING (status IN ('pending','processing'));

DROP POLICY IF EXISTS p_queue_update_worker ON public.code_chunk_ingest_queue;
CREATE POLICY p_queue_update_worker ON public.code_chunk_ingest_queue
  FOR UPDATE TO queue_worker
  USING (status IN ('pending','processing'))
  WITH CHECK (status IN ('processing','done','error'));

-- Log: allow worker to insert only (no select needed)
DROP POLICY IF EXISTS p_log_insert_worker ON public.code_chunk_ingest_log;
CREATE POLICY p_log_insert_worker ON public.code_chunk_ingest_log
  FOR INSERT TO queue_worker
  WITH CHECK (true);

-- Embeddings: allow insert + select of its own rows (batch_tag used for provenance)
DROP POLICY IF EXISTS p_doc_embeddings_insert_worker ON public.doc_embeddings;
CREATE POLICY p_doc_embeddings_insert_worker ON public.doc_embeddings
  FOR INSERT TO queue_worker
  WITH CHECK (true);

DROP POLICY IF EXISTS p_doc_embeddings_select_worker ON public.doc_embeddings;
CREATE POLICY p_doc_embeddings_select_worker ON public.doc_embeddings
  FOR SELECT TO queue_worker
  USING (true);
