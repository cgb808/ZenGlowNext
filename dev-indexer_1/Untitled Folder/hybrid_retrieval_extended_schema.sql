-- Hybrid Retrieval Extended Schema (Artifact A)
-- Idempotent DDL adding advanced tables alongside legacy doc_embeddings.
-- Apply order: init.sql -> rag_core_schema.sql -> hybrid_retrieval_extended_schema.sql -> rls_policies.sql / indexes.

CREATE EXTENSION IF NOT EXISTS vector;

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
CREATE UNIQUE INDEX IF NOT EXISTS documents_unique_hash_latest
  ON documents (content_hash) WHERE latest;
CREATE INDEX IF NOT EXISTS documents_tenant_idx ON documents(tenant_id) WHERE tenant_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS chunks (
  id                 BIGSERIAL PRIMARY KEY,
  document_id        BIGINT REFERENCES documents(id) ON DELETE CASCADE,
  ordinal            INT NOT NULL DEFAULT 0,
  text               TEXT NOT NULL,
  token_count        INT,
  checksum           TEXT NOT NULL,
  embedding_small    vector(768),
  embedding_dense    vector(768),
  meta               JSONB DEFAULT '{}'::jsonb,
  signal_stats       JSONB DEFAULT '{}'::jsonb,
  authority_score    REAL,
  content_quality_score REAL,
  complexity_level   REAL,
  active             BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ DEFAULT now(),
  updated_at         TIMESTAMPTZ DEFAULT now(),
  tenant_id          TEXT
);
CREATE INDEX IF NOT EXISTS chunks_doc_ord_idx ON chunks(document_id, ordinal);
CREATE INDEX IF NOT EXISTS chunks_checksum_idx ON chunks(checksum);
CREATE INDEX IF NOT EXISTS chunks_active_idx ON chunks(active) WHERE active;
CREATE INDEX IF NOT EXISTS chunks_tenant_idx ON chunks(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS chunks_embedding_small_ivf
  ON chunks USING ivfflat (embedding_small vector_l2_ops) WITH (lists=100) WHERE active;

CREATE TABLE IF NOT EXISTS chunk_features (
  chunk_id          BIGINT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
  feature_schema_version INT NOT NULL DEFAULT 1,
  entities          JSONB,
  keyphrases        JSONB,
  topics            JSONB,
  sentiments        JSONB,
  extra             JSONB,
  updated_at        TIMESTAMPTZ DEFAULT now(),
  tenant_id         TEXT
);
CREATE INDEX IF NOT EXISTS chunk_features_tenant_idx ON chunk_features(tenant_id) WHERE tenant_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS interaction_events (
  id              BIGSERIAL PRIMARY KEY,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_hash       TEXT,
  session_id      TEXT,
  query_text      TEXT,
  query_vector    vector(768),
  chunk_id        BIGINT REFERENCES chunks(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL,
  dwell_time_ms   INT,
  extra           JSONB,
  tenant_id       TEXT
);
CREATE INDEX IF NOT EXISTS interaction_events_chunk_idx ON interaction_events(chunk_id);
CREATE INDEX IF NOT EXISTS interaction_events_event_type_idx ON interaction_events(event_type);
CREATE INDEX IF NOT EXISTS interaction_events_tenant_idx ON interaction_events(tenant_id) WHERE tenant_id IS NOT NULL;

CREATE MATERIALIZED VIEW IF NOT EXISTS chunk_engagement_stats AS
SELECT
  c.id AS chunk_id,
  c.tenant_id,
  count(*) FILTER (WHERE ie.event_type = 'impression') AS impressions,
  count(*) FILTER (WHERE ie.event_type = 'click') AS clicks,
  count(*) FILTER (WHERE ie.event_type = 'upvote') AS upvotes,
  count(*) FILTER (WHERE ie.event_type = 'downvote') AS downvotes,
  AVG(ie.dwell_time_ms) FILTER (WHERE ie.dwell_time_ms IS NOT NULL) AS avg_dwell_ms,
  CASE WHEN count(*) FILTER (WHERE ie.event_type = 'impression') > 0
       THEN (count(*) FILTER (WHERE ie.event_type = 'click')::float / NULLIF(count(*) FILTER (WHERE ie.event_type = 'impression'),0))
       ELSE 0 END AS ctr,
  now() AS refreshed_at
FROM chunks c
LEFT JOIN interaction_events ie ON ie.chunk_id = c.id
GROUP BY c.id, c.tenant_id;
CREATE INDEX IF NOT EXISTS chunk_engagement_stats_tenant_idx ON chunk_engagement_stats(tenant_id) WHERE tenant_id IS NOT NULL;

CREATE OR REPLACE FUNCTION refresh_chunk_engagement_stats() RETURNS void LANGUAGE sql AS $$
  REFRESH MATERIALIZED VIEW CONCURRENTLY chunk_engagement_stats;
$$;

CREATE TABLE IF NOT EXISTS scoring_experiments (
  id             BIGSERIAL PRIMARY KEY,
  name           TEXT UNIQUE NOT NULL,
  active         BOOLEAN NOT NULL DEFAULT FALSE,
  weight_config  JSONB,
  model_variant  TEXT,
  notes          TEXT,
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now(),
  tenant_id      TEXT
);

CREATE TABLE IF NOT EXISTS query_performance (
  id              BIGSERIAL PRIMARY KEY,
  occurred_at     TIMESTAMPTZ DEFAULT now(),
  query_text      TEXT,
  query_hash      TEXT,
  latency_ms      INT,
  candidate_count INT,
  clicked_chunk_ids BIGINT[],
  experiment_id   BIGINT REFERENCES scoring_experiments(id),
  metrics         JSONB,
  tenant_id       TEXT
);
CREATE INDEX IF NOT EXISTS query_performance_query_hash_idx ON query_performance(query_hash);

CREATE TABLE IF NOT EXISTS ann_runtime_config (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT UNIQUE NOT NULL,
  metric        TEXT DEFAULT 'l2',
  lists         INT,
  probes        INT,
  ef_search     INT,
  min_candidate INT DEFAULT 50,
  max_candidate INT DEFAULT 150,
  notes         TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_registry (
  id           BIGSERIAL PRIMARY KEY,
  model_type   TEXT NOT NULL,
  name         TEXT NOT NULL,
  version      TEXT NOT NULL,
  artifact_ref TEXT,
  meta         JSONB,
  created_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE(model_type, name, version)
);

CREATE TABLE IF NOT EXISTS scoring_weights (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT UNIQUE NOT NULL,
  active        BOOLEAN NOT NULL DEFAULT FALSE,
  weights       JSONB NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now(),
  activated_at  TIMESTAMPTZ,
  notes         TEXT
);

CREATE TABLE IF NOT EXISTS feature_snapshots (
  id             BIGSERIAL PRIMARY KEY,
  query_hash     TEXT,
  ltr_model_version TEXT,
  feature_schema_version INT,
  candidate_chunk_ids BIGINT[],
  features_matrix BYTEA,
  scores         REAL[],
  created_at     TIMESTAMPTZ DEFAULT now()
);
