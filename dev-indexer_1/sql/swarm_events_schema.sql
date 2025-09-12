-- swarm_events_schema.sql
-- Purpose: Capture routing, feedback, and optimization events for the swarm scheduler
-- Provides structured columns for future predictive modeling and long-horizon analytics.
-- Hash Strategy:
--   query_hash  = sha256(lower(trim(query_text)))
--   path_hash   = sha256(sorted factors + sorted parameter keys) generated in app layer
--   session_id / user_hash optional (personalization & longitudinal tracking)
-- FDW / Timescale Notes:
--   Writes remain local (Supabase primary). Long-range analytical joins can leverage
--   a TimescaleDB instance via postgres_fdw (see fdw_timescale_setup.sql) mapping this table.
--   If hypertable migration desired later: SELECT create_hypertable('swarm_events','ts');
-- Index Guidance:
--   BRIN on ts for append-only efficiency.
--   B-tree on (query_hash), (path_hash) for exact dedupe / rollups.
--   Partial IVF/IVFFLAT index for event_embedding (future) filtered on swarm_% event_type.
--   (Embedding column is NULL now; left for future migration.)

CREATE TABLE IF NOT EXISTS swarm_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type TEXT NOT NULL CHECK (event_type ~ '^swarm_'), -- e.g. swarm_route, swarm_feedback, swarm_optimize
    session_id TEXT NULL,
    user_hash TEXT NULL,
    query_text TEXT NULL,
    query_hash TEXT NULL,  -- sha256 of normalized query_text
    path_hash TEXT NULL,   -- sha256 of sorted factors + parameter keys
    partition_id INT NULL,
    swarm_type TEXT NULL,  -- PRIMARY | EXPLORER
    success BOOLEAN NULL,
    latency_ms DOUBLE PRECISION NULL,
    quality_signal DOUBLE PRECISION NULL,
    factors JSONB NULL,        -- array of strings (for optimize candidates)
    parameters JSONB NULL,     -- key/value object for candidate parameters
    telemetry JSONB NULL,      -- snapshot fragment or scheduler metrics
    meta JSONB NULL,           -- reserved for additional context
    event_embedding vector(384) NULL -- placeholder dimension (if pgvector installed later)
);

COMMENT ON TABLE swarm_events IS 'Swarm routing / feedback / optimization event log (append-only).';

CREATE INDEX IF NOT EXISTS idx_swarm_events_ts_brin ON swarm_events USING brin (ts);
CREATE INDEX IF NOT EXISTS idx_swarm_events_query_hash ON swarm_events (query_hash);
CREATE INDEX IF NOT EXISTS idx_swarm_events_path_hash ON swarm_events (path_hash);
CREATE INDEX IF NOT EXISTS idx_swarm_events_event_type ON swarm_events (event_type);

-- Future (when pgvector + embeddings present) and only for swarm_* events containing embeddings:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_swarm_events_embedding_partial ON swarm_events USING ivfflat (event_embedding vector_cosine_ops) WITH (lists=100)
--   WHERE event_type LIKE 'swarm_%' AND event_embedding IS NOT NULL;

-- Optional rollup materialized view example (not yet populated):
-- CREATE MATERIALIZED VIEW IF NOT EXISTS swarm_partition_daily AS
-- SELECT date_trunc('day', ts) AS day, partition_id,
--        count(*) FILTER (WHERE event_type='swarm_route') AS route_count,
--        avg(latency_ms) FILTER (WHERE latency_ms IS NOT NULL) AS avg_latency,
--        avg(CASE WHEN success THEN 1 ELSE 0 END) FILTER (WHERE success IS NOT NULL) AS success_rate
-- FROM swarm_events
-- GROUP BY 1,2;
-- CREATE INDEX IF NOT EXISTS idx_swarm_partition_daily_day ON swarm_partition_daily(day);
