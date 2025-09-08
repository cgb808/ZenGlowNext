// Parent Dashboard API Service
import { createClient } from '@supabase/supabase-js';
import type { 
  ParentDashboardData, 
  DailyData, 
  Insight, 
  ChildData, 
  RoutineCompletion,
  SensorData,
  MoodAggregate,
  ParentDashboardMetrics 
} from '../../types/parentDashboard';
import type { Database } from '../../types/supabase';

import { isMetricsDashboardEnabled } from '../utils/featureFlags';

import { mapMetricsRow, summarize } from '../utils/metricsUtils';


// Initialize Supabase client with fallback for testing
let supabase: any;

try {
  // Try to import Constants for Expo environment
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Constants = require('expo-constants').default;
  const supabaseUrl = Constants?.expoConfig?.extra?.supabaseUrl || '';
  const supabaseAnonKey = Constants?.expoConfig?.extra?.supabaseAnonKey || '';
  
  if (supabaseUrl && supabaseAnonKey) {
    supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);
  }
} catch {
  // Fallback for non-Expo environments (tests, etc.)
  console.warn('Expo Constants not available, using environment variables');
  const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '';
  const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || '';
  
  if (supabaseUrl && supabaseAnonKey) {
    supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);
  }
}

// Mock client for testing environments
if (!supabase) {
  console.warn('Supabase client not initialized - using mock for testing');
  supabase = {
    from: () => ({
      select: () => ({
        eq: () => ({
          order: () => ({ data: [], error: null }),
          gte: () => ({
            lte: () => ({
              order: () => ({ data: [], error: null })
            })
          }),
          single: () => ({ data: null, error: { code: 'PGRST116' } }),
          limit: () => ({ data: [], error: null })
        })
      })
    }),
    rpc: () => ({ data: [], error: null })
  };
}

export const parentDashboardApi = {
  /**
   * Get dashboard data using feature flag to determine approach
   * This method automatically chooses between legacy and metrics-first based on PARENT_DASHBOARD_METRICS flag
   */
  async getParentDashboard(userId: string): Promise<ParentDashboardData> {
    if (isMetricsDashboardEnabled()) {
      return this.getAggregatedMetricsDashboard(userId);
    } else {
      return this.getDashboardData(userId);
    }
  },

  /**
   * Get comprehensive dashboard data for a parent user (LEGACY)
   */
  async getDashboardData(userId: string): Promise<ParentDashboardData> {
    try {
      const [
        childrenResult,
        dailyDataResult,
        routineCompletionsResult,
        sensorDataResult,
        moodAggregatesResult,
        metricsResult
      ] = await Promise.all([
        this.getChildren(userId),
        this.getRecentDailyData(userId, 30),
        this.getRecentRoutineCompletions(userId, 30), 
        this.getRecentSensorData(userId, 30),
        this.getMoodAggregates(userId, 30),
        this.getDashboardMetrics(userId, 30)
      ]);

      // Generate insights based on the data
      const insights = await this.generateInsights(childrenResult, dailyDataResult, metricsResult);

      return {
        children: childrenResult,
        insights,
        dailyData: dailyDataResult,
        routineCompletions: routineCompletionsResult,
        sensorData: sensorDataResult,
        moodAggregates: moodAggregatesResult,
        metrics: metricsResult,
        weeklyTrends: {}, // TODO: Implement weekly trends
        monthlyReport: {}  // TODO: Implement monthly report
      };
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      throw new Error('Failed to fetch dashboard data');
    }
  },

  /**
   * Get aggregated metrics dashboard data (metrics-first approach)
   * This is the optimized version that prioritizes metrics data
   */
  async getAggregatedMetricsDashboard(userId: string): Promise<ParentDashboardData> {
    try {
      // Start with metrics as the primary data source
      const metricsResult = await this.getDashboardMetrics(userId, 30);
      
      // Get children data enhanced with metrics
      const childrenResult = await this.getChildren(userId);
      
      // Generate insights based on metrics
      const insights = await this.generateInsights(childrenResult, [], metricsResult);
      
      // Get only essential supporting data in parallel
      const [
        routineCompletionsResult,
        moodAggregatesResult
      ] = await Promise.all([
        this.getRecentRoutineCompletions(userId, 30),
        this.getMoodAggregates(userId, 30)
      ]);

      // Return streamlined dashboard focused on metrics
      return {
        children: childrenResult,
        insights,
        dailyData: [], // Minimal daily data in metrics-first approach
        routineCompletions: routineCompletionsResult,
        sensorData: [], // Sensor data derived from metrics instead
        moodAggregates: moodAggregatesResult,
        metrics: metricsResult,
        weeklyTrends: {}, // TODO: Implement from metrics
        monthlyReport: {}  // TODO: Implement from metrics
      };
    } catch (error) {
      console.error('Error fetching aggregated metrics dashboard:', error);
      throw new Error('Failed to fetch aggregated metrics dashboard');
    }
  },

  /**
   * Get children for a parent user with enhanced metrics
   */
  async getChildren(userId: string): Promise<ChildData[]> {
    const { data, error } = await supabase
      .from('children')
      .select(`
        id,
        name,
        age,
        avatar,
        status,
        device,
        created_at,
        updated_at
      `)
      .eq('user_id', userId)
      .order('name');

    if (error) {
      console.error('Error fetching children:', error);
      throw error;
    }

    // Enhance with metrics from dashboard function
    const metrics = await this.getDashboardMetrics(userId);
    
    return data.map((child: any) => mapMetricsRow(child, metrics));
  },

  /**
   * Get dashboard metrics using optimized function
   */
  async getDashboardMetrics(userId: string, daysBack: number = 30): Promise<ParentDashboardMetrics[]> {
    const { data, error } = await supabase.rpc('get_parent_dashboard_metrics', {
      parent_user_id: userId,
      days_back: daysBack
    });

    if (error) {
      console.error('Error fetching dashboard metrics:', error);
      throw error;
    }

    return data || [];
  },

  /**
   * Get daily data for date range
   */
  async getDailyData(childId: number, dateRange: { start: Date; end: Date }): Promise<DailyData[]> {
    const { data, error } = await supabase
      .from('daily_logs')
      .select(`
        id,
        log_date,
        fitness,
        mental,
        screen_time_minutes,
        exercise_minutes,
        breaks_taken,
        wellness_score,
        notes,
        achievements
      `)
      .eq('child_id', childId)
      .gte('log_date', dateRange.start.toISOString().split('T')[0])
      .lte('log_date', dateRange.end.toISOString().split('T')[0])
      .order('log_date', { ascending: false });

    if (error) {
      console.error('Error fetching daily data:', error);
      throw error;
    }

    return data.map(log => ({
      date: log.log_date,
      mood: log.mental || 0,
      exercise: log.exercise_minutes || 0,
      sleep: 0, // TODO: Add sleep data
      nutrition: 0, // TODO: Add nutrition data  
      mental: log.mental || 0,
      screenTime: log.screen_time_minutes || 0,
      fitness: log.fitness || 0,
      wellness_score: log.wellness_score || 0,
      breaks_taken: log.breaks_taken || 0,
      achievements: log.achievements || [],
      notes: log.notes || ''
    }));
  },

  /**
   * Get recent daily data for all children of a parent
   */
  async getRecentDailyData(userId: string, daysBack: number = 30): Promise<DailyData[]> {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - daysBack);

    const { data, error } = await supabase
      .from('daily_logs')
      .select(`
        id,
        log_date,
        fitness,
        mental,
        screen_time_minutes,
        exercise_minutes,
        breaks_taken,
        wellness_score,
        notes,
        achievements,
        child_id,
        children!inner(user_id)
      `)
      .eq('children.user_id', userId)
      .gte('log_date', startDate.toISOString().split('T')[0])
      .order('log_date', { ascending: false })
      .limit(100);

    if (error) {
      console.error('Error fetching recent daily data:', error);
      throw error;
    }

    return data.map(log => ({
      date: log.log_date,
      mood: log.mental || 0,
      exercise: log.exercise_minutes || 0,
      sleep: 0,
      nutrition: 0,
      mental: log.mental || 0,
      screenTime: log.screen_time_minutes || 0,
      fitness: log.fitness || 0,
      wellness_score: log.wellness_score || 0,
      breaks_taken: log.breaks_taken || 0,
      achievements: log.achievements || [],
      notes: log.notes || ''
    }));
  },

  /**
   * Get daily data for a specific date
   */
  async getDailyDataForDate(childId: number, date: Date): Promise<DailyData | null> {
    const dateStr = date.toISOString().split('T')[0];
    
    const { data, error } = await supabase
      .from('daily_logs')
      .select(`
        id,
        log_date,
        fitness,
        mental,
        screen_time_minutes,
        exercise_minutes,
        breaks_taken,
        wellness_score,
        notes,
        achievements
      `)
      .eq('child_id', childId)
      .eq('log_date', dateStr)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        // No data found for this date
        return null;
      }
      console.error('Error fetching daily data for date:', error);
      throw error;
    }

    return {
      date: data.log_date,
      mood: data.mental || 0,
      exercise: data.exercise_minutes || 0,
      sleep: 0,
      nutrition: 0,
      mental: data.mental || 0,
      screenTime: data.screen_time_minutes || 0,
      fitness: data.fitness || 0,
      wellness_score: data.wellness_score || 0,
      breaks_taken: data.breaks_taken || 0,
      achievements: data.achievements || [],
      notes: data.notes || ''
    };
  },

  /**
   * Get routine completions
   */
  async getRecentRoutineCompletions(userId: string, daysBack: number = 30): Promise<RoutineCompletion[]> {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - daysBack);

    const { data, error } = await supabase
      .from('routine_completions')
      .select(`
        id,
        routine_type,
        routine_name,
        completed_at,
        completion_date,
        duration_minutes,
        completion_percentage,
        notes
      `)
      .eq('user_id', userId)
      .gte('completion_date', startDate.toISOString().split('T')[0])
      .order('completed_at', { ascending: false })
      .limit(100);

    if (error) {
      console.error('Error fetching routine completions:', error);
      throw error;
    }

    return data || [];
  },

  /**
   * Get sensor data summaries  
   */
  async getRecentSensorData(userId: string, daysBack: number = 30): Promise<SensorData[]> {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - daysBack);

    const { data, error } = await supabase
      .from('sensor_daily_summaries')
      .select(`
        id,
        summary_date,
        steps_count,
        active_minutes,
        heart_rate_avg,
        sleep_duration_minutes,
        sleep_quality_score,
        stress_level_avg,
        calories_burned,
        device_wear_time_minutes,
        data_completeness_percentage
      `)
      .eq('user_id', userId)
      .gte('summary_date', startDate.toISOString().split('T')[0])
      .order('summary_date', { ascending: false })
      .limit(100);

    if (error) {
      console.error('Error fetching sensor data:', error);
      throw error;
    }

    return data || [];
  },

  /**
   * Get mood aggregates from materialized view
   */
  async getMoodAggregates(userId: string, daysBack: number = 30): Promise<MoodAggregate[]> {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - daysBack);

    const { data, error } = await supabase
      .from('mood_aggregates')
      .select('*')
      .eq('user_id', userId)
      .gte('date', startDate.toISOString().split('T')[0])
      .order('date', { ascending: false })
      .limit(200);

    if (error) {
      console.error('Error fetching mood aggregates:', error);
      throw error;
    }

    return data || [];
  },

  /**
   * Generate insights based on collected data
   */
  async generateInsights(
    children: ChildData[],
    dailyData: DailyData[],
    metrics: ParentDashboardMetrics[]
  ): Promise<Insight[]> {
    return summarize(children, metrics);
  },

  /**
   * Get insights for a specific child
   */
  async getInsights(childId: number): Promise<Insight[]> {
    // Get insights from database
    const { data, error } = await supabase
      .from('insights')
      .select('*')
      .eq('child_id', childId)
      .eq('is_dismissed', false)
      .order('generated_at', { ascending: false })
      .limit(10);

    if (error) {
      console.error('Error fetching insights:', error);
      throw error;
    }

    return data.map(insight => ({
      id: insight.id.toString(),
      type: insight.insight_type as any,
      title: insight.title,
      description: insight.message,
      priority: 'medium' as const,
      actionable: true
    }));
  },

  /**
   * Refresh mood aggregates materialized view
   */
  async refreshMoodAggregates(): Promise<void> {
    const { error } = await supabase.rpc('refresh_mood_aggregates');
    
    if (error) {
      console.error('Error refreshing mood aggregates:', error);
      throw error;
    }
  }
};