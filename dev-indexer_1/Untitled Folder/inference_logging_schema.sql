-- Inference Logging Schema
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
    decision TEXT,
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

CREATE INDEX IF NOT EXISTS idx_infer_events_model_ts ON model_inference_events(model_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_infer_events_decision_ts ON model_inference_events(decision, ts DESC);
