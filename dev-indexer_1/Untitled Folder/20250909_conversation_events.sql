-- 20250909_conversation_events.sql
-- Minimal conversation_events table to support async embedding worker.
-- Idempotent and compatible with pgvector if available.

BEGIN;

CREATE TABLE IF NOT EXISTS conversation_events (
    time TIMESTAMPTZ NOT NULL DEFAULT now(),
    id BIGSERIAL NOT NULL,
    scope TEXT NOT NULL DEFAULT 'session',
    user_id TEXT,
    role TEXT,
    content TEXT NOT NULL,
    content_hash TEXT,
    embedded BOOLEAN NOT NULL DEFAULT FALSE,
    embedding vector(384),
    meta JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (time, id)
);

-- Optional: index for fetch ordering
CREATE INDEX IF NOT EXISTS idx_conversation_events_time ON conversation_events(time);
-- Optional partial index for unembedded work queue
CREATE INDEX IF NOT EXISTS idx_conversation_events_unembedded ON conversation_events(time)
WHERE embedded = FALSE AND embedding IS NULL;

COMMIT;
