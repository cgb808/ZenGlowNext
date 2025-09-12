-- Query performance tracking
CREATE TABLE IF NOT EXISTS query_performance (
  id BIGSERIAL PRIMARY KEY,
  query_text TEXT,
  query_embedding vector(768),
  latency_ms INT,
  results_count INT,
  metrics JSONB,
  occurred_at TIMESTAMPTZ DEFAULT now()
);

-- Query result caching
CREATE TABLE IF NOT EXISTS query_cache (
  query_hash TEXT PRIMARY KEY,
  query_embedding vector(384),
  cached_results JSONB,
  hit_count INT DEFAULT 1,
  expires_at TIMESTAMPTZ
);

-- Interaction events (partitioned by time)
CREATE TABLE IF NOT EXISTS interaction_events (
  id BIGSERIAL PRIMARY KEY,
  occurred_at TIMESTAMPTZ NOT NULL,
  user_hash TEXT,
  session_id TEXT,
  query_vector vector(384),
  chunk_id BIGINT,
  event_type TEXT NOT NULL,
  dwell_time_ms INT,
  extra JSONB,
  tenant_id TEXT
) PARTITION BY RANGE (occurred_at);