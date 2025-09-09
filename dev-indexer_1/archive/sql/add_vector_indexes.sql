-- ARCHIVED: Overlaps with sql/rag_indexes.sql. Use rag_indexes.sql for ANN + supporting indexes.

-- Vector & dedupe performance indexes (legacy excerpt)
CREATE INDEX IF NOT EXISTS doc_embeddings_embedding_ivf
ON doc_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists=100);

CREATE INDEX IF NOT EXISTS doc_embeddings_metadata_content_hash_idx
ON doc_embeddings ((metadata->>'content_hash'));
