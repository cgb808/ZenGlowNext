-- Development Knowledge Graph
CREATE TABLE IF NOT EXISTS source_documents (
  id BIGSERIAL PRIMARY KEY,
  file_path TEXT UNIQUE NOT NULL,
  language TEXT,
  content_hash TEXT NOT NULL,
  version INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS code_chunks (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES source_documents(id),
  chunk_name TEXT,
  start_line INT NOT NULL,
  end_line INT NOT NULL,
  code_content TEXT NOT NULL,
  code_embedding vector(768),
  analysis_metrics JSONB
);

CREATE TABLE IF NOT EXISTS development_log (
  id BIGSERIAL PRIMARY KEY,
  epic_id TEXT,
  event_type TEXT NOT NULL,
  title TEXT NOT NULL,
  narrative TEXT,
  narrative_embedding vector(768),
  outcome TEXT,
  occurred_at TIMESTAMPTZ DEFAULT now()
);

-- Research fetches
CREATE TABLE IF NOT EXISTS pubmed_fetches (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT,
  query TEXT NOT NULL,
  pmids TEXT[],
  fetch_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Memory ingestion dedup
CREATE TABLE IF NOT EXISTS memory_ingest_dedup (
  content_hash TEXT PRIMARY KEY,
  processed_at TIMESTAMPTZ DEFAULT now()
);