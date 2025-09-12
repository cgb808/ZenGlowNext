-- RPC for similarity search over doc_embeddings
-- Requires SECURITY DEFINER if you want anon key access; adjust as needed.

-- Function: match_documents(embedding vector, match_count int)
CREATE OR REPLACE FUNCTION match_documents(embedding vector, match_count int)
RETURNS TABLE (id bigint, chunk text, distance double precision)
LANGUAGE sql
STABLE
AS $$
  SELECT id, chunk, (doc_embeddings.embedding <-> embedding)::float AS distance
  FROM doc_embeddings
  ORDER BY doc_embeddings.embedding <-> embedding
  LIMIT match_count
$$;

-- Optional: grant execution to anon role (adjust roles to your project)
-- GRANT EXECUTE ON FUNCTION match_documents(vector, int) TO anon, authenticated;

-- RPC for similarity search over chunks (using embedding_small by default)
CREATE OR REPLACE FUNCTION match_chunks(embedding vector, match_count int)
RETURNS TABLE (id bigint, text text, distance double precision)
LANGUAGE sql
STABLE
AS $$
  SELECT id, text, (chunks.embedding_small <-> embedding)::float AS distance
  FROM chunks
  WHERE chunks.embedding_small IS NOT NULL
  ORDER BY chunks.embedding_small <-> embedding
  LIMIT match_count
$$;
-- GRANT EXECUTE ON FUNCTION match_chunks(vector, int) TO anon, authenticated;