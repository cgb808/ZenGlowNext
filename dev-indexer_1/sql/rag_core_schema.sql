-- RAG core schema (idempotent)
CREATE TABLE IF NOT EXISTS doc_embeddings (
  id BIGSERIAL PRIMARY KEY,
  source TEXT,
  chunk TEXT NOT NULL,
  embedding vector(768),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_metrics (
  time TIMESTAMPTZ NOT NULL,
  device_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value DOUBLE PRECISION,
  PRIMARY KEY(time, device_id, metric)
);
SELECT create_hypertable('device_metrics','time', if_not_exists=>TRUE);

-- Optional provenance tag
ALTER TABLE doc_embeddings ADD COLUMN IF NOT EXISTS batch_tag TEXT;

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
