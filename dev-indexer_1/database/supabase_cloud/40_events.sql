-- General events table (avoid PII; consider hashing user_token)
CREATE TABLE IF NOT EXISTS events (
  event_time TIMESTAMPTZ NOT NULL,
  user_token TEXT,
  agent_key TEXT,
  device_key TEXT,
  location_key TEXT,
  event_type TEXT NOT NULL,
  data_payload_raw JSONB,
  data_payload_proc JSONB,
  event_embedding vector(768),
  PRIMARY KEY (event_time, user_token, event_type)
) PARTITION BY RANGE (event_time);