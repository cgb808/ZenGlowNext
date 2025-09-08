-- ZenGlow RAG System - Consolidated Schema v2
-- Comprehensive schema for retrieval-augmented generation system
-- Includes document processing, embeddings, conversations, families, and analytics

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ANN Runtime Configuration
CREATE TABLE IF NOT EXISTS public.ann_runtime_config (
  id bigint NOT NULL DEFAULT nextval('ann_runtime_config_id_seq'::regclass),
  name text NOT NULL UNIQUE,
  metric text DEFAULT 'l2'::text,
  lists integer,
  probes integer,
  ef_search integer,
  min_candidate integer DEFAULT 50,
  max_candidate integer DEFAULT 150,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT ann_runtime_config_pkey PRIMARY KEY (id)
);

-- Artifact Schema Management
CREATE TABLE IF NOT EXISTS public.artifact_schema_versions (
  artifact_type text NOT NULL,
  version text NOT NULL,
  released_at timestamp with time zone DEFAULT now(),
  status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'deprecated'::text, 'draft'::text])),
  metadata jsonb,
  CONSTRAINT artifact_schema_versions_pkey PRIMARY KEY (artifact_type, version)
);

CREATE TABLE IF NOT EXISTS public.artifact_instances (
  id bigint NOT NULL DEFAULT nextval('artifact_instances_id_seq'::regclass),
  created_at timestamp with time zone DEFAULT now(),
  session_id uuid,
  user_id text,
  artifact_type text NOT NULL,
  schema_version text NOT NULL DEFAULT '1.0'::text,
  family_version text,
  source_file text,
  sha256 text,
  dedup_hash text,
  quality_score numeric,
  ingestion_batch_tag text,
  payload jsonb NOT NULL,
  metadata jsonb,
  CONSTRAINT artifact_instances_pkey PRIMARY KEY (id),
  CONSTRAINT artifact_instances_schema_fk FOREIGN KEY (artifact_type, schema_version) REFERENCES public.artifact_schema_versions(artifact_type, version)
);

CREATE TABLE IF NOT EXISTS public.artifact_type_stats (
  artifact_type text NOT NULL,
  last_updated timestamp with time zone DEFAULT now(),
  total_count bigint,
  last_24h_count bigint,
  target_ratio numeric,
  actual_ratio numeric,
  drift numeric,
  metadata jsonb,
  CONSTRAINT artifact_type_stats_pkey PRIMARY KEY (artifact_type)
);

-- Document Management
CREATE TABLE IF NOT EXISTS public.documents (
  id bigint NOT NULL DEFAULT nextval('documents_id_seq'::regclass),
  content_hash text NOT NULL,
  external_id text,
  source_type text NOT NULL DEFAULT 'generic'::text,
  uri text,
  version integer NOT NULL DEFAULT 1,
  latest boolean NOT NULL DEFAULT true,
  title text,
  author text,
  language text,
  meta jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT documents_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.source_documents (
  id bigint NOT NULL DEFAULT nextval('source_documents_id_seq'::regclass),
  file_path text NOT NULL UNIQUE,
  language text,
  content_hash text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  provenance jsonb,
  created_at timestamp with time zone DEFAULT now(),
  last_analyzed_at timestamp with time zone,
  CONSTRAINT source_documents_pkey PRIMARY KEY (id)
);

-- Chunk Management & Embeddings
CREATE TABLE IF NOT EXISTS public.chunks (
  id bigint NOT NULL DEFAULT nextval('chunks_id_seq'::regclass),
  document_id bigint,
  ordinal integer NOT NULL DEFAULT 0,
  text text NOT NULL,
  token_count integer,
  checksum text NOT NULL,
  embedding_small vector(384),
  embedding_dense vector(1024),
  meta jsonb DEFAULT '{}'::jsonb,
  signal_stats jsonb DEFAULT '{}'::jsonb,
  authority_score real,
  active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  parent_chunk_id bigint,
  CONSTRAINT chunks_pkey PRIMARY KEY (id),
  CONSTRAINT chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
  CONSTRAINT chunks_parent_chunk_id_fkey FOREIGN KEY (parent_chunk_id) REFERENCES public.chunks(id)
);

CREATE TABLE IF NOT EXISTS public.chunk_features (
  chunk_id bigint NOT NULL,
  feature_schema_version integer NOT NULL DEFAULT 1,
  entities jsonb,
  keyphrases jsonb,
  topics jsonb,
  sentiments jsonb,
  extra jsonb,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT chunk_features_pkey PRIMARY KEY (chunk_id),
  CONSTRAINT chunk_features_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.chunks(id)
);

CREATE TABLE IF NOT EXISTS public.code_chunks (
  id bigint NOT NULL DEFAULT nextval('code_chunks_id_seq'::regclass),
  document_id bigint,
  chunk_name text,
  start_line integer NOT NULL,
  end_line integer NOT NULL,
  code_content text NOT NULL,
  checksum text NOT NULL,
  code_embedding vector(768),
  analysis_metrics jsonb DEFAULT '{}'::jsonb,
  CONSTRAINT code_chunks_pkey PRIMARY KEY (id),
  CONSTRAINT code_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.source_documents(id)
);

-- Legacy doc_embeddings table (for compatibility)
CREATE TABLE IF NOT EXISTS public.doc_embeddings (
  id bigint NOT NULL DEFAULT nextval('doc_embeddings_id_seq'::regclass),
  source text,
  chunk text NOT NULL,
  embedding vector(384),
  created_at timestamp with time zone DEFAULT now(),
  batch_tag text,
  metadata jsonb,
  CONSTRAINT doc_embeddings_pkey PRIMARY KEY (id)
);

-- Family Management
CREATE TABLE IF NOT EXISTS public.families (
  id bigint NOT NULL DEFAULT nextval('families_id_seq'::regclass),
  family_key text UNIQUE,
  display_name text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT families_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.family_members (
  id bigint NOT NULL DEFAULT nextval('family_members_id_seq'::regclass),
  family_id bigint NOT NULL,
  given_name text,
  family_name text,
  full_name text NOT NULL,
  role text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT family_members_pkey PRIMARY KEY (id),
  CONSTRAINT family_members_family_id_fkey FOREIGN KEY (family_id) REFERENCES public.families(id)
);

CREATE TABLE IF NOT EXISTS public.member_profiles (
  member_id bigint NOT NULL,
  preferences jsonb DEFAULT '{}'::jsonb,
  traits jsonb DEFAULT '{}'::jsonb,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT member_profiles_pkey PRIMARY KEY (member_id),
  CONSTRAINT member_profiles_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.family_members(id)
);

-- Conversation Management (TimescaleDB hypertables)
CREATE TABLE IF NOT EXISTS public.conversation_sessions (
  id bigint NOT NULL DEFAULT nextval('conversation_sessions_id_seq'::regclass),
  session_id uuid DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  started_at timestamp with time zone DEFAULT now(),
  ended_at timestamp with time zone,
  metadata jsonb,
  CONSTRAINT conversation_sessions_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.conversation_events (
  time timestamp with time zone NOT NULL,
  id bigint NOT NULL DEFAULT nextval('conversation_events_id_seq'::regclass),
  session_id uuid NOT NULL,
  user_id text NOT NULL,
  role text NOT NULL,
  seq integer,
  content text NOT NULL,
  embedding vector(384),
  embedded boolean DEFAULT false,
  content_hash text,
  importance smallint,
  retention_policy text,
  metadata jsonb,
  CONSTRAINT conversation_events_pkey PRIMARY KEY (time, id)
);

CREATE TABLE IF NOT EXISTS public.conversation_summaries (
  time timestamp with time zone NOT NULL,
  id bigint NOT NULL DEFAULT nextval('conversation_summaries_id_seq'::regclass),
  user_id text NOT NULL,
  scope text NOT NULL,
  summary text NOT NULL,
  embedding vector(384),
  embedded boolean DEFAULT true,
  importance smallint,
  metadata jsonb,
  CONSTRAINT conversation_summaries_pkey PRIMARY KEY (time, id)
);

CREATE TABLE IF NOT EXISTS public.mentions_index (
  time timestamp with time zone NOT NULL,
  event_id bigint NOT NULL,
  mentioned_user text NOT NULL,
  source_user text NOT NULL,
  session_id uuid,
  context_snippet text,
  metadata jsonb,
  CONSTRAINT mentions_index_pkey PRIMARY KEY (time, event_id, mentioned_user)
);

-- Profile Management
CREATE TABLE IF NOT EXISTS public.profile_snapshots (
  time timestamp with time zone NOT NULL,
  user_id text NOT NULL,
  version integer NOT NULL,
  profile jsonb NOT NULL,
  embedding vector(384),
  CONSTRAINT profile_snapshots_pkey PRIMARY KEY (time, user_id, version)
);

-- Project Management
CREATE TABLE IF NOT EXISTS public.project_missions (
  id bigint NOT NULL DEFAULT nextval('project_missions_id_seq'::regclass),
  name text NOT NULL UNIQUE,
  description text NOT NULL,
  status text DEFAULT 'active'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT project_missions_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.project_epics (
  id bigint NOT NULL DEFAULT nextval('project_epics_id_seq'::regclass),
  mission_id bigint,
  name text NOT NULL,
  description text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT project_epics_pkey PRIMARY KEY (id),
  CONSTRAINT project_epics_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES public.project_missions(id)
);

CREATE TABLE IF NOT EXISTS public.development_log (
  id bigint NOT NULL DEFAULT nextval('development_log_id_seq'::regclass),
  epic_id bigint,
  event_type text NOT NULL,
  outcome text,
  title text NOT NULL,
  narrative text NOT NULL,
  narrative_embedding vector(384),
  author text,
  metadata jsonb DEFAULT '{}'::jsonb,
  occurred_at timestamp with time zone DEFAULT now(),
  CONSTRAINT development_log_pkey PRIMARY KEY (id),
  CONSTRAINT development_log_epic_id_fkey FOREIGN KEY (epic_id) REFERENCES public.project_epics(id)
);

CREATE TABLE IF NOT EXISTS public.log_to_chunk_link (
  log_id bigint NOT NULL,
  chunk_id bigint NOT NULL,
  CONSTRAINT log_to_chunk_link_pkey PRIMARY KEY (log_id, chunk_id),
  CONSTRAINT log_to_chunk_link_log_id_fkey FOREIGN KEY (log_id) REFERENCES public.development_log(id),
  CONSTRAINT log_to_chunk_link_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.code_chunks(id)
);

-- Model Registry & Performance
CREATE TABLE IF NOT EXISTS public.model_registry (
  id bigint NOT NULL DEFAULT nextval('model_registry_id_seq'::regclass),
  model_type text NOT NULL,
  name text NOT NULL,
  version text NOT NULL,
  artifact_ref text,
  meta jsonb,
  status text DEFAULT 'experimental'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT model_registry_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.dev_model_registry (
  id bigint NOT NULL DEFAULT nextval('dev_model_registry_id_seq'::regclass),
  model_type text NOT NULL,
  name text NOT NULL,
  version text NOT NULL,
  meta jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT dev_model_registry_pkey PRIMARY KEY (id)
);

-- Performance Analytics
CREATE TABLE IF NOT EXISTS public.query_performance (
  id bigint NOT NULL DEFAULT nextval('query_performance_id_seq'::regclass),
  occurred_at timestamp with time zone DEFAULT now(),
  query_text text,
  query_hash text,
  latency_ms integer,
  candidate_count integer,
  clicked_chunk_ids bigint[],
  metrics jsonb,
  CONSTRAINT query_performance_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.dev_query_performance (
  id bigint NOT NULL DEFAULT nextval('dev_query_performance_id_seq'::regclass),
  query_text text,
  query_embedding vector(384),
  latency_ms integer,
  results_count integer,
  metrics jsonb,
  occurred_at timestamp with time zone DEFAULT now(),
  CONSTRAINT dev_query_performance_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.interaction_events (
  id bigint NOT NULL DEFAULT nextval('interaction_events_id_seq'::regclass),
  occurred_at timestamp with time zone NOT NULL DEFAULT now(),
  user_hash text,
  session_id text,
  query_text text,
  query_vector vector(384),
  chunk_id bigint,
  event_type text NOT NULL,
  dwell_time_ms integer,
  extra jsonb,
  CONSTRAINT interaction_events_pkey PRIMARY KEY (id),
  CONSTRAINT interaction_events_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.chunks(id)
);

-- Scoring & Configuration
CREATE TABLE IF NOT EXISTS public.scoring_weights (
  id bigint NOT NULL DEFAULT nextval('scoring_weights_id_seq'::regclass),
  name text NOT NULL UNIQUE,
  active boolean NOT NULL DEFAULT false,
  weights jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  activated_at timestamp with time zone,
  notes text,
  CONSTRAINT scoring_weights_pkey PRIMARY KEY (id)
);

-- Request Processing
CREATE TABLE IF NOT EXISTS public.request_staging (
  id bigint NOT NULL DEFAULT nextval('request_staging_id_seq'::regclass),
  created_at timestamp with time zone DEFAULT now(),
  user_id text,
  voice_id text,
  source text,
  request_text text NOT NULL,
  metadata jsonb,
  auth_state text NOT NULL DEFAULT 'pending'::text,
  auth_decided_at timestamp with time zone,
  decision_reason text,
  hash_sha256 text,
  importance_score real,
  processed boolean NOT NULL DEFAULT false,
  CONSTRAINT request_staging_pkey PRIMARY KEY (id)
);

-- Memory & Deduplication
CREATE TABLE IF NOT EXISTS public.memory_ingest_dedup (
  id bigint NOT NULL DEFAULT nextval('memory_ingest_dedup_id_seq'::regclass),
  content_hash text UNIQUE,
  payload jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT memory_ingest_dedup_pkey PRIMARY KEY (id)
);

-- Tool Usage Tracking
CREATE TABLE IF NOT EXISTS public.tool_invocations (
  id bigint NOT NULL DEFAULT nextval('tool_invocations_id_seq'::regclass),
  time timestamp with time zone DEFAULT now(),
  session_id uuid,
  user_id text,
  tool_name text NOT NULL,
  wake_word text,
  intent jsonb,
  inputs jsonb,
  output jsonb,
  latency_ms integer,
  success boolean DEFAULT true,
  error_code text,
  cache_hit boolean,
  metadata jsonb,
  CONSTRAINT tool_invocations_pkey PRIMARY KEY (id)
);

-- Runtime Metrics
CREATE TABLE IF NOT EXISTS public.runtime_metrics (
  id bigint NOT NULL DEFAULT nextval('runtime_metrics_id_seq'::regclass),
  source text NOT NULL,
  metric text NOT NULL,
  value double precision,
  labels jsonb DEFAULT '{}'::jsonb,
  collected_at timestamp with time zone DEFAULT now(),
  CONSTRAINT runtime_metrics_pkey PRIMARY KEY (id)
);

-- Create hypertables for time-series data (if TimescaleDB is available)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
    PERFORM create_hypertable('conversation_events', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('conversation_summaries', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('mentions_index', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('profile_snapshots', 'time', if_not_exists => TRUE);
  END IF;
END $$;
