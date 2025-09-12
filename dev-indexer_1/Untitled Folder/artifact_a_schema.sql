-- Artifact A: Core Retrieval Schema (v1.0)
-- Requires: pgvector extension installed (CREATE EXTENSION IF NOT EXISTS vector;)
-- Safety: run in transaction for initial bootstrap.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

-- =====================
-- 1. documents
-- =====================
CREATE TABLE IF NOT EXISTS documents (
  id               BIGSERIAL PRIMARY KEY,
  tenant_id        BIGINT NOT NULL DEFAULT 0,
  external_id      TEXT,                -- upstream reference
  version          INT  NOT NULL DEFAULT 1,
  content_hash     TEXT NOT NULL,       -- stable hash of original canonical text
  title            TEXT,
  language         TEXT,
  source_type      TEXT,                -- e.g. web, manual, memory
  raw_text         TEXT,                -- optional full text (can be truncated) / or stored externally
  meta             JSONB DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_documents_hash ON documents(tenant_id, content_hash, version);
CREATE INDEX IF NOT EXISTS ix_documents_tenant_archived ON documents(tenant_id, archived) WHERE archived = FALSE;

-- =====================
-- 2. chunks (retrieval units)
-- embedding_small mandatory; embedding_dense optional; pgvector dims parametric via domain / check
-- =====================
CREATE TABLE IF NOT EXISTS chunks (
  id                BIGSERIAL PRIMARY KEY,
  tenant_id         BIGINT NOT NULL DEFAULT 0,
  document_id       BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal           INT    NOT NULL,          -- position within document
  text              TEXT   NOT NULL,
  checksum          TEXT   NOT NULL,          -- hash of chunk text
  embedding_small   vector(384),              -- adjust dimension to match EMBEDDING_MODEL_SMALL
  embedding_dense   vector(1024),             -- optional richer embedding model dimension (placeholder)
  meta              JSONB DEFAULT '{}'::jsonb,-- summary/entities/tags
  signal_stats      JSONB DEFAULT '{}'::jsonb,-- decayed engagement metrics snapshot
  authority_score   REAL,
  content_quality_score REAL,
  complexity_level  REAL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived          BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(document_id, ordinal);
CREATE UNIQUE INDEX IF NOT EXISTS ux_chunks_checksum ON chunks(tenant_id, checksum);
-- IVF / HNSW indexes (attempt HNSW; fallback to ivfflat if not supported)
DO $$
BEGIN
  EXECUTE 'CREATE INDEX IF NOT EXISTS ix_chunks_emb_small_hnsw ON chunks USING hnsw (embedding_small vector_l2_ops)';
EXCEPTION WHEN others THEN
  BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_chunks_emb_small_ivf ON chunks USING ivfflat (embedding_small vector_l2_ops) WITH (lists=100)';
  EXCEPTION WHEN others THEN NULL; END;
END$$;

DO $$
BEGIN
  EXECUTE 'CREATE INDEX IF NOT EXISTS ix_chunks_emb_dense_hnsw ON chunks USING hnsw (embedding_dense vector_l2_ops)';
EXCEPTION WHEN others THEN
  BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_chunks_emb_dense_ivf ON chunks USING ivfflat (embedding_dense vector_l2_ops) WITH (lists=100)';
  EXCEPTION WHEN others THEN NULL; END;
END$$;

-- =====================
-- 3. chunk_features (expensive enrichment cache)
-- =====================
CREATE TABLE IF NOT EXISTS chunk_features (
  chunk_id        BIGINT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
  tenant_id       BIGINT NOT NULL DEFAULT 0,
  feature_version INT    NOT NULL,
  entities        JSONB,
  topics          JSONB,
  summary         TEXT,
  category        TEXT,
  embedding_dense_ready BOOLEAN NOT NULL DEFAULT FALSE,
  extra           JSONB,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chunk_features_version ON chunk_features(feature_version);

-- =====================
-- 4. interaction_events (implicit & explicit feedback)
-- =====================
CREATE TABLE IF NOT EXISTS interaction_events (
  id           BIGSERIAL PRIMARY KEY,
  tenant_id    BIGINT NOT NULL DEFAULT 0,
  user_hash    TEXT,              -- pseudonymized user id
  query_id     TEXT,              -- client-generated correlation id
  chunk_id     BIGINT REFERENCES chunks(id) ON DELETE CASCADE,
  event_type   TEXT NOT NULL,     -- view|click|dismiss|upvote|downvote|reformulate
  weight       REAL DEFAULT 1.0,
  meta         JSONB DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_interaction_chunk ON interaction_events(chunk_id, event_type);
CREATE INDEX IF NOT EXISTS ix_interaction_query ON interaction_events(query_id);

-- =====================
-- 5. chunk_engagement_stats (materialized view)
-- =====================
CREATE MATERIALIZED VIEW IF NOT EXISTS chunk_engagement_stats AS
SELECT
  chunk_id,
  tenant_id,
  count(*)                       AS event_count,
  sum(CASE WHEN event_type='click' THEN 1 ELSE 0 END)        AS clicks,
  sum(CASE WHEN event_type='view' THEN 1 ELSE 0 END)         AS views,
  sum(CASE WHEN event_type='dismiss' THEN 1 ELSE 0 END)      AS dismisses,
  sum(CASE WHEN event_type='upvote' THEN 1 ELSE 0 END)       AS upvotes,
  sum(CASE WHEN event_type='downvote' THEN 1 ELSE 0 END)     AS downvotes,
  max(created_at)                AS last_event_at
FROM interaction_events
GROUP BY chunk_id, tenant_id;
CREATE INDEX IF NOT EXISTS ix_chunk_engagement_chunk ON chunk_engagement_stats(chunk_id);

-- =====================
-- 6. scoring_experiments
-- =====================
CREATE TABLE IF NOT EXISTS scoring_experiments (
  id            BIGSERIAL PRIMARY KEY,
  tenant_id     BIGINT NOT NULL DEFAULT 0,
  name          TEXT NOT NULL,
  active        BOOLEAN NOT NULL DEFAULT FALSE,
  weight_config JSONB,       -- pre-LTR blend weights
  model_variant TEXT,         -- post-LTR variant key
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_scoring_experiments_name ON scoring_experiments(tenant_id, name);

-- =====================
-- 7. query_performance
-- =====================
CREATE TABLE IF NOT EXISTS query_performance (
  id             BIGSERIAL PRIMARY KEY,
  tenant_id      BIGINT NOT NULL DEFAULT 0,
  query_hash     TEXT NOT NULL,
  top_k          INT  NOT NULL,
  ndcg_at_k      REAL,
  success_at_k   REAL,
  dwell_ms_avg   REAL,
  abandonment_rate REAL,
  model_variant  TEXT,
  collected_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_query_perf_hash ON query_performance(query_hash, collected_at DESC);

-- =====================
-- 8. ann_runtime_config
-- =====================
CREATE TABLE IF NOT EXISTS ann_runtime_config (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,
  probes        INT,
  ef_search     INT,
  min_candidate INT NOT NULL,
  max_candidate INT NOT NULL,
  notes         TEXT,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================
-- 9. model_registry
-- =====================
CREATE TABLE IF NOT EXISTS model_registry (
  id            BIGSERIAL PRIMARY KEY,
  model_name    TEXT NOT NULL,
  model_type    TEXT NOT NULL,    -- embedding_small|embedding_dense|ltr|prompt|contextual_lm
  version       TEXT NOT NULL,
  uri           TEXT,             -- artifact location / hash
  meta          JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  active        BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_model_registry_active ON model_registry(model_type, active) WHERE active;

-- =====================
-- 10. scoring_weights (active blend sets pre-LTR or calibration data)
-- =====================
CREATE TABLE IF NOT EXISTS scoring_weights (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL DEFAULT 0,
  name        TEXT NOT NULL,
  weights     JSONB NOT NULL,
  active      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_scoring_weights_name ON scoring_weights(tenant_id, name);

-- =====================
-- 11. feature_snapshots (for reproducibility / audit)
-- =====================
CREATE TABLE IF NOT EXISTS feature_snapshots (
  id            BIGSERIAL PRIMARY KEY,
  tenant_id     BIGINT NOT NULL DEFAULT 0,
  query_hash    TEXT NOT NULL,
  feature_schema_version INT NOT NULL,
  candidate_set_hash TEXT NOT NULL,
  features_msgpack BYTEA NOT NULL,   -- compressed serialized feature matrix
  ltr_scores      JSONB,             -- array of scores
  fusion_weights  JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_feature_snapshots_query ON feature_snapshots(query_hash, created_at DESC);

-- =====================
-- 12. RLS (pattern; actual enable step left commented to allow migration tools to manage)
-- =====================
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY p_documents_tenant ON documents USING (tenant_id = current_setting('app.current_tenant')::BIGINT);
-- Repeat for other tenant tables (chunks, interaction_events, etc.).

COMMIT;

-- Refresh helper for engagement stats
CREATE OR REPLACE FUNCTION refresh_chunk_engagement_stats() RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY chunk_engagement_stats;
END;$$;

-- End Artifact A
