-- pgvector approximate index examples (apply when row counts justify)
-- IVF Flat
CREATE INDEX IF NOT EXISTS doc_embeddings_embedding_ivf
ON doc_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists=100);

-- HNSW (if supported by installed pgvector build)
-- CREATE INDEX IF NOT EXISTS doc_embeddings_embedding_hnsw
-- ON doc_embeddings
-- USING hnsw (embedding vector_l2_ops)
-- WITH (m=16, ef_construction=64);
