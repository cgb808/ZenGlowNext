-- Seed some daily logs for all children
-- Emma (child_id = 1)
INSERT INTO public.daily_logs (child_id, log_date, fitness, mental, notes, screen_time_minutes, exercise_minutes, breaks) VALUES
  (1, '2025-07-12', 7, 6, 'A bit restless today.', 110, 20, 2),
  (1, '2025-07-11', 6, 8, 'Calm and focused during homework', 95, 30, 3),
  (1, '2025-07-10', 8, 7, 'Good day at school.', 80, 60, 4);
-- Liam (child_id = 2)
INSERT INTO public.daily_logs (child_id, log_date, fitness, mental, notes, screen_time_minutes, exercise_minutes, breaks) VALUES
  (2, '2025-07-12', 8, 8, 'Great soccer practice.', 90, 75, 3),
  (2, '2025-07-11', 7, 9, 'Finished his book report.', 100, 45, 4);
-- Sophia (child_id = 3)
INSERT INTO public.daily_logs (child_id, log_date, fitness, mental, notes, screen_time_minutes, exercise_minutes, breaks) VALUES
  (3, '2025-07-12', 9, 9, 'Loved the park today!', 30, 40, 5);

INSERT INTO public.medications (child_id, name, dosage, frequency, reason, type) VALUES
  (2, 'Albuterol', '2 puffs', 'As needed for asthma', 'Asthma', 'prescription');

-- Link supplements and medications to daily logs
-- Emma on 2025-07-12 (daily_log_id = 1)
INSERT INTO public.daily_log_supplements (daily_log_id, supplement_id) VALUES
  (1, 1),
  (1, 2);
-- Liam on 2025-07-12 (daily_log_id = 4)
INSERT INTO public.daily_log_supplements (daily_log_id, supplement_id) VALUES
  (4, 3);
INSERT INTO public.daily_log_medications (daily_log_id, medication_id) VALUES
  (4, 1);

-- Seed some goals for the children
INSERT INTO public.goals (child_id, title, type, target_minutes, is_active) VALUES
  (1, 'Read for 20 minutes daily', 'custom', 20, true),
  (2, 'Practice soccer skills', 'exercise', 30, true);

-- Seed a family conversation
INSERT INTO public.family_conversations (user_id) VALUES ('a1b2c3d4-e5f6-7890-1234-567890abcdef');
-- Add participants to conversation_id = 1
INSERT INTO public.conversation_participants (conversation_id, child_id) VALUES
  (1, 1),
  (1, 2);
-- Add messages to the conversation
INSERT INTO public.family_messages (conversation_id, sender_id, message_type, content) VALUES
  (1, 1, 'text', 'Want to play after homework?'),
  (1, 2, 'text', 'Yeah! Let''s build the new Lego set.');
