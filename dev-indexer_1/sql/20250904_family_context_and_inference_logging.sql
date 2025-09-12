-- 20250904_family_context_and_inference_logging.sql
-- Family context persistence + inference logging + RLS policies.
-- Idempotent (CREATE IF NOT EXISTS / CREATE POLICY names stable / CREATE VIEW OR REPLACE).

BEGIN;

-- Core tables -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS family_people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INT NOT NULL,
    grade_band TEXT NOT NULL,
    last_name TEXT,
    birthdate DATE,
    household_id TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_ts TIMESTAMPTZ DEFAULT now(),
    updated_ts TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS family_relationships (
    guardian_id TEXT NOT NULL REFERENCES family_people(id) ON DELETE CASCADE,
    child_id TEXT NOT NULL REFERENCES family_people(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'guardian',
    legal BOOLEAN NOT NULL DEFAULT TRUE,
    created_ts TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (guardian_id, child_id, kind)
);

CREATE TABLE IF NOT EXISTS family_artifacts (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    content_ref TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_ts TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS family_health_metrics (
    id BIGSERIAL PRIMARY KEY,
    entity_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value_text TEXT,
    value_num DOUBLE PRECISION,
    unit TEXT,
    ts TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_family_artifacts_entity ON family_artifacts(entity_id);
CREATE INDEX IF NOT EXISTS idx_family_artifacts_tags ON family_artifacts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_family_health_entity_metric ON family_health_metrics(entity_id, metric, ts DESC);

-- RLS enable ------------------------------------------------------------------
ALTER TABLE family_people ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_health_metrics ENABLE ROW LEVEL SECURITY;

-- Ensure admin role exists for policies
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'family_admin'
    ) THEN
        EXECUTE 'CREATE ROLE family_admin';
    END IF;
END $$;

-- Policies (idempotent: drop then create ensures desired definition if changed)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_people' AND policyname='people_admin_all'
    ) THEN
        CREATE POLICY people_admin_all ON family_people FOR ALL TO family_admin USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_people' AND policyname='people_self_select'
    ) THEN
        CREATE POLICY people_self_select ON family_people FOR SELECT USING (id = current_setting('app.current_user', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_people' AND policyname='people_self_update'
    ) THEN
        CREATE POLICY people_self_update ON family_people FOR UPDATE USING (id = current_setting('app.current_user', true)) WITH CHECK (id = current_setting('app.current_user', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_artifacts' AND policyname='artifacts_admin_all'
    ) THEN
        CREATE POLICY artifacts_admin_all ON family_artifacts FOR ALL TO family_admin USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_artifacts' AND policyname='artifacts_owner_select'
    ) THEN
        CREATE POLICY artifacts_owner_select ON family_artifacts FOR SELECT USING (entity_id = current_setting('app.current_user', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_artifacts' AND policyname='artifacts_owner_insert'
    ) THEN
        CREATE POLICY artifacts_owner_insert ON family_artifacts FOR INSERT WITH CHECK (entity_id = current_setting('app.current_user', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_health_metrics' AND policyname='health_admin_all'
    ) THEN
        CREATE POLICY health_admin_all ON family_health_metrics FOR ALL TO family_admin USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_health_metrics' AND policyname='health_owner_select'
    ) THEN
        CREATE POLICY health_owner_select ON family_health_metrics FOR SELECT USING (entity_id = current_setting('app.current_user', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_health_metrics' AND policyname='health_owner_insert'
    ) THEN
        CREATE POLICY health_owner_insert ON family_health_metrics FOR INSERT WITH CHECK (entity_id = current_setting('app.current_user', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_relationships' AND policyname='rel_admin_all'
    ) THEN
        CREATE POLICY rel_admin_all ON family_relationships FOR ALL TO family_admin USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename='family_relationships' AND policyname='rel_guardian_view'
    ) THEN
        CREATE POLICY rel_guardian_view ON family_relationships FOR SELECT USING (
            guardian_id = current_setting('app.current_user', true)
            OR child_id = current_setting('app.current_user', true)
        );
    END IF;
END $$;

-- Masked view -----------------------------------------------------------------
CREATE OR REPLACE VIEW family_people_masked AS
SELECT
    id,
    name,
    age,
    grade_band,
    last_name,
    CASE
        WHEN (SELECT current_setting('app.current_user', true)) = id
          OR pg_has_role(current_user, 'family_admin', 'USAGE') THEN birthdate
        ELSE NULL
    END AS birthdate,
    household_id,
    meta,
    created_ts,
    updated_ts
FROM family_people;

-- Inference logging ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_inference_events (
    id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_name TEXT NOT NULL,
    user_id TEXT,
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    avg_logprob REAL,
    entropy REAL,
    top1_prob REAL,
    decision TEXT,
    meta JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS model_inference_token_stats (
    event_id UUID REFERENCES model_inference_events(id) ON DELETE CASCADE,
    position INT NOT NULL,
    token TEXT NOT NULL,
    logprob REAL NOT NULL,
    is_generated BOOLEAN NOT NULL,
    PRIMARY KEY (event_id, position)
);

CREATE INDEX IF NOT EXISTS idx_infer_events_model_ts ON model_inference_events(model_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_infer_events_decision_ts ON model_inference_events(decision, ts DESC);

-- Convenience views -------------------------------------------------------
CREATE OR REPLACE VIEW v_inference_recent AS
SELECT id, ts, model_name, decision, avg_logprob, entropy, top1_prob, latency_ms,
       prompt_tokens, completion_tokens
FROM model_inference_events
ORDER BY ts DESC
LIMIT 200;

CREATE OR REPLACE VIEW v_inference_hourly_agg AS
SELECT date_trunc('hour', ts) AS hour_bucket,
       model_name,
       count(*) AS events,
       avg(avg_logprob) AS avg_avg_logprob,
       avg(entropy) AS avg_entropy,
       avg(top1_prob) AS avg_top1_prob,
       avg(latency_ms) AS avg_latency_ms,
       sum(prompt_tokens) AS total_prompt_tokens,
       sum(completion_tokens) AS total_completion_tokens,
       jsonb_object_agg(decision, decision_count) AS decisions
FROM (
    SELECT *, 1 AS decision_count FROM model_inference_events
    WHERE ts > now() - interval '24 hours'
) s
GROUP BY 1,2
ORDER BY hour_bucket DESC, model_name;

COMMIT;
