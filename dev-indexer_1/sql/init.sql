-- Initialize pgvector extension and embeddings table
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS doc_embeddings (
  id SERIAL PRIMARY KEY,
  source TEXT,
  chunk TEXT NOT NULL,
  embedding vector(384), -- adjust if model dim differs
  metadata JSONB,
  batch_tag TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doc_embeddings_source ON doc_embeddings(source);
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_batch_tag ON doc_embeddings(batch_tag);
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_created_at ON doc_embeddings(created_at);

-- Vector similarity helper index (HNSW for speed if available in pgvector version)
-- For pgvector >= 0.5.0
DO $$
BEGIN
  EXECUTE 'CREATE INDEX IF NOT EXISTS idx_doc_embeddings_embedding ON doc_embeddings USING hnsw (embedding vector_l2_ops)';
EXCEPTION WHEN others THEN
  -- fallback to ivfflat if hnsw not supported
  BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_doc_embeddings_embedding_ivf ON doc_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)';
  EXCEPTION WHEN others THEN
    -- ignore if neither available
    NULL;
  END;
END$$;
