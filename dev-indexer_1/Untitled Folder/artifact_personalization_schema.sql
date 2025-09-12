-- Artifact A Extension: Personalization & Identity Schema (v1.1)
-- Adds user/group context so chatbot can adapt responses per individual or shared group context.
-- Safe to apply after core Artifact A schema. Wrap in transaction for bootstrap.

BEGIN;

-- ================
-- users (actors)
-- ================
CREATE TABLE IF NOT EXISTS users (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL DEFAULT 0,
  external_id TEXT,                 -- upstream auth/user directory id
  display_name TEXT,
  handle      TEXT,
  email       TEXT,
  status      TEXT DEFAULT 'active',
  locale      TEXT,
  timezone    TEXT,
  meta        JSONB DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_tenant ON users(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_external ON users(tenant_id, external_id) WHERE external_id IS NOT NULL;

-- ================
-- groups
-- ================
CREATE TABLE IF NOT EXISTS groups (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL DEFAULT 0,
  name        TEXT NOT NULL,
  description TEXT,
  meta        JSONB DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_groups_name ON groups(tenant_id, name);

-- ================
-- group_memberships
-- ================
CREATE TABLE IF NOT EXISTS group_memberships (
  user_id   BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  group_id  BIGINT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  role      TEXT DEFAULT 'member',
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, group_id)
);
CREATE INDEX IF NOT EXISTS ix_group_memberships_group ON group_memberships(group_id);

-- ================
-- user_persona_prefs (preferred persona / system style per user)
-- ================
CREATE TABLE IF NOT EXISTS user_persona_prefs (
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  persona_key TEXT NOT NULL,
  weight      REAL DEFAULT 1.0,
  active      BOOLEAN NOT NULL DEFAULT TRUE,
  meta        JSONB DEFAULT '{}'::jsonb,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, persona_key)
);

-- ================
-- conversation_sessions (maps requests to identity context)
-- ================
CREATE TABLE IF NOT EXISTS conversation_sessions (
  id               BIGSERIAL PRIMARY KEY,
  tenant_id        BIGINT NOT NULL DEFAULT 0,
  session_token    TEXT NOT NULL UNIQUE,
  user_id          BIGINT REFERENCES users(id) ON DELETE SET NULL,
  group_id         BIGINT REFERENCES groups(id) ON DELETE SET NULL,
  persona_key      TEXT,         -- explicit persona override
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_interaction TIMESTAMPTZ NOT NULL DEFAULT now(),
  active           BOOLEAN NOT NULL DEFAULT TRUE,
  meta             JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_convo_sessions_user ON conversation_sessions(user_id, active);

-- ================
-- user_embeddings (optional personalization vectors)
-- ================
CREATE TABLE IF NOT EXISTS user_embeddings (
  user_id         BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  embedding_small vector(384),
  embedding_dense vector(1024),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ================
-- user_traits (flexible key-value traits / preferences)
-- ================
CREATE TABLE IF NOT EXISTS user_traits (
  user_id   BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  trait_key TEXT NOT NULL,
  trait_val TEXT,
  confidence REAL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, trait_key)
);

-- ================
-- user_memory_items (structured memory separate from generic chunks)
-- (Current streaming router still writes to doc_embeddings for backward compatibility; migration planned)
-- ================
CREATE TABLE IF NOT EXISTS user_memory_items (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL DEFAULT 0,
  user_id     BIGINT REFERENCES users(id) ON DELETE CASCADE,
  group_id    BIGINT REFERENCES groups(id) ON DELETE SET NULL,
  visibility  TEXT NOT NULL DEFAULT 'user',  -- user|group|global
  content     TEXT NOT NULL,
  embedding_small vector(384),
  meta        JSONB DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at  TIMESTAMPTZ,
  archived    BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_user_memory_user ON user_memory_items(user_id, visibility) WHERE archived=FALSE;
CREATE INDEX IF NOT EXISTS ix_user_memory_group ON user_memory_items(group_id) WHERE group_id IS NOT NULL AND archived=FALSE;
-- ANN index for memory (optional; fallback to seq):
DO $$
BEGIN
  EXECUTE 'CREATE INDEX IF NOT EXISTS ix_user_memory_emb_small_hnsw ON user_memory_items USING hnsw (embedding_small vector_l2_ops)';
EXCEPTION WHEN others THEN
  BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_user_memory_emb_small_ivf ON user_memory_items USING ivfflat (embedding_small vector_l2_ops) WITH (lists=50)';
  EXCEPTION WHEN others THEN NULL; END;
END$$;

COMMIT;

-- End Personalization Extension
