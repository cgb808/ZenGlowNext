-- Insight graph: capture uncorrelated signals, pheromones, and candidate insights
BEGIN;

-- Generic signals extracted from conversation (entities, moods, appetite mentions, locations, etc.)
CREATE TABLE IF NOT EXISTS convo_signals (
  signal_id   BIGSERIAL PRIMARY KEY,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT,            -- conversation/message id
  person_id   TEXT,            -- who it's about
  name        TEXT NOT NULL,   -- normalized entity/signal name
  kind        TEXT NOT NULL,   -- mood|appetite|symptom|place|thing|topic|tutor_tag|...
  weight      DOUBLE PRECISION DEFAULT 1.0,
  meta        JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_convo_signals_person_ts ON convo_signals(person_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_convo_signals_name ON convo_signals(name);

-- Pheromones: accumulation tracks for names/places/things that queries stimulate
CREATE TABLE IF NOT EXISTS pheromones (
  key         TEXT PRIMARY KEY,   -- e.g., entity name
  score       DOUBLE PRECISION NOT NULL DEFAULT 0,
  last_ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
  meta        JSONB DEFAULT '{}'::jsonb
);

-- Candidate insights: store surfaced links for review
CREATE TABLE IF NOT EXISTS insight_candidates (
  insight_id  BIGSERIAL PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  person_id   TEXT,
  hypothesis  TEXT NOT NULL,
  evidence    JSONB NOT NULL,      -- references to signals/metrics
  score       DOUBLE PRECISION NOT NULL,
  status      TEXT NOT NULL DEFAULT 'new'   -- new|accepted|rejected|escalate
);
CREATE INDEX IF NOT EXISTS idx_insight_candidates_status ON insight_candidates(status);

-- Optional: lightweight KG edges between entities/topics
CREATE TABLE IF NOT EXISTS kg_edges (
  src   TEXT NOT NULL,
  dst   TEXT NOT NULL,
  rel   TEXT NOT NULL,
  weight DOUBLE PRECISION DEFAULT 1.0,
  PRIMARY KEY (src, dst, rel)
);

COMMIT;
