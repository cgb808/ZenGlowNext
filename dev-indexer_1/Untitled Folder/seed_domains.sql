-- Seed domains registry
INSERT INTO domains(key, title) VALUES
  ('health','Health'),
  ('mental_health','Mental Health'),
  ('tutoring','Tutoring'),
  ('conversation','Conversation'),
  ('cooking','Cooking'),
  ('diy','DIY'),
  ('personal_assistant','Personal Assistant'),
  ('search','Search')
ON CONFLICT DO NOTHING;
