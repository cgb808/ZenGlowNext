-- Artifact Personalization Tags Extension (v1.2)
-- Adds flexible tagging and scoping metadata to support fine-tuning datasets (family jokes, historical events, individual traits).

BEGIN;

-- Generic tag registry (avoids duplicates, allows aliasing later)
CREATE TABLE IF NOT EXISTS tags (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL DEFAULT 0,
  tag         TEXT NOT NULL,
  category    TEXT,                 -- e.g. persona, inside_joke, event, place, trait
  description TEXT,
  meta        JSONB DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, tag)
);

-- Tag assignments to retrieval units (chunk) OR user memory items (soft polymorphism)
CREATE TABLE IF NOT EXISTS tag_assignments (
  id             BIGSERIAL PRIMARY KEY,
  tenant_id      BIGINT NOT NULL DEFAULT 0,
  tag_id         BIGINT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  chunk_id       BIGINT REFERENCES chunks(id) ON DELETE CASCADE,
  user_memory_id BIGINT REFERENCES user_memory_items(id) ON DELETE CASCADE,
  user_id        BIGINT REFERENCES users(id) ON DELETE SET NULL, -- who added it
  source         TEXT,       -- manual|auto|import
  confidence     REAL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ( (chunk_id IS NOT NULL)::int + (user_memory_id IS NOT NULL)::int = 1 )
);
CREATE INDEX IF NOT EXISTS ix_tag_assign_chunk ON tag_assignments(chunk_id, tag_id) WHERE chunk_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_tag_assign_mem ON tag_assignments(user_memory_id, tag_id) WHERE user_memory_id IS NOT NULL;

-- Optional fine-tune example linkage (store canonical training pairs referencing source memories/chunks)
CREATE TABLE IF NOT EXISTS finetune_examples (
  id           BIGSERIAL PRIMARY KEY,
  tenant_id    BIGINT NOT NULL DEFAULT 0,
  user_id      BIGINT REFERENCES users(id) ON DELETE SET NULL,  -- originating speaker/author
  group_id     BIGINT REFERENCES groups(id) ON DELETE SET NULL,
  prompt       TEXT NOT NULL,
  response     TEXT NOT NULL,
  meta         JSONB DEFAULT '{}'::jsonb,
  source_chunk_ids BIGINT[],
  source_memory_ids BIGINT[],
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  tags         TEXT[]  -- denormalized tag snapshot for faster export filtering
);
CREATE INDEX IF NOT EXISTS ix_finetune_examples_user ON finetune_examples(user_id, created_at DESC);

COMMIT;

-- End Tags Extension
