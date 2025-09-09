-- Development Knowledge Graph Schema (v5 - Production Optimized)
-- Features:
-- 1) Partitioned time-series via pg_partman (manual setup section below)
-- 2) Smart comments to shape pg_graphql API (omit raw vectors)
-- 3) RPC functions for edge functions (read-only STABLE)

-- Extensions (enable in Supabase: vector, pg_partman, pg_cron)
CREATE EXTENSION IF NOT EXISTS vector;

-- Types
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dev_event_type') THEN
    CREATE TYPE dev_event_type AS ENUM (
      'ai_interaction','human_commit','decision_log','bug_report','performance_test','security_scan'
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_outcome') THEN
    CREATE TYPE event_outcome AS ENUM ('win','loss','neutral','observation');
  END IF;
END $$;

-- Core entities
CREATE TABLE IF NOT EXISTS project_missions (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT UNIQUE NOT NULL,
  description TEXT NOT NULL,
  status      TEXT DEFAULT 'active',
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_epics (
  id          BIGSERIAL PRIMARY KEY,
  mission_id  BIGINT REFERENCES project_missions(id),
  name        TEXT NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_documents (
  id               BIGSERIAL PRIMARY KEY,
  file_path        TEXT UNIQUE NOT NULL,
  language         TEXT,
  content_hash     TEXT NOT NULL,
  version          INT NOT NULL DEFAULT 1,
  created_at       TIMESTAMPTZ DEFAULT now(),
  last_analyzed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS code_chunks (
  id                 BIGSERIAL PRIMARY KEY,
  document_id        BIGINT REFERENCES source_documents(id) ON DELETE CASCADE,
  chunk_name         TEXT,
  start_line         INT NOT NULL,
  end_line           INT NOT NULL,
  code_content       TEXT NOT NULL,
  checksum           TEXT NOT NULL,
  code_embedding     vector(768),
  analysis_metrics   JSONB DEFAULT '{}'::jsonb
);

-- Data quality constraints and dedup helpers
ALTER TABLE code_chunks
  ADD CONSTRAINT code_chunks_line_bounds_chk CHECK (start_line > 0 AND end_line >= start_line)
  , ADD CONSTRAINT code_chunks_checksum_not_empty_chk CHECK (length(checksum) > 0)
  ;
-- Avoid duplicate line ranges within a document (best-effort; allow NULL chunk_name)
CREATE UNIQUE INDEX IF NOT EXISTS code_chunks_doc_line_uniq
  ON code_chunks(document_id, start_line, end_line);

-- Time-series partitioned tables
CREATE TABLE IF NOT EXISTS development_log (
  occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  id                  BIGSERIAL NOT NULL,
  epic_id             BIGINT REFERENCES project_epics(id),
  event_type          dev_event_type NOT NULL,
  outcome             event_outcome,
  title               TEXT NOT NULL,
  narrative           TEXT NOT NULL,
  narrative_embedding vector(768),
  author              TEXT,
  metadata            JSONB DEFAULT '{}'::jsonb,
  PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);
COMMENT ON TABLE development_log IS 'The central, time-series log of significant development events.';
COMMENT ON COLUMN development_log.narrative_embedding IS E'@omit';

CREATE TABLE IF NOT EXISTS log_to_chunk_link (
  log_id    BIGINT NOT NULL,
  log_time  TIMESTAMPTZ NOT NULL,
  chunk_id  BIGINT REFERENCES code_chunks(id) ON DELETE CASCADE,
  PRIMARY KEY (log_id, log_time, chunk_id)
) PARTITION BY RANGE (log_time);
COMMENT ON TABLE log_to_chunk_link IS E'@omit';

-- Ensure link rows reference an existing (id, occurred_at) from development_log
ALTER TABLE ONLY log_to_chunk_link
  ADD CONSTRAINT log_to_chunk_link_log_fk
  FOREIGN KEY (log_id, log_time)
  REFERENCES development_log(id, occurred_at)
  ON DELETE CASCADE;

-- Indexes
CREATE INDEX IF NOT EXISTS dev_log_epic_idx ON development_log(epic_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS code_chunks_doc_id_idx ON code_chunks(document_id);
CREATE INDEX IF NOT EXISTS dev_log_type_outcome_time_idx ON development_log(event_type, outcome, occurred_at DESC);
-- Vector ANN indexes (partial to skip NULLs); consider HNSW when available
CREATE INDEX IF NOT EXISTS dev_log_embedding_idx
  ON development_log USING ivfflat (narrative_embedding vector_cosine_ops)
  WITH (lists=100)
  WHERE narrative_embedding IS NOT NULL;
CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx
  ON code_chunks USING ivfflat (code_embedding vector_cosine_ops)
  WITH (lists=100)
  WHERE code_embedding IS NOT NULL;

-- Helpful relational/partition pruning indexes
CREATE INDEX IF NOT EXISTS log_to_chunk_link_time_idx ON log_to_chunk_link(log_time);
CREATE INDEX IF NOT EXISTS log_to_chunk_link_chunk_idx ON log_to_chunk_link(chunk_id);

-- RPCs
CREATE OR REPLACE FUNCTION search_code_chunks(
  query_embedding vector(768), match_limit INT DEFAULT 10
) RETURNS SETOF code_chunks AS $$
BEGIN
  RETURN QUERY
  SELECT * FROM code_chunks
  ORDER BY code_embedding <=> query_embedding
  LIMIT match_limit;
END; $$ LANGUAGE plpgsql STABLE;
COMMENT ON FUNCTION search_code_chunks IS 'Performs a semantic search on code chunks.';

CREATE OR REPLACE FUNCTION get_narrative_for_complex_code(mission_name TEXT)
RETURNS TABLE (
  chunk_id BIGINT,
  chunk_name TEXT,
  complexity INT,
  narrative_title TEXT,
  outcome event_outcome,
  occurred_at TIMESTAMPTZ
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    cc.id,
    cc.chunk_name,
    (cc.analysis_metrics ->> 'cyclomatic_complexity')::INT,
    dl.title,
    dl.outcome,
    dl.occurred_at
  FROM project_missions pm
  JOIN project_epics pe ON pm.id = pe.mission_id
  JOIN development_log dl ON pe.id = dl.epic_id
  JOIN log_to_chunk_link ltcl ON dl.id = ltcl.log_id AND dl.occurred_at = ltcl.log_time
  JOIN code_chunks cc ON ltcl.chunk_id = cc.id
  WHERE pm.name = mission_name
  ORDER BY (cc.analysis_metrics ->> 'cyclomatic_complexity')::INT DESC
  LIMIT 5;
END; $$ LANGUAGE plpgsql STABLE;
COMMENT ON FUNCTION get_narrative_for_complex_code IS 'Finds the story behind the most complex code for a given mission.';

-- pg_partman + pg_cron setup (manual)
-- Keep app logic in Edge Functions (TS/JS); DB holds schema & RPCs only.
/*
SELECT partman.create_parent(
   p_parent_table => 'public.development_log',
   p_control => 'occurred_at',
   p_type => 'native',
   p_interval=> '1 month',
   p_premake => 4
);

SELECT partman.create_parent(
   p_parent_table => 'public.log_to_chunk_link',
   p_control => 'log_time',
   p_type => 'native',
   p_interval=> '1 month',
   p_premake => 4
);

SELECT cron.schedule(
    'partman-nightly-maintenance',
    '0 1 * * *',
    $$ SELECT partman.run_maintenance_proc(); $$
);
*/
