-- Unified Events Schema (Timescale + pgvector)
-- Purpose: Central, append-only event stream acting as the system's "river of data".
-- Safety: Designed to work even if related entity tables are not yet present.

-- Required extensions (idempotent)
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;         -- for optional field-level encryption
CREATE EXTENSION IF NOT EXISTS vector;           -- pgvector (a.k.a. "vector")
CREATE EXTENSION IF NOT EXISTS btree_gin;        -- helpful for mixed indexes
CREATE EXTENSION IF NOT EXISTS pg_trgm;          -- text similarity ops (optional)

-- Core events table
CREATE TABLE IF NOT EXISTS events (
    event_time         TIMESTAMPTZ NOT NULL,
    -- Pseudonymous identifiers preferred; avoid direct FK into PII DB
    user_token         TEXT,
    agent_key          TEXT,
    device_key         TEXT,
    location_key       TEXT,

    event_type         TEXT NOT NULL,
    data_payload_raw   JSONB,         -- sensitive raw input (consider encryption at column or app layer)
    data_payload_proc  JSONB,         -- anonymized/processed payload for analytics
    event_embedding    vector(768),   -- semantic embedding of processed payload

    -- Primary key optimized for time-first retrieval; token+type disambiguates within same instant
    PRIMARY KEY (event_time, user_token, event_type)
) PARTITION BY RANGE (event_time);

-- Convert to hypertable (no-op if already done)
SELECT create_hypertable('events', 'event_time', if_not_exists => TRUE);

-- Useful indexes
CREATE INDEX IF NOT EXISTS ix_events_time_desc ON events (event_time DESC);
CREATE INDEX IF NOT EXISTS ix_events_type_time ON events (event_type, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_events_user_time ON events (user_token, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_events_proc_gin ON events USING GIN (data_payload_proc);

-- Vector ANN index (partial) – adapt to IVF/HNSW per Postgres version/pgvector support
-- Recommended: HNSW for read-mostly workloads; fallback to IVF+PQ if desired.
DO $$
BEGIN
    -- Try HNSW first; if not supported, fall back to IVFFlat.
    BEGIN
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_events_embed_hnsw ON events USING hnsw (event_embedding) WHERE event_embedding IS NOT NULL';
    EXCEPTION WHEN undefined_object THEN
        -- Older pgvector without HNSW, use IVF with list count tuned to data size
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_events_embed_ivf ON events USING ivfflat (event_embedding vector_cosine_ops) WITH (lists = 100) WHERE event_embedding IS NOT NULL';
    END;
END$$;

-- Guardian layer: redact raw payload after retention window (default 30 days)
CREATE OR REPLACE FUNCTION redact_raw_payload_older_than(days INTEGER DEFAULT 30)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE events
       SET data_payload_raw = NULL
     WHERE event_time < NOW() - make_interval(days => days)
       AND data_payload_raw IS NOT NULL;
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;

COMMENT ON TABLE events IS 'Unified, time-partitioned event stream across all domains (conversation, health, education, automation).';
COMMENT ON COLUMN events.user_token IS 'Pseudonymous key linking to PII vault via secure token map.';
COMMENT ON COLUMN events.data_payload_raw IS 'Sensitive raw input; consider pgcrypto or app-layer encryption + scheduled redaction.';
COMMENT ON COLUMN events.data_payload_proc IS 'Anonymized/structured payload for analytics and ASO swarms.';

-- RLS (annotated, intentionally not enabled yet)
-- Guidance:
-- 1) Enable RLS only after data model settles:
--      ALTER TABLE events ENABLE ROW LEVEL SECURITY;
-- 2) Apply policies keyed by event_type and user_token:
--      CREATE POLICY events_self_access ON events
--        USING (user_token = current_setting('app.user_token', true))
--        WITH CHECK (user_token = current_setting('app.user_token', true));
--      CREATE POLICY events_by_type ON events
--        USING (event_type = ANY (string_to_array(current_setting('app.event_types', true), ',')));
-- 3) Keep re-identification in the PII vault. Do not store PII here.
