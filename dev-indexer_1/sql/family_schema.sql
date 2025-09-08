-- Family context persistence schema (idempotent)
CREATE TABLE IF NOT EXISTS family_people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INT NOT NULL,
    grade_band TEXT NOT NULL,
    last_name TEXT,
    birthdate DATE,
    household_id TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_ts TIMESTAMPTZ DEFAULT now(),
    updated_ts TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS family_relationships (
    guardian_id TEXT NOT NULL REFERENCES family_people(id) ON DELETE CASCADE,
    child_id TEXT NOT NULL REFERENCES family_people(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'guardian',
    legal BOOLEAN NOT NULL DEFAULT TRUE,
    created_ts TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (guardian_id, child_id, kind)
);

CREATE TABLE IF NOT EXISTS family_artifacts (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    content_ref TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_ts TIMESTAMPTZ DEFAULT now()
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

CREATE INDEX IF NOT EXISTS idx_family_artifacts_entity ON family_artifacts(entity_id);
CREATE INDEX IF NOT EXISTS idx_family_artifacts_tags ON family_artifacts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_family_health_entity_metric ON family_health_metrics(entity_id, metric, ts DESC);
