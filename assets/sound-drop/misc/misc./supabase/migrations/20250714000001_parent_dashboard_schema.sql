-- =================================================================================
-- PARENT DASHBOARD SCHEMA - The Database Blueprint
-- =================================================================================
-- Purpose: Complete database structure for Parent Dashboard functionality
-- Features: Multi-user support, Row Level Security, proper relationships

-- =================================================================================
-- 1. CHILDREN TABLE
-- =================================================================================
-- Stores information about each child in the system
CREATE TABLE children (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  age INTEGER NOT NULL CHECK (age > 0 AND age < 18),
  avatar TEXT DEFAULT '👧',
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'break', 'offline')),
  device TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_children_user_id ON children(user_id);
CREATE INDEX idx_children_status ON children(status);

-- =================================================================================
-- 2. SUPPLEMENTS TABLE
-- =================================================================================
-- Master list of available supplements with detailed information
CREATE TABLE supplements (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  dosage TEXT NOT NULL,
  color TEXT DEFAULT 'bg-blue-400',
  description TEXT NOT NULL,
  benefits TEXT[] DEFAULT '{}',
  research_links JSONB DEFAULT '[]',
  considerations JSONB DEFAULT '[]',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_supplements_user_id ON supplements(user_id);
CREATE INDEX idx_supplements_is_active ON supplements(is_active);

-- =================================================================================
-- 3. DAILY LIMITS TABLE
-- =================================================================================
-- Store customizable daily limits for each child
CREATE TABLE daily_limits (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  child_id BIGINT REFERENCES children(id) ON DELETE CASCADE NOT NULL,
  screen_time_minutes INTEGER NOT NULL DEFAULT 90,
  exercise_minutes INTEGER NOT NULL DEFAULT 60,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(child_id) -- One limit set per child
);

-- Add indexes
CREATE INDEX idx_daily_limits_child_id ON daily_limits(child_id);

-- =================================================================================
-- 4. DAILY LOGS TABLE
-- =================================================================================
-- Core table for tracking daily wellness metrics
CREATE TABLE daily_logs (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  child_id BIGINT REFERENCES children(id) ON DELETE CASCADE NOT NULL,
  log_date DATE NOT NULL,
  fitness INTEGER CHECK (fitness >= 0 AND fitness <= 10),
  mental INTEGER CHECK (mental >= 0 AND mental <= 10),
  notes TEXT DEFAULT '',
  screen_time_minutes INTEGER DEFAULT 0 CHECK (screen_time_minutes >= 0),
  exercise_minutes INTEGER DEFAULT 0 CHECK (exercise_minutes >= 0),
  breaks_taken INTEGER DEFAULT 0 CHECK (breaks_taken >= 0),
  achievements TEXT[] DEFAULT '{}',
  wellness_score INTEGER DEFAULT 0 CHECK (wellness_score >= 0 AND wellness_score <= 100),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(child_id, log_date) -- Ensure only one log per child per day
);

-- Add indexes for efficient querying
CREATE INDEX idx_daily_logs_child_id ON daily_logs(child_id);
CREATE INDEX idx_daily_logs_date ON daily_logs(log_date);
CREATE INDEX idx_daily_logs_child_date ON daily_logs(child_id, log_date);

-- =================================================================================
-- 5. DAILY LOG SUPPLEMENTS TABLE (Junction Table)
-- =================================================================================
-- Many-to-many relationship between daily logs and supplements taken
CREATE TABLE daily_log_supplements (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  daily_log_id BIGINT REFERENCES daily_logs(id) ON DELETE CASCADE NOT NULL,
  supplement_id BIGINT REFERENCES supplements(id) ON DELETE CASCADE NOT NULL,
  taken_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(daily_log_id, supplement_id) -- Prevent duplicate entries
);

-- Add indexes
CREATE INDEX idx_daily_log_supplements_log_id ON daily_log_supplements(daily_log_id);
CREATE INDEX idx_daily_log_supplements_supplement_id ON daily_log_supplements(supplement_id);

-- =================================================================================
-- 6. INSIGHTS TABLE
-- =================================================================================
-- Store generated predictive insights for review and tracking
CREATE TABLE insights (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  child_id BIGINT REFERENCES children(id) ON DELETE CASCADE NOT NULL,
  insight_type TEXT NOT NULL CHECK (insight_type IN ('warning', 'suggestion', 'positive')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  is_dismissed BOOLEAN DEFAULT FALSE,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  dismissed_at TIMESTAMPTZ
);

-- Add indexes
CREATE INDEX idx_insights_child_id ON insights(child_id);
CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_generated_at ON insights(generated_at);
CREATE INDEX idx_insights_is_dismissed ON insights(is_dismissed);

-- =================================================================================
-- 7. REMINDERS TABLE
-- =================================================================================
-- System for scheduling supplement and activity reminders
CREATE TABLE reminders (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  child_id BIGINT REFERENCES children(id) ON DELETE CASCADE NOT NULL,
  supplement_id BIGINT REFERENCES supplements(id) ON DELETE CASCADE,
  reminder_type TEXT NOT NULL CHECK (reminder_type IN ('supplement', 'exercise', 'break', 'bedtime')),
  reminder_time TIME NOT NULL,
  frequency TEXT NOT NULL DEFAULT 'daily' CHECK (frequency IN ('daily', 'weekly', 'weekdays', 'weekends')),
  days_of_week TEXT[] DEFAULT '{}', -- ['Monday', 'Wednesday', 'Friday']
  is_active BOOLEAN DEFAULT TRUE,
  last_sent TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_reminders_user_id ON reminders(user_id);
CREATE INDEX idx_reminders_child_id ON reminders(child_id);
CREATE INDEX idx_reminders_is_active ON reminders(is_active);
CREATE INDEX idx_reminders_time ON reminders(reminder_time);

-- =================================================================================
-- 8. ENABLE ROW LEVEL SECURITY (RLS)
-- =================================================================================
-- Critical security feature - users can only access their own data

ALTER TABLE children ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplements ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_log_supplements ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;

-- =================================================================================
-- 9. ROW LEVEL SECURITY POLICIES
-- =================================================================================

-- Children: Users can only manage their own children
CREATE POLICY "users_can_manage_own_children" ON children
  FOR ALL USING (auth.uid() = user_id);

-- Supplements: Users can only manage their own supplements
CREATE POLICY "users_can_manage_own_supplements" ON supplements
  FOR ALL USING (auth.uid() = user_id);

-- Daily Limits: Users can only manage limits for their own children
CREATE POLICY "users_can_manage_own_daily_limits" ON daily_limits
  FOR ALL USING (
    child_id IN (SELECT id FROM children WHERE user_id = auth.uid())
  );

-- Daily Logs: Users can only manage logs for their own children
CREATE POLICY "users_can_manage_own_daily_logs" ON daily_logs
  FOR ALL USING (
    child_id IN (SELECT id FROM children WHERE user_id = auth.uid())
  );

-- Daily Log Supplements: Users can only manage supplement logs for their own children
CREATE POLICY "users_can_manage_own_log_supplements" ON daily_log_supplements
  FOR ALL USING (
    daily_log_id IN (
      SELECT id FROM daily_logs 
      WHERE child_id IN (SELECT id FROM children WHERE user_id = auth.uid())
    )
  );

-- Insights: Users can only view insights for their own children
CREATE POLICY "users_can_view_own_insights" ON insights
  FOR ALL USING (
    child_id IN (SELECT id FROM children WHERE user_id = auth.uid())
  );

-- Reminders: Users can only manage their own reminders
CREATE POLICY "users_can_manage_own_reminders" ON reminders
  FOR ALL USING (auth.uid() = user_id);

-- =================================================================================
-- 10. HELPER FUNCTIONS
-- =================================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers to automatically update updated_at
CREATE TRIGGER update_children_updated_at BEFORE UPDATE ON children
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supplements_updated_at BEFORE UPDATE ON supplements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_limits_updated_at BEFORE UPDATE ON daily_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_logs_updated_at BEFORE UPDATE ON daily_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reminders_updated_at BEFORE UPDATE ON reminders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =================================================================================
-- 11. SAMPLE DATA INSERTION (FOR DEVELOPMENT)
-- =================================================================================

-- This would only be run in development environments
-- INSERT INTO children (user_id, name, age, avatar, device) VALUES
-- (auth.uid(), 'Emma', 8, '👧', 'iPad'),
-- (auth.uid(), 'Liam', 12, '👦', 'iPhone'),
-- (auth.uid(), 'Sophia', 6, '👶', 'Tablet');

-- =================================================================================
-- 12. USEFUL VIEWS FOR ANALYTICS
-- =================================================================================

-- Create a view for comprehensive daily metrics
CREATE VIEW daily_metrics_view AS
SELECT 
  dl.id,
  dl.child_id,
  c.name as child_name,
  c.age as child_age,
  dl.log_date,
  dl.fitness,
  dl.mental,
  dl.screen_time_minutes,
  dl.exercise_minutes,
  dl.breaks_taken,
  dl.wellness_score,
  dl.notes,
  dl.achievements,
  dlim.screen_time_minutes as screen_time_limit,
  dlim.exercise_minutes as exercise_limit,
  ARRAY_AGG(s.name) FILTER (WHERE s.name IS NOT NULL) as supplements_taken
FROM daily_logs dl
JOIN children c ON dl.child_id = c.id
LEFT JOIN daily_limits dlim ON c.id = dlim.child_id
LEFT JOIN daily_log_supplements dls ON dl.id = dls.daily_log_id
LEFT JOIN supplements s ON dls.supplement_id = s.id
GROUP BY dl.id, c.id, dlim.id
ORDER BY dl.log_date DESC;

-- Create a view for trend analysis
CREATE VIEW weekly_trends_view AS
SELECT 
  c.id as child_id,
  c.name as child_name,
  DATE_TRUNC('week', dl.log_date) as week_start,
  AVG(dl.fitness) as avg_fitness,
  AVG(dl.mental) as avg_mental,
  AVG(dl.screen_time_minutes) as avg_screen_time,
  AVG(dl.exercise_minutes) as avg_exercise,
  AVG(dl.wellness_score) as avg_wellness_score
FROM daily_logs dl
JOIN children c ON dl.child_id = c.id
GROUP BY c.id, c.name, DATE_TRUNC('week', dl.log_date)
ORDER BY week_start DESC;

-- =================================================================================
-- 13. COMMENT ON TABLES FOR DOCUMENTATION
-- =================================================================================

COMMENT ON TABLE children IS 'Core table storing child profiles and basic information';
COMMENT ON TABLE supplements IS 'Master list of available supplements with detailed metadata';
COMMENT ON TABLE daily_limits IS 'Customizable daily limits and goals for each child';
COMMENT ON TABLE daily_logs IS 'Primary table for daily wellness tracking and metrics';
COMMENT ON TABLE daily_log_supplements IS 'Junction table linking daily logs to supplements taken';
COMMENT ON TABLE insights IS 'System-generated insights and recommendations based on data analysis';
COMMENT ON TABLE reminders IS 'Configurable reminders for supplements, activities, and wellness tasks';

-- =================================================================================
-- SCHEMA COMPLETE
-- =================================================================================
-- This schema provides:
-- 1. Multi-user support with RLS
-- 2. Comprehensive wellness tracking
-- 3. Predictive insights storage
-- 4. Flexible reminder system
-- 5. Performance optimizations
-- 6. Data integrity constraints
-- 7. Audit trails with timestamps
-- 8. Analytics-ready views
