-- Row Level Security & masking configuration for family context.
-- Assumes app sets: SET LOCAL app.current_user = '<person_id>' per request.
-- Admin (global) users via role: family_admin (grant to charles, nancy).

ALTER TABLE family_people ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_health_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY people_admin_all ON family_people FOR ALL TO family_admin USING (true) WITH CHECK (true);
CREATE POLICY people_self_select ON family_people FOR SELECT USING (id = current_setting('app.current_user', true));
CREATE POLICY people_self_update ON family_people FOR UPDATE USING (id = current_setting('app.current_user', true)) WITH CHECK (id = current_setting('app.current_user', true));

CREATE POLICY artifacts_admin_all ON family_artifacts FOR ALL TO family_admin USING (true) WITH CHECK (true);
CREATE POLICY artifacts_owner_select ON family_artifacts FOR SELECT USING (entity_id = current_setting('app.current_user', true));
CREATE POLICY artifacts_owner_insert ON family_artifacts FOR INSERT WITH CHECK (entity_id = current_setting('app.current_user', true));

CREATE POLICY health_admin_all ON family_health_metrics FOR ALL TO family_admin USING (true) WITH CHECK (true);
CREATE POLICY health_owner_select ON family_health_metrics FOR SELECT USING (entity_id = current_setting('app.current_user', true));
CREATE POLICY health_owner_insert ON family_health_metrics FOR INSERT WITH CHECK (entity_id = current_setting('app.current_user', true));

CREATE POLICY rel_admin_all ON family_relationships FOR ALL TO family_admin USING (true) WITH CHECK (true);
CREATE POLICY rel_guardian_view ON family_relationships FOR SELECT USING (
    guardian_id = current_setting('app.current_user', true)
    OR child_id = current_setting('app.current_user', true)
);

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

-- Note: Highly sensitive identifiers (e.g., SSN) are intentionally never stored.