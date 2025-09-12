-- runtime_metrics.sql
-- Table for storing periodic metrics snapshots from various sources (docker, supabase, worker, model).
-- Minimal wide-open schema; extend with indexes as needed.

CREATE TABLE IF NOT EXISTS runtime_metrics (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,              -- e.g. 'docker:api', 'supabase:queue', 'worker:embedding'
  metric TEXT NOT NULL,              -- metric key name (cpu_percent, mem_bytes, queue_pending, etc.)
  value DOUBLE PRECISION,            -- numeric value
  labels JSONB DEFAULT '{}'::jsonb,  -- optional label map (container name, table, etc.)
  collected_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS runtime_metrics_source_time_idx ON runtime_metrics (source, collected_at DESC);
CREATE INDEX IF NOT EXISTS runtime_metrics_metric_time_idx ON runtime_metrics (metric, collected_at DESC);

-- Retention policy (manual; implement a cron or external job to prune):
-- DELETE FROM runtime_metrics WHERE collected_at < now() - interval '30 days';
