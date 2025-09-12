-- RAG core & metrics schema (idempotent)
CREATE TABLE IF NOT EXISTS doc_embeddings (
	id BIGSERIAL PRIMARY KEY,
	source TEXT,
	chunk TEXT NOT NULL,
	embedding vector(768),
	batch_tag TEXT,
	metadata JSONB,
	created_at TIMESTAMPTZ DEFAULT now()
);

-- Timescale hypertable conversion (safe if extension absent)
DO $$
BEGIN
	IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='timescaledb') THEN
		PERFORM create_hypertable('doc_embeddings','created_at', if_not_exists=>TRUE);
	END IF;
END $$;

CREATE TABLE IF NOT EXISTS device_metrics (
	time TIMESTAMPTZ NOT NULL,
	device_id TEXT NOT NULL,
	metric TEXT NOT NULL,
	value DOUBLE PRECISION,
	PRIMARY KEY(time, device_id, metric)
);

DO $$
BEGIN
	IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='timescaledb') THEN
		PERFORM create_hypertable('device_metrics','time', if_not_exists=>TRUE);
	END IF;
END $$;

-- Optional content hash for dedupe
ALTER TABLE doc_embeddings ADD COLUMN IF NOT EXISTS content_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_content_hash ON doc_embeddings(content_hash);
