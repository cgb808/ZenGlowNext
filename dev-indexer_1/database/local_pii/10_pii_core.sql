-- Family-specific data (PII)
CREATE TABLE IF NOT EXISTS family_people (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  age INT NOT NULL,
  grade_band TEXT NOT NULL,
  household_id TEXT,
  meta JSONB
);

CREATE TABLE IF NOT EXISTS family_artifacts (
  id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  tags TEXT[],
  content_ref TEXT,
  meta JSONB
);

CREATE TABLE IF NOT EXISTS family_health_metrics (
  id BIGSERIAL PRIMARY KEY,
  entity_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value_text TEXT,
  value_num DOUBLE PRECISION,
  unit TEXT,
  ts TIMESTAMPTZ DEFAULT now()
);

-- Session & voice processing (PII)
CREATE TABLE IF NOT EXISTS sessions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  session_key TEXT UNIQUE NOT NULL,
  state JSONB DEFAULT '{}'::jsonb,
  accum_text TEXT DEFAULT '',
  turns INT DEFAULT 0,
  is_final BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS voice_fragments (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES sessions(id),
  fragment TEXT NOT NULL,
  is_final BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS intent_events (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES sessions(id),
  domain TEXT NOT NULL,
  confidence DOUBLE PRECISION,
  thresholds JSONB,
  reasons JSONB,
  recommendation TEXT
);