-- Core RAG table
CREATE TABLE IF NOT EXISTS doc_embeddings (
  id BIGSERIAL PRIMARY KEY,
  source TEXT,
  chunk TEXT NOT NULL,
  embedding vector(768),
  batch_tag TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Supporting enum for chunk roles
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chunk_role') THEN
    CREATE TYPE chunk_role AS ENUM ('standalone', 'introduction', 'conclusion', 'section', 'code', 'appendix');
  END IF;
END $$;

-- Supporting documents table (minimal)
CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  source TEXT,
  title TEXT,
  checksum TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Advanced chunks table
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_name='chunks'
  ) THEN
    CREATE TABLE chunks (
      id BIGSERIAL PRIMARY KEY,
      document_id BIGINT REFERENCES documents(id),
      parent_chunk_id BIGINT REFERENCES chunks(id),
      role chunk_role DEFAULT 'standalone',
      ordinal INT DEFAULT 0,
      text TEXT NOT NULL,
      token_count INT,
      checksum TEXT NOT NULL,
      embedding_small vector(384),
      embedding_dense vector(768),
      authority_score REAL,
      active BOOLEAN DEFAULT TRUE,
      tenant_id TEXT,
      meta JSONB DEFAULT '{}'::jsonb
    );
  END IF;
END $$;