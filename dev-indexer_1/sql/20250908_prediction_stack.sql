-- Prediction stack: Timescale + pgvector schema for family/health context and AOS stats
-- Safe to re-run; uses IF NOT EXISTS

BEGIN;

-- Extensions (Timescale is optional; pgvector required)
DO $$
BEGIN
  BEGIN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS timescaledb';
  EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'timescaledb not installed or unavailable; continuing without hypertables';
  END;
END$$;
CREATE EXTENSION IF NOT EXISTS vector;

-- Family events (time-series)
CREATE TABLE IF NOT EXISTS family_events (
  event_id     BIGSERIAL PRIMARY KEY,
  person_id    TEXT NOT NULL,
  ts           TIMESTAMPTZ NOT NULL,
  event_type   TEXT NOT NULL,
  details      JSONB DEFAULT '{}'::jsonb
);
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'create_hypertable'
  ) THEN
    PERFORM create_hypertable('family_events', 'ts', if_not_exists => TRUE);
  ELSE
    RAISE NOTICE 'timescaledb not available; family_events left as regular table';
  END IF;
END$$;
CREATE INDEX IF NOT EXISTS idx_family_events_person_ts ON family_events(person_id, ts DESC);

-- Health metrics (time-series)
CREATE TABLE IF NOT EXISTS health_metrics (
  person_id    TEXT NOT NULL,
  ts           TIMESTAMPTZ NOT NULL,
  metric       TEXT NOT NULL,
  value        DOUBLE PRECISION NOT NULL,
  unit         TEXT,
  meta         JSONB DEFAULT '{}'::jsonb,
  PRIMARY KEY (person_id, ts, metric)
);
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'create_hypertable'
  ) THEN
    PERFORM create_hypertable('health_metrics', 'ts', if_not_exists => TRUE);
  ELSE
    RAISE NOTICE 'timescaledb not available; health_metrics left as regular table';
  END IF;
END$$;
CREATE INDEX IF NOT EXISTS idx_health_metrics_person_metric_ts ON health_metrics(person_id, metric, ts DESC);

-- AOS matches (time-series) for win/loss tracking
CREATE TABLE IF NOT EXISTS aos_matches (
  match_id         BIGSERIAL PRIMARY KEY,
  ts               TIMESTAMPTZ NOT NULL,
  season           TEXT,
  player           TEXT NOT NULL,
  opponent         TEXT,
  faction          TEXT,
  opponent_faction TEXT,
  outcome          TEXT NOT NULL CHECK (outcome IN ('win','loss','draw')),
  score            INT,
  meta             JSONB DEFAULT '{}'::jsonb
);
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'create_hypertable'
  ) THEN
    PERFORM create_hypertable('aos_matches', 'ts', if_not_exists => TRUE);
  ELSE
    RAISE NOTICE 'timescaledb not available; aos_matches left as regular table';
  END IF;
END$$;
CREATE INDEX IF NOT EXISTS idx_aos_matches_player_ts ON aos_matches(player, ts DESC);
CREATE INDEX IF NOT EXISTS idx_aos_matches_outcome ON aos_matches(outcome);

-- Player stats (materialized view)
CREATE MATERIALIZED VIEW IF NOT EXISTS aos_player_stats AS
SELECT
  player,
  COUNT(*)                                 AS games,
  SUM((outcome='win')::INT)                AS wins,
  SUM((outcome='loss')::INT)               AS losses,
  SUM((outcome='draw')::INT)               AS draws,
  ROUND(100.0 * SUM((outcome='win')::INT) / NULLIF(COUNT(*),0), 2) AS win_rate
FROM aos_matches
GROUP BY player
WITH NO DATA;

-- Helper to refresh stats quickly
CREATE OR REPLACE FUNCTION refresh_aos_stats() RETURNS VOID LANGUAGE SQL AS $$
  REFRESH MATERIALIZED VIEW CONCURRENTLY aos_player_stats;
$$;

-- Documents + pgvector embeddings (384-dim by default; adjust if using a different model)
CREATE TABLE IF NOT EXISTS documents (
  doc_id     BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source     TEXT,
  family_id  TEXT,
  title      TEXT,
  text       TEXT NOT NULL
);

-- NOTE: Adjust dimension to match the chosen embedding model (e.g., 384 for bge-small-en-v1.5, 768 for e5-large)
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_name='doc_embeddings' AND column_name='embedding'
  ) THEN
    CREATE TABLE doc_embeddings (
      doc_id     BIGINT PRIMARY KEY REFERENCES documents(doc_id) ON DELETE CASCADE,
      embedding  VECTOR(384),
      model      TEXT NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_doc_embeddings_embedding ON doc_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists=100);
  END IF;
END $$;

-- Recommended ANN search tuning (per-session):
--   SET ivfflat.probes = 10;  -- increase for better recall
--   ANALYZE doc_embeddings;

COMMIT;
