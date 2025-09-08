-- Inference logging schema (Timescale-compatible). Optional extension enable:
--   CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS model_inference_events (
    id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_name TEXT NOT NULL,
    user_id TEXT,
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    avg_logprob REAL,
    entropy REAL,
    top1_prob REAL,
    decision TEXT,          -- proceed|abstain|reflect|retrieve
    meta JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS model_inference_token_stats (
    event_id UUID REFERENCES model_inference_events(id) ON DELETE CASCADE,
    position INT NOT NULL,
    token TEXT NOT NULL,
    logprob REAL NOT NULL,
    is_generated BOOLEAN NOT NULL,
    PRIMARY KEY (event_id, position)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_infer_events_model_ts ON model_inference_events(model_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_infer_events_decision_ts ON model_inference_events(decision, ts DESC);

-- (Optional) Convert to hypertable (if Timescale installed)
-- SELECT create_hypertable('model_inference_events', 'ts', if_not_exists => TRUE);
-- Retention policy example (30 days):
-- SELECT add_retention_policy('model_inference_events', INTERVAL '30 days');

-- Convenience views -------------------------------------------------------
CREATE OR REPLACE VIEW v_inference_recent AS
SELECT id, ts, model_name, decision, avg_logprob, entropy, top1_prob, latency_ms,
       prompt_tokens, completion_tokens
FROM model_inference_events
ORDER BY ts DESC
LIMIT 200;

-- Hourly aggregates (rolling 24h); extend with Timescale continuous agg if desired.
CREATE OR REPLACE VIEW v_inference_hourly_agg AS
SELECT date_trunc('hour', ts) AS hour_bucket,
       model_name,
       count(*) AS events,
       avg(avg_logprob) AS avg_avg_logprob,
       avg(entropy) AS avg_entropy,
       avg(top1_prob) AS avg_top1_prob,
       avg(latency_ms) AS avg_latency_ms,
       sum(prompt_tokens) AS total_prompt_tokens,
       sum(completion_tokens) AS total_completion_tokens,
       jsonb_object_agg(decision, decision_count) AS decisions
FROM (
    SELECT *, 1 AS decision_count FROM model_inference_events
    WHERE ts > now() - interval '24 hours'
) s
GROUP BY 1,2
ORDER BY hour_bucket DESC, model_name;
