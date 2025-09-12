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
-- Create hypertable only if timescaledb extension is available (keeps schema portable)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='timescaledb') THEN
    PERFORM create_hypertable('device_metrics','time', if_not_exists=>TRUE);
  END IF;
END $$;

-- Optional provenance tag
ALTER TABLE doc_embeddings ADD COLUMN IF NOT EXISTS batch_tag TEXT;
