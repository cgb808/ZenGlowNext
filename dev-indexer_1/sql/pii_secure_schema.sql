-- Baseline PII / sensitive data schema (initial normal security posture).
-- Required for UUID and token generation helpers
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- Do NOT enable strict RLS / encryption yet; this is a staging design.
-- Future: add column-level encryption (pgcrypto or external KMS) + masking views.

CREATE TABLE IF NOT EXISTS pii_identity_profiles (
    id UUID PRIMARY KEY,
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    subject_type TEXT NOT NULL,                 -- person|guardian|staff|other
    subject_ref TEXT NOT NULL,                  -- foreign id (e.g. family_people.id)
    legal_name TEXT,                            -- [PII]
    preferred_name TEXT,                        -- [PII]
    birthdate DATE,                             -- [PII]
    email TEXT,                                 -- [PII][EMAIL]
    phone TEXT,                                 -- [PII][PHONE]
    address_line1 TEXT,                         -- [PII][ADDRESS]
    address_line2 TEXT,                         -- [PII][ADDRESS]
    city TEXT,                                  -- [PII][ADDRESS]
    region TEXT,                                -- [PII][ADDRESS]
    postal_code TEXT,                           -- [PII][ADDRESS]
    country TEXT,                               -- [PII][ADDRESS]
    meta JSONB DEFAULT '{}'::jsonb              -- misc (avoid freeform raw PII here)
);

COMMENT ON TABLE pii_identity_profiles IS 'Identity profile (stage) [PII]';
COMMENT ON COLUMN pii_identity_profiles.legal_name IS 'Legal full name [PII][NAME]';
COMMENT ON COLUMN pii_identity_profiles.preferred_name IS 'Preferred name [PII][NAME]';
COMMENT ON COLUMN pii_identity_profiles.birthdate IS 'Date of birth [PII][DOB]';
COMMENT ON COLUMN pii_identity_profiles.email IS 'Email address [PII][EMAIL]';
COMMENT ON COLUMN pii_identity_profiles.phone IS 'Phone number [PII][PHONE]';
COMMENT ON COLUMN pii_identity_profiles.address_line1 IS 'Address line 1 [PII][ADDRESS]';

CREATE INDEX IF NOT EXISTS idx_pii_identity_subject ON pii_identity_profiles(subject_type, subject_ref);

-- Access audit (lightweight) – stores only metadata, not raw values.
CREATE TABLE IF NOT EXISTS pii_access_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor TEXT NOT NULL,               -- app user / service principal
    action TEXT NOT NULL,              -- read|update|export
    subject_type TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    field_list TEXT,                   -- comma-separated columns touched
    reason TEXT,                       -- optional justification code
    meta JSONB DEFAULT '{}'::jsonb
);
COMMENT ON TABLE pii_access_log IS 'PII access audit trail [SENSITIVE]';
CREATE INDEX IF NOT EXISTS idx_pii_access_actor_ts ON pii_access_log(actor, ts DESC);
CREATE INDEX IF NOT EXISTS idx_pii_access_subject_ts ON pii_access_log(subject_type, subject_ref, ts DESC);

-- ============================
-- RLS & Guardianship scaffolding
-- ============================
-- Assumes application sets:
--   SELECT set_config('app.user_id', '<identity_uuid>', true);
--   SELECT set_config('app.role', '<role>', true); -- e.g., 'dev', 'user'

-- Guardianship links: parent/guardian can access child identity
CREATE TABLE IF NOT EXISTS pii_guardianship (
        guardian_id UUID NOT NULL REFERENCES pii_identity_profiles(id) ON DELETE CASCADE,
        ward_id     UUID NOT NULL REFERENCES pii_identity_profiles(id) ON DELETE CASCADE,
        relation    TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (guardian_id, ward_id)
);

ALTER TABLE pii_identity_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE pii_access_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE pii_token_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE pii_guardianship ENABLE ROW LEVEL SECURITY;

-- Helper: checks if session user is dev
CREATE OR REPLACE FUNCTION app_is_dev() RETURNS BOOLEAN LANGUAGE sql AS $$
    SELECT current_setting('app.role', true) = 'dev'
$$;

-- Helper: session identity uuid
CREATE OR REPLACE FUNCTION app_identity_uuid() RETURNS UUID LANGUAGE sql AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

-- Policies: pii_identity_profiles
DROP POLICY IF EXISTS pii_self ON pii_identity_profiles;
CREATE POLICY pii_self ON pii_identity_profiles
FOR SELECT USING (
    app_is_dev() OR id = app_identity_uuid() OR EXISTS (
        SELECT 1 FROM pii_guardianship g WHERE g.guardian_id = app_identity_uuid() AND g.ward_id = pii_identity_profiles.id
    )
);

-- Policies: pii_token_map (allow read of own tokens; dev full)
DROP POLICY IF EXISTS token_self ON pii_token_map;
CREATE POLICY token_self ON pii_token_map
FOR SELECT USING (
    app_is_dev() OR identity_id = app_identity_uuid()
);

-- Policies: pii_access_log (dev read, and actors can see their own entries)
DROP POLICY IF EXISTS accesslog_read ON pii_access_log;
CREATE POLICY accesslog_read ON pii_access_log
FOR SELECT USING (
    app_is_dev() OR actor = current_setting('app.actor', true)
);

-- =============================================
-- Pseudonymous Token Map (PII vault boundary)
-- =============================================
-- Maps public-facing tokens to internal PII profile IDs with rotation support
CREATE TABLE IF NOT EXISTS pii_token_map (
    token           TEXT PRIMARY KEY,              -- pseudonymous key used across data plane
    identity_id     UUID NOT NULL REFERENCES pii_identity_profiles(id) ON DELETE CASCADE,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until     TIMESTAMPTZ,                  -- rotate tokens by setting expiration
    purpose         TEXT,                          -- login|data_link|edge_function|other
    meta            JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_token_identity ON pii_token_map(identity_id);
CREATE INDEX IF NOT EXISTS ix_token_valid_window ON pii_token_map(valid_from, valid_until);

-- ============================
-- Token helper functions
-- ============================

-- Mint a new token for an identity with optional purpose and TTL (days). If ttl_days is null, no expiry is set.
CREATE OR REPLACE FUNCTION mint_user_token(identity_uuid UUID, token_purpose TEXT DEFAULT 'data_link', ttl_days INTEGER DEFAULT NULL)
RETURNS TEXT
LANGUAGE plpgsql AS $$
DECLARE
    new_token TEXT;
BEGIN
    -- Generate a URL-safe token (base64 without padding) using gen_random_bytes
    new_token := replace(encode(gen_random_bytes(24), 'base64'), '=', '');
    INSERT INTO pii_token_map(token, identity_id, issued_at, valid_from, valid_until, purpose)
    VALUES (new_token, identity_uuid, now(), now(), CASE WHEN ttl_days IS NULL THEN NULL ELSE now() + make_interval(days => ttl_days) END, token_purpose);
    RETURN new_token;
END;
$$;

-- Resolve: get identity UUID for a valid token at current time
CREATE OR REPLACE FUNCTION resolve_identity(token_in TEXT)
RETURNS UUID
LANGUAGE sql AS $$
    SELECT identity_id
    FROM pii_token_map
    WHERE token = token_in
      AND (valid_from IS NULL OR valid_from <= now())
      AND (valid_until IS NULL OR valid_until >= now())
    LIMIT 1;
$$;

-- Rotate: expire existing token and mint new one atomically
CREATE OR REPLACE FUNCTION rotate_user_token(token_in TEXT, ttl_days INTEGER DEFAULT NULL)
RETURNS TEXT
LANGUAGE plpgsql AS $$
DECLARE
    ident UUID;
    new_tok TEXT;
BEGIN
    SELECT identity_id INTO ident FROM pii_token_map WHERE token = token_in LIMIT 1;
    IF ident IS NULL THEN
        RAISE EXCEPTION 'token not found';
    END IF;
    UPDATE pii_token_map SET valid_until = now() WHERE token = token_in AND (valid_until IS NULL OR valid_until > now());
    new_tok := mint_user_token(ident, 'rotation', ttl_days);
    RETURN new_tok;
END;
$$;


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

-- Optional: TimescaleDB hypertables for high-write tables (guarded)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='timescaledb') THEN
        -- Conversation sessions time-based access patterns
        PERFORM create_hypertable('conversation_sessions','started_at', if_not_exists=>TRUE);
        -- Tag assignments (created_at)
        PERFORM create_hypertable('tag_assignments','created_at', if_not_exists=>TRUE);
        -- Finetune examples (created_at)
        PERFORM create_hypertable('finetune_examples','created_at', if_not_exists=>TRUE);
        -- User memory items (created_at)
        PERFORM create_hypertable('user_memory_items','created_at', if_not_exists=>TRUE);
    END IF;
END$$;
