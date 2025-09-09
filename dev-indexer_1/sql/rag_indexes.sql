-- ZenGlow RAG System - Indexes and ANN setup
-- Safe, idempotent indexes to complement consolidated_rag_schema_v2.sql
-- Notes:
-- - Uses pg_trgm for trigram GIN/GIST where helpful
-- - For pgvector columns, attempts HNSW first, falls back to IVFFlat if unsupported
-- - Default metric opclass is cosine (vector_cosine_ops); adjust if you use l2/ip

-- Helpful extensions (idempotent)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ========== Helper: Create ANN index with HNSW→IVFFlat fallback ==========
-- We avoid creating a persistent helper function; instead, we inline DO blocks per index.

-- ========================== documents ==========================
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON public.documents (content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_external_id ON public.documents (external_id);
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON public.documents (source_type);
CREATE INDEX IF NOT EXISTS idx_documents_latest ON public.documents (latest);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents (created_at DESC);
-- JSONB metadata search
CREATE INDEX IF NOT EXISTS idx_documents_meta_gin ON public.documents USING gin (meta);
-- Trigram search on title/author (optional, sizable). Enable if needed.
CREATE INDEX IF NOT EXISTS idx_documents_title_trgm ON public.documents USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_author_trgm ON public.documents USING gin (author gin_trgm_ops);

-- ======================= source_documents ======================
CREATE INDEX IF NOT EXISTS idx_source_documents_content_hash ON public.source_documents (content_hash);
CREATE INDEX IF NOT EXISTS idx_source_documents_last_analyzed_at ON public.source_documents (last_analyzed_at);

-- ============================ chunks ===========================
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON public.chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_checksum ON public.chunks (checksum);
CREATE INDEX IF NOT EXISTS idx_chunks_active ON public.chunks (active);
CREATE INDEX IF NOT EXISTS idx_chunks_updated_at ON public.chunks (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_parent_chunk_id ON public.chunks (parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_authority_score ON public.chunks (authority_score DESC);
-- JSONB search
CREATE INDEX IF NOT EXISTS idx_chunks_meta_gin ON public.chunks USING gin (meta);
CREATE INDEX IF NOT EXISTS idx_chunks_signal_stats_gin ON public.chunks USING gin (signal_stats);

-- ANN for embedding_small (384)
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_chunks_embedding_small_ann ON public.chunks USING hnsw (embedding_small vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_chunks_embedding_small_ann ON public.chunks USING ivfflat (embedding_small vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

-- ANN for embedding_dense (1024)
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_chunks_embedding_dense_ann ON public.chunks USING hnsw (embedding_dense vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_chunks_embedding_dense_ann ON public.chunks USING ivfflat (embedding_dense vector_cosine_ops) WITH (lists=200)';
	END;
END$$;

-- ======================== chunk_features =======================
CREATE INDEX IF NOT EXISTS idx_chunk_features_updated_at ON public.chunk_features (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunk_features_entities_gin ON public.chunk_features USING gin (entities);
CREATE INDEX IF NOT EXISTS idx_chunk_features_keyphrases_gin ON public.chunk_features USING gin (keyphrases);
CREATE INDEX IF NOT EXISTS idx_chunk_features_topics_gin ON public.chunk_features USING gin (topics);
CREATE INDEX IF NOT EXISTS idx_chunk_features_sentiments_gin ON public.chunk_features USING gin (sentiments);
CREATE INDEX IF NOT EXISTS idx_chunk_features_extra_gin ON public.chunk_features USING gin (extra);

-- ========================= code_chunks =========================
CREATE INDEX IF NOT EXISTS idx_code_chunks_document_id ON public.code_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_code_chunks_name ON public.code_chunks (chunk_name);
CREATE INDEX IF NOT EXISTS idx_code_chunks_checksum ON public.code_chunks (checksum);
-- Trigram for code content search (can be heavy; enable if needed)
CREATE INDEX IF NOT EXISTS idx_code_chunks_content_trgm ON public.code_chunks USING gin (code_content gin_trgm_ops);

-- ANN for code_embedding (768)
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_code_chunks_code_embedding_ann ON public.code_chunks USING hnsw (code_embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_code_chunks_code_embedding_ann ON public.code_chunks USING ivfflat (code_embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

-- ======================== doc_embeddings =======================
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_source ON public.doc_embeddings (source);
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_created_at ON public.doc_embeddings (created_at DESC);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_doc_embeddings_embedding_ann ON public.doc_embeddings USING hnsw (embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_doc_embeddings_embedding_ann ON public.doc_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

-- ========================== families ===========================
CREATE INDEX IF NOT EXISTS idx_family_members_family_id ON public.family_members (family_id);
CREATE INDEX IF NOT EXISTS idx_family_members_full_name ON public.family_members (full_name);
CREATE INDEX IF NOT EXISTS idx_family_members_role ON public.family_members (role);

-- ===================== conversation_* (TS) =====================
-- Secondary indexes helpful on hypertables; Timescale will manage chunking by time
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_started ON public.conversation_sessions (user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_session_id ON public.conversation_sessions (session_id);

CREATE INDEX IF NOT EXISTS idx_conversation_events_session_time ON public.conversation_events (session_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_events_user_time ON public.conversation_events (user_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_events_role_time ON public.conversation_events (role, time DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_events_content_trgm ON public.conversation_events USING gin (content gin_trgm_ops);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_conversation_events_embedding_ann ON public.conversation_events USING hnsw (embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_conversation_events_embedding_ann ON public.conversation_events USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_time ON public.conversation_summaries (user_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_scope_time ON public.conversation_summaries (scope, time DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_summary_trgm ON public.conversation_summaries USING gin (summary gin_trgm_ops);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_conversation_summaries_embedding_ann ON public.conversation_summaries USING hnsw (embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_conversation_summaries_embedding_ann ON public.conversation_summaries USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

CREATE INDEX IF NOT EXISTS idx_mentions_index_mentioned_time ON public.mentions_index (mentioned_user, time DESC);
CREATE INDEX IF NOT EXISTS idx_mentions_index_source_time ON public.mentions_index (source_user, time DESC);

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_user_time ON public.profile_snapshots (user_id, time DESC);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_profile_snapshots_embedding_ann ON public.profile_snapshots USING hnsw (embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_profile_snapshots_embedding_ann ON public.profile_snapshots USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

-- ===================== project_* and logs ======================
CREATE INDEX IF NOT EXISTS idx_project_epics_mission_id ON public.project_epics (mission_id);
CREATE INDEX IF NOT EXISTS idx_development_log_epic_id ON public.development_log (epic_id);
CREATE INDEX IF NOT EXISTS idx_development_log_event_type ON public.development_log (event_type);
CREATE INDEX IF NOT EXISTS idx_development_log_occurred_at ON public.development_log (occurred_at DESC);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_development_log_narrative_embedding_ann ON public.development_log USING hnsw (narrative_embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_development_log_narrative_embedding_ann ON public.development_log USING ivfflat (narrative_embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

CREATE INDEX IF NOT EXISTS idx_log_to_chunk_link_chunk_id ON public.log_to_chunk_link (chunk_id);

-- =================== model registries and perf =================
CREATE UNIQUE INDEX IF NOT EXISTS uq_model_registry_name_version ON public.model_registry (model_type, name, version);
CREATE INDEX IF NOT EXISTS idx_model_registry_status ON public.model_registry (status);

CREATE INDEX IF NOT EXISTS idx_dev_model_registry_name_version ON public.dev_model_registry (model_type, name, version);

CREATE INDEX IF NOT EXISTS idx_query_performance_occurred_at ON public.query_performance (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_performance_hash ON public.query_performance (query_hash);

CREATE INDEX IF NOT EXISTS idx_dev_query_performance_occurred_at ON public.dev_query_performance (occurred_at DESC);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_dev_query_performance_query_embedding_ann ON public.dev_query_performance USING hnsw (query_embedding vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_dev_query_performance_query_embedding_ann ON public.dev_query_performance USING ivfflat (query_embedding vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

-- ======================== interaction_events ===================
CREATE INDEX IF NOT EXISTS idx_interaction_events_occurred_at ON public.interaction_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_events_user_hash ON public.interaction_events (user_hash);
CREATE INDEX IF NOT EXISTS idx_interaction_events_session_id ON public.interaction_events (session_id);
CREATE INDEX IF NOT EXISTS idx_interaction_events_event_type ON public.interaction_events (event_type);
CREATE INDEX IF NOT EXISTS idx_interaction_events_chunk_id ON public.interaction_events (chunk_id);
DO $$
BEGIN
	BEGIN
		EXECUTE 'CREATE INDEX idx_interaction_events_query_vector_ann ON public.interaction_events USING hnsw (query_vector vector_cosine_ops)';
	EXCEPTION WHEN others THEN
		EXECUTE 'CREATE INDEX IF NOT EXISTS idx_interaction_events_query_vector_ann ON public.interaction_events USING ivfflat (query_vector vector_cosine_ops) WITH (lists=100)';
	END;
END$$;

-- ======================= scoring_weights =======================
CREATE INDEX IF NOT EXISTS idx_scoring_weights_active ON public.scoring_weights (active);
CREATE INDEX IF NOT EXISTS idx_scoring_weights_created_at ON public.scoring_weights (created_at DESC);

-- ======================= request_staging =======================
CREATE INDEX IF NOT EXISTS idx_request_staging_created_at ON public.request_staging (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_request_staging_processed ON public.request_staging (processed);
CREATE INDEX IF NOT EXISTS idx_request_staging_auth_state ON public.request_staging (auth_state);
CREATE UNIQUE INDEX IF NOT EXISTS uq_request_staging_hash_sha256 ON public.request_staging (hash_sha256) WHERE hash_sha256 IS NOT NULL;

-- ===================== memory_ingest_dedup =====================
CREATE INDEX IF NOT EXISTS idx_memory_ingest_dedup_created_at ON public.memory_ingest_dedup (created_at DESC);

-- ======================= tool_invocations ======================
CREATE INDEX IF NOT EXISTS idx_tool_invocations_time ON public.tool_invocations (time DESC);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_session_time ON public.tool_invocations (session_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_user_time ON public.tool_invocations (user_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool_name ON public.tool_invocations (tool_name);

-- ======================= runtime_metrics =======================
CREATE INDEX IF NOT EXISTS idx_runtime_metrics_source_metric_time ON public.runtime_metrics (source, metric, collected_at DESC);

-- ======================= artifact_* tables =====================
CREATE INDEX IF NOT EXISTS idx_artifact_instances_type ON public.artifact_instances (artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_schema_version ON public.artifact_instances (schema_version);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_session_id ON public.artifact_instances (session_id);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_user_id ON public.artifact_instances (user_id);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_created_at ON public.artifact_instances (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_sha256 ON public.artifact_instances (sha256);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_dedup_hash ON public.artifact_instances (dedup_hash);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_payload_gin ON public.artifact_instances USING gin (payload);
CREATE INDEX IF NOT EXISTS idx_artifact_instances_metadata_gin ON public.artifact_instances USING gin (metadata);

-- ======================= housekeeping ==========================
-- Optional: analyze tables after bulk index creation for better plans
-- DO $$ BEGIN PERFORM pg_stat_statements_reset(); END $$; -- if extension is present

