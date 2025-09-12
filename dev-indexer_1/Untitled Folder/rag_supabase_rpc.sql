-- Supabase RPC for remote similarity search over doc_embeddings
-- Requires pgvector extension and appropriate role privileges.
-- Create function idempotently.
-- Exposed via PostgREST RPC: POST /rest/v1/rpc/rag_search

CREATE OR REPLACE FUNCTION rag_search(query_vec vector, match_count int DEFAULT 10)
RETURNS TABLE(id bigint, chunk text, distance double precision, source text, batch_tag text)
LANGUAGE sql STABLE AS $$
    SELECT d.id, d.chunk, (d.embedding <-> query_vec) AS distance, d.source, d.batch_tag
    FROM doc_embeddings d
    ORDER BY d.embedding <-> query_vec
    LIMIT match_count;
$$;

-- Optionally revoke execute from public and grant to specific API role(s) if locking down.
-- REVOKE ALL ON FUNCTION rag_search(vector,int) FROM PUBLIC;
-- GRANT EXECUTE ON FUNCTION rag_search(vector,int) TO authenticated, service_role;  -- adjust roles

