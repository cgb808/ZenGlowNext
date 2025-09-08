-- =================================================================================
-- PARENT DASHBOARD METRICS SCHEMA ENHANCEMENT
-- =================================================================================
-- Purpose: Add missing tables and optimize for parent dashboard metrics
-- Requirements: routine_completions, mood_aggregates, sensor_daily_summaries
-- Performance: Indexes on (user_id, date) for acceptable latency

-- =================================================================================
-- 1. ROUTINE COMPLETIONS TABLE
-- =================================================================================
-- Track completion of daily routines and activities
CREATE TABLE routine_completions (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  child_id BIGINT REFERENCES children(id) ON DELETE CASCADE NOT NULL,
  routine_type TEXT NOT NULL CHECK (routine_type IN ('morning', 'evening', 'exercise', 'meditation', 'bedtime', 'custom')),
  routine_name TEXT NOT NULL,
  completed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  completion_date DATE NOT NULL DEFAULT CURRENT_DATE,
  duration_minutes INTEGER CHECK (duration_minutes > 0),
  completion_percentage INTEGER DEFAULT 100 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
  notes TEXT DEFAULT '',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Performance indexes
CREATE INDEX idx_routine_completions_user_date ON routine_completions(user_id, completion_date);
CREATE INDEX idx_routine_completions_child_date ON routine_completions(child_id, completion_date);
CREATE INDEX idx_routine_completions_type ON routine_completions(routine_type);
CREATE INDEX idx_routine_completions_completed_at ON routine_completions(completed_at);

-- =================================================================================
-- 2. SENSOR DAILY SUMMARIES TABLE  
-- =================================================================================
-- Daily aggregated sensor data for wellness tracking
CREATE TABLE sensor_daily_summaries (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  child_id BIGINT REFERENCES children(id) ON DELETE CASCADE NOT NULL,
  summary_date DATE NOT NULL DEFAULT CURRENT_DATE,
  steps_count INTEGER DEFAULT 0 CHECK (steps_count >= 0),
  active_minutes INTEGER DEFAULT 0 CHECK (active_minutes >= 0),
  heart_rate_avg DECIMAL(5,2) CHECK (heart_rate_avg > 0),
  heart_rate_min INTEGER CHECK (heart_rate_min > 0),
  heart_rate_max INTEGER CHECK (heart_rate_max > 0),
  sleep_duration_minutes INTEGER CHECK (sleep_duration_minutes >= 0),
  sleep_quality_score INTEGER CHECK (sleep_quality_score >= 1 AND sleep_quality_score <= 10),
  stress_level_avg DECIMAL(3,2) CHECK (stress_level_avg >= 0 AND stress_level_avg <= 10),
  calories_burned INTEGER DEFAULT 0 CHECK (calories_burned >= 0),
  device_wear_time_minutes INTEGER DEFAULT 0 CHECK (device_wear_time_minutes >= 0),
  data_completeness_percentage INTEGER DEFAULT 100 CHECK (data_completeness_percentage >= 0 AND data_completeness_percentage <= 100),
  sensor_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  UNIQUE(child_id, summary_date) -- One summary per child per day
);

-- Performance indexes
CREATE INDEX idx_sensor_summaries_user_date ON sensor_daily_summaries(user_id, summary_date);
CREATE INDEX idx_sensor_summaries_child_date ON sensor_daily_summaries(child_id, summary_date);
CREATE INDEX idx_sensor_summaries_date ON sensor_daily_summaries(summary_date);

-- =================================================================================
-- 3. MOOD AGGREGATES MATERIALIZED VIEW
-- =================================================================================
-- Optimized view for mood trends and analytics
CREATE MATERIALIZED VIEW mood_aggregates AS
SELECT 
  c.user_id,
  c.id as child_id,
  c.name as child_name,
  DATE_TRUNC('day', dl.log_date) as date,
  DATE_TRUNC('week', dl.log_date) as week_start,
  DATE_TRUNC('month', dl.log_date) as month_start,
  
  -- Daily mood metrics
  AVG(dl.mental) as avg_mental_score,
  AVG(dl.fitness) as avg_fitness_score,
  AVG(dl.wellness_score) as avg_wellness_score,
  
  -- Daily activity metrics
  AVG(dl.screen_time_minutes) as avg_screen_time,
  AVG(dl.exercise_minutes) as avg_exercise_time,
  AVG(dl.breaks_taken) as avg_breaks_taken,
  
  -- Completion metrics
  COUNT(*) as total_logs,
  COUNT(CASE WHEN dl.wellness_score >= 70 THEN 1 END) as good_days,
  COUNT(CASE WHEN dl.wellness_score < 50 THEN 1 END) as challenging_days,
  
  -- Trends
  CASE 
    WHEN AVG(dl.wellness_score) >= 80 THEN 'excellent'
    WHEN AVG(dl.wellness_score) >= 60 THEN 'good'  
    WHEN AVG(dl.wellness_score) >= 40 THEN 'fair'
    ELSE 'needs_attention'
  END as mood_trend,
  
  MAX(dl.log_date) as last_updated
FROM children c
LEFT JOIN daily_logs dl ON c.id = dl.child_id
WHERE dl.log_date >= CURRENT_DATE - INTERVAL '90 days' -- Last 90 days for performance
GROUP BY c.user_id, c.id, c.name, DATE_TRUNC('day', dl.log_date), DATE_TRUNC('week', dl.log_date), DATE_TRUNC('month', dl.log_date);

-- Indexes for materialized view
CREATE UNIQUE INDEX idx_mood_aggregates_user_child_date ON mood_aggregates(user_id, child_id, date);
CREATE INDEX idx_mood_aggregates_user_date ON mood_aggregates(user_id, date);
CREATE INDEX idx_mood_aggregates_week ON mood_aggregates(week_start);
CREATE INDEX idx_mood_aggregates_month ON mood_aggregates(month_start);
CREATE INDEX idx_mood_aggregates_trend ON mood_aggregates(mood_trend);

-- =================================================================================
-- 4. ENABLE ROW LEVEL SECURITY
-- =================================================================================
ALTER TABLE routine_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_daily_summaries ENABLE ROW LEVEL SECURITY;

-- =================================================================================
-- 5. ROW LEVEL SECURITY POLICIES
-- =================================================================================

-- Routine Completions: Users can only manage routines for their own children
CREATE POLICY "users_can_manage_own_routine_completions" ON routine_completions
  FOR ALL USING (
    user_id = auth.uid() OR 
    child_id IN (SELECT id FROM children WHERE user_id = auth.uid())
  );

-- Sensor Daily Summaries: Users can only view summaries for their own children  
CREATE POLICY "users_can_view_own_sensor_summaries" ON sensor_daily_summaries
  FOR ALL USING (
    user_id = auth.uid() OR
    child_id IN (SELECT id FROM children WHERE user_id = auth.uid())
  );

-- =================================================================================
-- 6. HELPER FUNCTIONS FOR METRICS
-- =================================================================================

-- Function to refresh mood aggregates materialized view
CREATE OR REPLACE FUNCTION refresh_mood_aggregates()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY mood_aggregates;
END;
$$;

-- Function to get parent dashboard summary metrics
CREATE OR REPLACE FUNCTION get_parent_dashboard_metrics(parent_user_id UUID, days_back INTEGER DEFAULT 30)
RETURNS TABLE (
  child_id BIGINT,
  child_name TEXT,
  recent_mood_trend TEXT,
  avg_wellness_score DECIMAL,
  total_routines_completed BIGINT,
  screen_time_avg INTEGER,
  exercise_avg INTEGER,
  last_activity_date DATE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id as child_id,
    c.name as child_name,
    COALESCE(ma.mood_trend, 'no_data') as recent_mood_trend,
    COALESCE(ma.avg_wellness_score, 0) as avg_wellness_score,
    COALESCE(rc_count.routine_count, 0) as total_routines_completed,
    COALESCE(ma.avg_screen_time::INTEGER, 0) as screen_time_avg,
    COALESCE(ma.avg_exercise_time::INTEGER, 0) as exercise_avg,
    COALESCE(ma.last_updated, CURRENT_DATE - INTERVAL '1 year') as last_activity_date
  FROM children c
  LEFT JOIN mood_aggregates ma ON c.id = ma.child_id 
    AND ma.date >= CURRENT_DATE - make_interval(days => days_back)
  LEFT JOIN (
    SELECT 
      child_id, 
      COUNT(*) as routine_count
    FROM routine_completions 
    WHERE completion_date >= CURRENT_DATE - make_interval(days => days_back)
    GROUP BY child_id
  ) rc_count ON c.id = rc_count.child_id
  WHERE c.user_id = parent_user_id
  GROUP BY c.id, c.name, ma.mood_trend, ma.avg_wellness_score, rc_count.routine_count, ma.avg_screen_time, ma.avg_exercise_time, ma.last_updated
  ORDER BY c.name;
END;
$$;

-- =================================================================================
-- 7. TRIGGERS FOR AUTOMATIC UPDATES
-- =================================================================================

-- Trigger for routine_completions updated_at
CREATE TRIGGER update_routine_completions_updated_at 
  BEFORE UPDATE ON routine_completions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for sensor_daily_summaries updated_at  
CREATE TRIGGER update_sensor_summaries_updated_at
  BEFORE UPDATE ON sensor_daily_summaries
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =================================================================================
-- 8. PERFORMANCE OPTIMIZATION INDEXES
-- =================================================================================

-- Additional composite indexes for parent dashboard queries
CREATE INDEX idx_children_user_id_name ON children(user_id, name);
CREATE INDEX idx_daily_logs_child_date_wellness ON daily_logs(child_id, log_date, wellness_score);
CREATE INDEX idx_daily_logs_date_wellness ON daily_logs(log_date, wellness_score) WHERE wellness_score IS NOT NULL;

-- =================================================================================
-- 9. COMMENTS FOR DOCUMENTATION
-- =================================================================================

COMMENT ON TABLE routine_completions IS 'Tracks completion of daily routines and activities for children';
COMMENT ON TABLE sensor_daily_summaries IS 'Daily aggregated sensor data from wearables and devices';
COMMENT ON MATERIALIZED VIEW mood_aggregates IS 'Optimized aggregated mood and wellness metrics for dashboard analytics';
COMMENT ON FUNCTION get_parent_dashboard_metrics IS 'Returns comprehensive metrics for parent dashboard with acceptable latency';
COMMENT ON FUNCTION refresh_mood_aggregates IS 'Refreshes materialized view for up-to-date mood analytics';

-- =================================================================================
-- SCHEMA ENHANCEMENT COMPLETE
-- =================================================================================
-- This enhancement provides:
-- 1. ✅ routine_completions table for activity tracking
-- 2. ✅ sensor_daily_summaries table for device data
-- 3. ✅ mood_aggregates materialized view for performance
-- 4. ✅ Optimized indexes on (user_id, date) pairs
-- 5. ✅ RLS policies for data security
-- 6. ✅ Helper functions for efficient metrics queries
-- 7. ✅ Performance optimization for parent dashboard