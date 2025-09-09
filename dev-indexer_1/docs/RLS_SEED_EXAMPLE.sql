-- Seed example for RLS and guardianship
-- Replace UUIDs with your actual values

-- Identities
INSERT INTO pii_identity_profiles (id, subject_type, subject_ref, legal_name, preferred_name, email)
VALUES
  ('00000000-0000-0000-0000-00000000c001', 'person', 'charles', 'Charles Bowen', 'Charles', 'charles@example.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO pii_identity_profiles (id, subject_type, subject_ref, legal_name, preferred_name, email)
VALUES
  ('00000000-0000-0000-0000-00000000c002', 'person', 'nancy', 'Nancy Bowen', 'Nancy', 'nancy@example.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO pii_identity_profiles (id, subject_type, subject_ref, legal_name, preferred_name)
VALUES
  ('00000000-0000-0000-0000-00000000c003', 'person', 'willow', 'Willow Bowen', 'Willow')
ON CONFLICT (id) DO NOTHING;

-- Guardianship
INSERT INTO pii_guardianship (guardian_id, ward_id, relation)
VALUES
  ('00000000-0000-0000-0000-00000000c001', '00000000-0000-0000-0000-00000000c003', 'parent'),
  ('00000000-0000-0000-0000-00000000c002', '00000000-0000-0000-0000-00000000c003', 'parent')
ON CONFLICT DO NOTHING;

-- Test: set session as dev (full access)
SELECT set_config('app.role', 'dev', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-00000000c001', true);

-- Test: self access
SELECT set_config('app.role', 'user', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-00000000c001', true);
SELECT * FROM pii_identity_profiles; -- sees Charles

-- Test: guardian access (as Charles to Willow)
SELECT set_config('app.user_id', '00000000-0000-0000-0000-00000000c001', true);
SELECT * FROM pii_identity_profiles WHERE id = '00000000-0000-0000-0000-00000000c003'; -- sees Willow

-- Test: as Nancy
SELECT set_config('app.user_id', '00000000-0000-0000-0000-00000000c002', true);
SELECT * FROM pii_identity_profiles WHERE id = '00000000-0000-0000-0000-00000000c003'; -- sees Willow
