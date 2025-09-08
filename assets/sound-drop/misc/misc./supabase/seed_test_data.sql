-- Seed a test user
INSERT INTO auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  recovery_token, recovery_sent_at, last_sign_in_at, raw_app_meta_data,
  raw_user_meta_data, created_at, updated_at, confirmation_token, email_change,
  email_change_sent_at, confirmed_at
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  'a1b2c3d4-e5f6-7890-1234-567890abcdef',
  'authenticated', 'authenticated', 'test@example.com',
  crypt('password123', gen_salt('bf')), NOW(), '', NULL, NULL,
  '{"provider":"email","providers":["email"]}', '{}', NOW(), NOW(), '', '', NULL, NOW()
);

-- Seed children for the test user
INSERT INTO public.children (user_id, name, age, avatar, device, status) VALUES
  ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'Emma', 8, '👧', 'iPad', 'active'),
  ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'Liam', 12, '👦', 'iPhone', 'break');

-- Seed some daily logs for Emma (child_id = 1)
INSERT INTO public.daily_logs (child_id, log_date, fitness, mental, notes, screen_time_minutes, exercise_minutes, breaks) VALUES
  (1, '2025-07-12', 7, 6, 'A bit restless today.', 110, 20, 2),
  (1, '2025-07-11', 6, 8, 'Calm and focused during homework', 95, 30, 3);

-- Seed some supplements
INSERT INTO public.supplements (user_id, name, dosage) VALUES
  ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'Vitamin D3', '1000 IU'),
  ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'Omega-3', '500mg');

-- Link supplements to a daily log (for log_id = 1, which corresponds to Emma on 2025-07-12)
INSERT INTO public.daily_log_supplements (daily_log_id, supplement_id) VALUES
  (1, 1),
  (1, 2);
