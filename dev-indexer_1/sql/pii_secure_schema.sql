-- Baseline PII / sensitive data schema (initial normal security posture).
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

-- NOTE: RLS / masking not yet enabled. Add once operational requirements finalized.
-- Placeholder for future enablement:
-- ALTER TABLE pii_identity_profiles ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY pii_read_self ON pii_identity_profiles FOR SELECT USING (true);
