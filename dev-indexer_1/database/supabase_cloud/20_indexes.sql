-- ANN and covering indexes
-- IVF Flat (most common)
CREATE INDEX IF NOT EXISTS doc_embeddings_embedding_ivf
ON doc_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists=100);

-- HNSW (if supported by your pgvector version)
-- Requires pgvector >= 0.5.0
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
ON chunks USING hnsw (embedding_small vector_cosine_ops) WITH (m=16, ef_construction=64);

-- Covering indexes for retrieval
CREATE INDEX IF NOT EXISTS chunks_retrieval_covering_idx
ON chunks (document_id, active, tenant_id) INCLUDE (text, token_count, authority_score);