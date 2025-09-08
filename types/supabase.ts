// Supabase Database Types
// Auto-generated from Supabase schema

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          username: string;
          full_name: string;
          avatar_url: string;
          website: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          username?: string;
          full_name?: string;
          avatar_url?: string;
          website?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          username?: string;
          full_name?: string;
          avatar_url?: string;
          website?: string;
          updated_at?: string;
        };
      };
      child_profiles: {
        Row: {
          id: string;
          user_id: string;
          name: string;
          age: number;
          avatar_color: string;
          bedtime: string;
          wake_time: string;
          max_session_length: number;
          allowed_exercise_types: string[];
          sound_volume_limits: any;
          total_sessions: number;
          longest_streak: number;
          current_streak: number;
          favorite_exercises: string[];
          recent_moods: any[];
          sleep_quality: any[];
          energy_levels: any[];
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          name: string;
          age: number;
          avatar_color?: string;
          bedtime?: string;
          wake_time?: string;
          max_session_length?: number;
          allowed_exercise_types?: string[];
          sound_volume_limits?: any;
          total_sessions?: number;
          longest_streak?: number;
          current_streak?: number;
          favorite_exercises?: string[];
          recent_moods?: any[];
          sleep_quality?: any[];
          energy_levels?: any[];
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          name?: string;
          age?: number;
          avatar_color?: string;
          bedtime?: string;
          wake_time?: string;
          max_session_length?: number;
          allowed_exercise_types?: string[];
          sound_volume_limits?: any;
          total_sessions?: number;
          longest_streak?: number;
          current_streak?: number;
          favorite_exercises?: string[];
          recent_moods?: any[];
          sleep_quality?: any[];
          energy_levels?: any[];
          created_at?: string;
          updated_at?: string;
        };
      };
      children: {
        Row: {
          id: number;
          user_id: string;
          name: string;
          age: number;
          avatar: string;
          status: string;
          device: string;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          user_id: string;
          name: string;
          age: number;
          avatar?: string;
          status?: string;
          device?: string;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          user_id?: string;
          name?: string;
          age?: number;
          avatar?: string;
          status?: string;
          device?: string;
          created_at?: string;
          updated_at?: string;
        };
      };
      routine_completions: {
        Row: {
          id: number;
          user_id: string;
          child_id: number;
          routine_type: string;
          routine_name: string;
          completed_at: string;
          completion_date: string;
          duration_minutes: number;
          completion_percentage: number;
          notes: string;
          metadata: any;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          user_id: string;
          child_id: number;
          routine_type: string;
          routine_name: string;
          completed_at?: string;
          completion_date?: string;
          duration_minutes?: number;
          completion_percentage?: number;
          notes?: string;
          metadata?: any;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          user_id?: string;
          child_id?: number;
          routine_type?: string;
          routine_name?: string;
          completed_at?: string;
          completion_date?: string;
          duration_minutes?: number;
          completion_percentage?: number;
          notes?: string;
          metadata?: any;
          created_at?: string;
          updated_at?: string;
        };
      };
      sensor_daily_summaries: {
        Row: {
          id: number;
          user_id: string;
          child_id: number;
          summary_date: string;
          steps_count: number;
          active_minutes: number;
          heart_rate_avg: number;
          heart_rate_min: number;
          heart_rate_max: number;
          sleep_duration_minutes: number;
          sleep_quality_score: number;
          stress_level_avg: number;
          calories_burned: number;
          device_wear_time_minutes: number;
          data_completeness_percentage: number;
          sensor_metadata: any;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          user_id: string;
          child_id: number;
          summary_date?: string;
          steps_count?: number;
          active_minutes?: number;
          heart_rate_avg?: number;
          heart_rate_min?: number;
          heart_rate_max?: number;
          sleep_duration_minutes?: number;
          sleep_quality_score?: number;
          stress_level_avg?: number;
          calories_burned?: number;
          device_wear_time_minutes?: number;
          data_completeness_percentage?: number;
          sensor_metadata?: any;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          user_id?: string;
          child_id?: number;
          summary_date?: string;
          steps_count?: number;
          active_minutes?: number;
          heart_rate_avg?: number;
          heart_rate_min?: number;
          heart_rate_max?: number;
          sleep_duration_minutes?: number;
          sleep_quality_score?: number;
          stress_level_avg?: number;
          calories_burned?: number;
          device_wear_time_minutes?: number;
          data_completeness_percentage?: number;
          sensor_metadata?: any;
          created_at?: string;
          updated_at?: string;
        };
      };
      daily_logs: {
        Row: {
          id: number;
          child_id: number;
          log_date: string;
          fitness: number;
          mental: number;
          notes: string;
          screen_time_minutes: number;
          exercise_minutes: number;
          breaks_taken: number;
          achievements: string[];
          wellness_score: number;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: number;
          child_id: number;
          log_date: string;
          fitness?: number;
          mental?: number;
          notes?: string;
          screen_time_minutes?: number;
          exercise_minutes?: number;
          breaks_taken?: number;
          achievements?: string[];
          wellness_score?: number;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: number;
          child_id?: number;
          log_date?: string;
          fitness?: number;
          mental?: number;
          notes?: string;
          screen_time_minutes?: number;
          exercise_minutes?: number;
          breaks_taken?: number;
          achievements?: string[];
          wellness_score?: number;
          created_at?: string;
          updated_at?: string;
        };
      };
      mood_entries: {
        Row: {
          id: string;
          user_id: string;
          mood: string;
          notes: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          mood: string;
          notes?: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          mood?: string;
          notes?: string;
          created_at?: string;
        };
      };
    };
    Views: {
      mood_aggregates: {
        Row: {
          user_id: string;
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
        };
      };
    };
    Functions: {
      get_parent_dashboard_metrics: {
        Args: {
          parent_user_id: string;
          days_back?: number;
        };
        Returns: {
          child_id: number;
          child_name: string;
          recent_mood_trend: string;
          avg_wellness_score: number;
          total_routines_completed: number;
          screen_time_avg: number;
          exercise_avg: number;
          last_activity_date: string;
        }[];
      };
      refresh_mood_aggregates: {
        Args: {};
        Returns: void;
      };
    };
    Enums: {
      user_type: 'parent' | 'child';
      message_type: 'encouragement' | 'alert' | 'guidance' | 'system';
      activity_type: 'meditation' | 'exercise' | 'screen_time' | 'mood_entry';
    };
  };
}

export type Tables<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Row'];
export type Inserts<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Insert'];
export type Updates<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Update'];