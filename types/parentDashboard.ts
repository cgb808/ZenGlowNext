// Parent Dashboard Types
import type { Database } from './supabase';

type ChildRow = Database['public']['Tables']['children']['Row'];
type DailyLogRow = Database['public']['Tables']['daily_logs']['Row'];
type RoutineCompletionRow = Database['public']['Tables']['routine_completions']['Row'];
type SensorSummaryRow = Database['public']['Tables']['sensor_daily_summaries']['Row'];
type MoodAggregateRow = Database['public']['Views']['mood_aggregates']['Row'];

export interface ChildData {
  id: number;
  name: string;
  age: number;
  currentMood: string;
  zenScore: number;
  activityLevel: number;
  status: string;
  avatar: string;
  device?: string;
  recentMoodTrend?: string;
  totalRoutinesCompleted?: number;
  screenTimeAvg?: number;
  exerciseAvg?: number;
  lastActivityDate?: string;
}

export interface DailyData {
  date: string;
  mood: number;
  exercise: number;
  sleep: number;
  nutrition: number;
  mental: number;
  screenTime: number;
  fitness: number;
  wellness_score: number;
  breaks_taken: number;
  achievements: string[];
  notes: string;
}

export interface RoutineCompletion {
  id: number;
  routine_type: string;
  routine_name: string;
  completed_at: string;
  completion_date: string;
  duration_minutes?: number;
  completion_percentage: number;
  notes: string;
}

export interface SensorData {
  id: number;
  summary_date: string;
  steps_count: number;
  active_minutes: number;
  heart_rate_avg?: number;
  sleep_duration_minutes?: number;
  sleep_quality_score?: number;
  stress_level_avg?: number;
  calories_burned: number;
  device_wear_time_minutes: number;
  data_completeness_percentage: number;
}

export interface MoodAggregate {
  child_id: number;
  child_name: string;
  date: string;
  week_start: string;
  month_start: string;
  avg_mental_score: number;
  avg_fitness_score: number;
  avg_wellness_score: number;
  avg_screen_time: number;
  avg_exercise_time: number;
  avg_breaks_taken: number;
  total_logs: number;
  good_days: number;
  challenging_days: number;
  mood_trend: string;
  last_updated: string;
}

export interface DailyLimits {
  [childName: string]: {
    exercise: number;
    sleep: number;
    nutrition: number;
    mental: number;
    screenTime: number;
  };
}

export interface Insight {
  id: string;
  type: 'warning' | 'tip' | 'celebration' | 'recommendation' | 'suggestion' | 'positive';
  title: string;
  description: string;
  message?: string;
  priority: 'low' | 'medium' | 'high';
  actionable: boolean;
  data?: any;
}

export interface ParentDashboardMetrics {
  child_id: number;
  child_name: string;
  recent_mood_trend: string;
  avg_wellness_score: number;
  total_routines_completed: number;
  screen_time_avg: number;
  exercise_avg: number;
  last_activity_date: string;
}

export interface ParentDashboardData {
  children: ChildData[];
  insights: Insight[];
  dailyData: DailyData[];
  routineCompletions: RoutineCompletion[];
  sensorData: SensorData[];
  moodAggregates: MoodAggregate[];
  metrics: ParentDashboardMetrics[];
  weeklyTrends: any;
  monthlyReport: any;
}

export interface ParentDashboardState {
  selectedChildId: string;
  viewMode: 'daily' | 'weekly' | 'trends' | 'zen-score' | 'routines' | 'sensors';
  dateRange: {
    start: Date;
    end: Date;
  };
  loading: boolean;
  error?: string;
}