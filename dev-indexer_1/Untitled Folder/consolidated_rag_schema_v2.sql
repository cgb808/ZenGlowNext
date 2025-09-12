-- =============================================================
-- Consolidated RAG System Schema (v2)
--
-- Combines original architecture with enhancements for:
-- 1. Advanced Retrieval (Parent-Child hierarchy)
-- 2. Scalability (Partitioned interaction events, batch ops)
-- 3. Operational Excellence (Quality logs, async notifications, partition mgmt)
-- 4. Performance Tuning (Targeted indexes, covering vector filters)
-- =============================================================

-- 1. EXTENSIONS -------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. CUSTOM TYPES ----------------------------------------------
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='chunk_role') THEN
    CREATE TYPE chunk_role AS ENUM ('child', 'parent', 'standalone');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='model_status') THEN
    CREATE TYPE model_status AS ENUM ('experimental', 'active', 'deprecated', 'archived');
  END IF;
END $$;

-- 3. CORE TABLES -----------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
  id               BIGSERIAL PRIMARY KEY,
  external_id      TEXT,
  source_type      TEXT NOT NULL DEFAULT 'generic',
  uri              TEXT,
  content_hash     TEXT NOT NULL,
  version          INT  NOT NULL DEFAULT 1,
  latest           BOOLEAN NOT NULL DEFAULT TRUE,
  title            TEXT,
  author           TEXT,
  language         TEXT,
  meta             JSONB DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now(),
  tenant_id        TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
  id                 BIGSERIAL PRIMARY KEY,
  document_id        BIGINT REFERENCES documents(id) ON DELETE CASCADE,
  parent_chunk_id    BIGINT REFERENCES chunks(id),
  role               chunk_role NOT NULL DEFAULT 'standalone',
  ordinal            INT NOT NULL DEFAULT 0,
  text               TEXT NOT NULL,
  token_count        INT,
  checksum           TEXT NOT NULL,
  embedding_small    vector(384),
  embedding_dense    vector(768),
  meta               JSONB DEFAULT '{}'::jsonb,
  signal_stats       JSONB DEFAULT '{}'::jsonb,
  authority_score    REAL,
  active             BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ DEFAULT now(),
  updated_at         TIMESTAMPTZ DEFAULT now(),
  tenant_id          TEXT
);

CREATE TABLE IF NOT EXISTS chunk_features (
  chunk_id              BIGINT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
  feature_schema_version INT NOT NULL DEFAULT 1,
  entities          JSONB,
  keyphrases        JSONB,
  topics            JSONB,
  updated_at        TIMESTAMPTZ DEFAULT now(),
  tenant_id         TEXT
);

CREATE TABLE IF NOT EXISTS interaction_events (
  id              BIGSERIAL PRIMARY KEY,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_hash       TEXT,
  session_id      TEXT,
  query_vector    vector(384),
  chunk_id        BIGINT REFERENCES chunks(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL,
  dwell_time_ms   INT,
  extra           JSONB,
  tenant_id       TEXT
) PARTITION BY RANGE (occurred_at);

CREATE TABLE IF NOT EXISTS interaction_events_default PARTITION OF interaction_events DEFAULT;

-- 4. MLOPS & OPERATIONAL ---------------------------------------
CREATE TABLE IF NOT EXISTS model_registry (
  id           BIGSERIAL PRIMARY KEY,
  model_type   TEXT NOT NULL,
  name         TEXT NOT NULL,
  version      TEXT NOT NULL,
  artifact_ref TEXT,
  meta         JSONB,
  status       model_status NOT NULL DEFAULT 'experimental',
  performance_metrics JSONB,
  description  TEXT,
  created_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE(model_type, name, version)
);

CREATE TABLE IF NOT EXISTS scoring_experiments (
  id             BIGSERIAL PRIMARY KEY,
  name           TEXT UNIQUE NOT NULL,
  active         BOOLEAN NOT NULL DEFAULT FALSE,
  weight_config  JSONB,
  model_variant  TEXT,
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now(),
  tenant_id      TEXT
);

CREATE TABLE IF NOT EXISTS query_performance (
  id              BIGSERIAL PRIMARY KEY,
  occurred_at     TIMESTAMPTZ DEFAULT now(),
  query_hash      TEXT,
  latency_ms      INT,
  candidate_count INT,
  clicked_chunk_ids BIGINT[],
  experiment_id   BIGINT REFERENCES scoring_experiments(id),
  metrics         JSONB,
  tenant_id       TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_logs (
  id BIGSERIAL PRIMARY KEY,
  check_name TEXT NOT NULL,
  status TEXT NOT NULL,
  details JSONB,
  checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS query_cache (
  query_hash TEXT PRIMARY KEY,
  query_embedding vector(384),
  cached_results JSONB,
  hit_count INT DEFAULT 1,
  expires_at TIMESTAMPTZ
);

-- 5. MATERIALIZED VIEWS ----------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS chunk_engagement_stats AS
SELECT
  c.id AS chunk_id,
  c.tenant_id,
  count(*) FILTER (WHERE ie.event_type = 'impression') AS impressions,
  count(*) FILTER (WHERE ie.event_type = 'click') AS clicks,
  count(*) FILTER (WHERE ie.event_type = 'upvote') AS upvotes,
  count(*) FILTER (WHERE ie.event_type = 'downvote') AS downvotes,
  AVG(ie.dwell_time_ms) FILTER (WHERE ie.dwell_time_ms IS NOT NULL) AS avg_dwell_ms,
  (count(*) FILTER (WHERE ie.event_type = 'click')::float / NULLIF(count(*) FILTER (WHERE ie.event_type = 'impression'),0)) AS ctr,
  now() AS refreshed_at
FROM chunks c
LEFT JOIN interaction_events ie ON ie.chunk_id = c.id
GROUP BY c.id, c.tenant_id;

CREATE UNIQUE INDEX IF NOT EXISTS chunk_engagement_stats_chunk_id ON chunk_engagement_stats (chunk_id);

-- 6. FUNCTIONS & TRIGGERS --------------------------------------
CREATE OR REPLACE FUNCTION refresh_chunk_engagement_stats() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY chunk_engagement_stats;
  RETURN NULL;
END;$$;

CREATE OR REPLACE FUNCTION notify_interaction_event() RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('engagement_updates', NEW.chunk_id::text);
  RETURN NEW;
END;$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER interaction_event_inserted
  AFTER INSERT ON interaction_events
  FOR EACH ROW
  EXECUTE FUNCTION notify_interaction_event();

CREATE OR REPLACE FUNCTION manage_interaction_events_partitions() RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  next_month_start timestamptz := date_trunc('month', now()) + interval '1 month';
  partition_name   text := 'interaction_events_' || to_char(next_month_start, 'YYYY_MM');
BEGIN
  IF NOT EXISTS (SELECT FROM pg_class WHERE relname = partition_name) THEN
    EXECUTE format(
      'CREATE TABLE %I PARTITION OF interaction_events FOR VALUES FROM (%L) TO (%L);',
      partition_name,
      next_month_start,
      next_month_start + interval '1 month'
    );
  END IF;
END;$$;

CREATE OR REPLACE FUNCTION batch_update_embeddings(batch_size INT DEFAULT 1000) RETURNS void LANGUAGE plpgsql AS $$
DECLARE processed INT := 0; BEGIN
  LOOP
    UPDATE chunks
       SET embedding_small = embedding_small -- placeholder (replace with actual function)
     WHERE embedding_small IS NULL
       AND id IN (SELECT id FROM chunks WHERE embedding_small IS NULL LIMIT batch_size);
    GET DIAGNOSTICS processed = ROW_COUNT;
    EXIT WHEN processed = 0;
    COMMIT;
  END LOOP;
END;$$;

-- 7. INDEXES ----------------------------------------------------
CREATE INDEX IF NOT EXISTS documents_tenant_idx ON documents(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS documents_unique_hash_latest ON documents (content_hash) WHERE latest;
CREATE INDEX IF NOT EXISTS chunks_doc_ord_idx ON chunks(document_id, ordinal);
CREATE INDEX IF NOT EXISTS chunks_tenant_idx ON chunks(tenant_id);
CREATE INDEX IF NOT EXISTS chunks_parent_chunk_id_idx ON chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS interaction_events_chunk_event_time_idx ON interaction_events (chunk_id, event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS query_performance_query_hash_idx ON query_performance(query_hash);
CREATE INDEX IF NOT EXISTS dql_check_name_time_idx ON data_quality_logs(check_name, checked_at DESC);

CREATE INDEX IF NOT EXISTS chunks_retrieval_covering_idx
  ON chunks (document_id, active, tenant_id)
  INCLUDE (text, token_count, authority_score);

CREATE INDEX IF NOT EXISTS chunks_tenant_active_embedding_idx
  ON chunks USING ivfflat (embedding_small vector_cosine_ops)
  WITH (lists=200)
  WHERE active AND tenant_id IS NOT NULL;

-- 8. PERFORMANCE & STORAGE -------------------------------------
ALTER TABLE chunks ALTER COLUMN text SET STORAGE EXTENDED;
ALTER TABLE documents ALTER COLUMN meta SET STORAGE EXTERNAL;

-- Optionally set DB-level timeouts externally (not enforced here to avoid side effects).

-- End consolidated_rag_schema_v2.sql
