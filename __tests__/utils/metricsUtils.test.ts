// Metrics Utils Tests
import { 
  mapMetricsRow, 
  summarize, 
  trend, 
  analyzeWellnessTrend, 
  calculateMetricsSummary 
} from '../../src/utils/metricsUtils';
import type { ChildData, ParentDashboardMetrics, DailyData } from '../../types/parentDashboard';

describe('metricsUtils', () => {
  describe('mapMetricsRow', () => {
    it('should map child data with matching metrics', () => {
      const child = {
        id: 1,
        name: 'Test Child',
        age: 8,
        avatar: '👧',
        status: 'active',
        device: 'tablet'
      };

      const metrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'excellent',
        avg_wellness_score: 85,
        total_routines_completed: 20,
        screen_time_avg: 60,
        exercise_avg: 45,
        last_activity_date: '2024-01-01'
      }];

      const result = mapMetricsRow(child, metrics);

      expect(result).toEqual({
        id: 1,
        name: 'Test Child',
        age: 8,
        avatar: '👧',
        status: 'active',
        device: 'tablet',
        currentMood: 'excellent',
        zenScore: 85,
        activityLevel: 45,
        recentMoodTrend: 'excellent',
        totalRoutinesCompleted: 20,
        screenTimeAvg: 60,
        exerciseAvg: 45,
        lastActivityDate: '2024-01-01'
      });
    });

    it('should handle child with no matching metrics', () => {
      const child = {
        id: 1,
        name: 'Test Child',
        age: 8,
        avatar: '👧',
        status: 'active',
        device: 'tablet'
      };

      const metrics: ParentDashboardMetrics[] = [];

      const result = mapMetricsRow(child, metrics);

      expect(result.currentMood).toBe('unknown');
      expect(result.zenScore).toBe(0);
      expect(result.activityLevel).toBe(0);
      expect(result.recentMoodTrend).toBeUndefined();
    });

    it('should handle partial metrics data', () => {
      const child = {
        id: 1,
        name: 'Test Child',
        age: 8,
        avatar: '👧',
        status: 'active',
        device: 'tablet'
      };

      const metrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'good',
        avg_wellness_score: 75.7,
        total_routines_completed: 15,
        screen_time_avg: 90,
        exercise_avg: 30,
        last_activity_date: '2024-01-01'
      }];

      const result = mapMetricsRow(child, metrics);

      expect(result.zenScore).toBe(76); // Should round 75.7 to 76
      expect(result.currentMood).toBe('good');
    });
  });

  describe('summarize', () => {
    it('should generate wellness warning for low scores', () => {
      const children: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'needs_attention',
        zenScore: 45,
        activityLevel: 20,
        status: 'active',
        avatar: '👧'
      }];

      const metrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'needs_attention',
        avg_wellness_score: 45,
        total_routines_completed: 5,
        screen_time_avg: 150,
        exercise_avg: 20,
        last_activity_date: '2024-01-01'
      }];

      const insights = summarize(children, metrics);

      expect(insights.length).toBeGreaterThan(0);
      
      const wellnessInsight = insights.find(i => i.type === 'warning' && i.title.includes('Wellness'));
      expect(wellnessInsight).toBeDefined();
      expect(wellnessInsight?.priority).toBe('high');
      expect(wellnessInsight?.actionable).toBe(true);
    });

    it('should generate positive insights for high scores', () => {
      const children: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'excellent',
        zenScore: 85,
        activityLevel: 60,
        status: 'active',
        avatar: '👧'
      }];

      const metrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'excellent',
        avg_wellness_score: 85,
        total_routines_completed: 20,
        screen_time_avg: 60,
        exercise_avg: 60,
        last_activity_date: '2024-01-01'
      }];

      const insights = summarize(children, metrics);

      const positiveInsight = insights.find(i => i.type === 'positive');
      expect(positiveInsight).toBeDefined();
      expect(positiveInsight?.title).toContain('Doing Great');
      expect(positiveInsight?.actionable).toBe(false);
    });

    it('should generate screen time suggestions', () => {
      const children: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'good',
        zenScore: 70,
        activityLevel: 30,
        status: 'active',
        avatar: '👧'
      }];

      const metrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'good',
        avg_wellness_score: 70,
        total_routines_completed: 15,
        screen_time_avg: 150, // Over 120 minutes
        exercise_avg: 30,
        last_activity_date: '2024-01-01'
      }];

      const insights = summarize(children, metrics);

      const screenTimeInsight = insights.find(i => i.type === 'suggestion' && i.title.includes('Screen Time'));
      expect(screenTimeInsight).toBeDefined();
      expect(screenTimeInsight?.priority).toBe('medium');
    });

    it('should generate exercise tips', () => {
      const children: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'good',
        zenScore: 70,
        activityLevel: 20,
        status: 'active',
        avatar: '👧'
      }];

      const metrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'good',
        avg_wellness_score: 70,
        total_routines_completed: 15,
        screen_time_avg: 90,
        exercise_avg: 20, // Less than 30 minutes
        last_activity_date: '2024-01-01'
      }];

      const insights = summarize(children, metrics);

      const exerciseInsight = insights.find(i => i.type === 'tip' && i.title.includes('Physical Activity'));
      expect(exerciseInsight).toBeDefined();
      expect(exerciseInsight?.priority).toBe('medium');
    });

    it('should handle children with no matching metrics', () => {
      const children: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'good',
        zenScore: 70,
        activityLevel: 30,
        status: 'active',
        avatar: '👧'
      }];

      const metrics: ParentDashboardMetrics[] = []; // No metrics

      const insights = summarize(children, metrics);

      expect(insights).toEqual([]);
    });
  });

  describe('trend', () => {
    it('should detect improving trend', () => {
      const values = [50, 60, 70, 80];
      const result = trend(values);
      expect(result).toBe('improving');
    });

    it('should detect declining trend', () => {
      const values = [80, 70, 60, 50];
      const result = trend(values);
      expect(result).toBe('declining');
    });

    it('should detect stable trend', () => {
      const values = [70, 72, 69, 71];
      const result = trend(values);
      expect(result).toBe('stable');
    });

    it('should handle insufficient data', () => {
      expect(trend([])).toBe('stable');
      expect(trend([70])).toBe('stable');
    });

    it('should handle invalid values', () => {
      const values = [70, null as any, undefined as any, 80];
      const result = trend(values);
      expect(result).toBe('improving'); // Should filter out invalid values
    });

    it('should respect custom threshold', () => {
      const values = [100, 102]; // 2% increase
      expect(trend(values, 5)).toBe('stable'); // Below 5% threshold
      expect(trend(values, 1)).toBe('improving'); // Above 1% threshold
    });
  });

  describe('analyzeWellnessTrend', () => {
    it('should analyze improving wellness trend', () => {
      const dailyData: DailyData[] = [
        { date: '2024-01-01', wellness_score: 60, mood: 6, exercise: 30, sleep: 8, nutrition: 7, mental: 6, screenTime: 90, fitness: 5, breaks_taken: 2, achievements: [], notes: '' },
        { date: '2024-01-02', wellness_score: 70, mood: 7, exercise: 30, sleep: 8, nutrition: 7, mental: 7, screenTime: 90, fitness: 6, breaks_taken: 2, achievements: [], notes: '' },
        { date: '2024-01-03', wellness_score: 80, mood: 8, exercise: 30, sleep: 8, nutrition: 7, mental: 8, screenTime: 90, fitness: 7, breaks_taken: 2, achievements: [], notes: '' }
      ];

      const result = analyzeWellnessTrend(dailyData);

      expect(result.direction).toBe('improving');
      expect(result.percentChange).toBeCloseTo(33.33, 1);
      expect(result.dataPoints).toBe(3);
    });

    it('should handle insufficient data', () => {
      const dailyData: DailyData[] = [
        { date: '2024-01-01', wellness_score: 60, mood: 6, exercise: 30, sleep: 8, nutrition: 7, mental: 6, screenTime: 90, fitness: 5, breaks_taken: 2, achievements: [], notes: '' }
      ];

      const result = analyzeWellnessTrend(dailyData);

      expect(result.direction).toBe('stable');
      expect(result.percentChange).toBe(0);
      expect(result.dataPoints).toBe(1);
    });

    it('should filter out zero wellness scores', () => {
      const dailyData: DailyData[] = [
        { date: '2024-01-01', wellness_score: 0, mood: 6, exercise: 30, sleep: 8, nutrition: 7, mental: 6, screenTime: 90, fitness: 5, breaks_taken: 2, achievements: [], notes: '' },
        { date: '2024-01-02', wellness_score: 70, mood: 7, exercise: 30, sleep: 8, nutrition: 7, mental: 7, screenTime: 90, fitness: 6, breaks_taken: 2, achievements: [], notes: '' },
        { date: '2024-01-03', wellness_score: 80, mood: 8, exercise: 30, sleep: 8, nutrition: 7, mental: 8, screenTime: 90, fitness: 7, breaks_taken: 2, achievements: [], notes: '' }
      ];

      const result = analyzeWellnessTrend(dailyData);

      expect(result.dataPoints).toBe(2); // Should exclude the zero score
      expect(result.direction).toBe('improving');
    });
  });

  describe('calculateMetricsSummary', () => {
    it('should calculate averages correctly', () => {
      const metrics: ParentDashboardMetrics[] = [
        {
          child_id: 1,
          child_name: 'Child 1',
          recent_mood_trend: 'good',
          avg_wellness_score: 80,
          total_routines_completed: 10,
          screen_time_avg: 60,
          exercise_avg: 40,
          last_activity_date: '2024-01-01'
        },
        {
          child_id: 2,
          child_name: 'Child 2',
          recent_mood_trend: 'excellent',
          avg_wellness_score: 90,
          total_routines_completed: 15,
          screen_time_avg: 50,
          exercise_avg: 50,
          last_activity_date: '2024-01-01'
        }
      ];

      const result = calculateMetricsSummary(metrics);

      expect(result.avgWellnessScore).toBe(85); // (80 + 90) / 2
      expect(result.avgScreenTime).toBe(55); // (60 + 50) / 2
      expect(result.avgExercise).toBe(45); // (40 + 50) / 2
      expect(result.totalRoutines).toBe(25); // 10 + 15
      expect(result.childrenCount).toBe(2);
    });

    it('should handle empty metrics array', () => {
      const result = calculateMetricsSummary([]);

      expect(result.avgWellnessScore).toBe(0);
      expect(result.avgScreenTime).toBe(0);
      expect(result.avgExercise).toBe(0);
      expect(result.totalRoutines).toBe(0);
      expect(result.childrenCount).toBe(0);
    });

    it('should handle missing metric values', () => {
      const metrics: ParentDashboardMetrics[] = [
        {
          child_id: 1,
          child_name: 'Child 1',
          recent_mood_trend: 'good',
          avg_wellness_score: null as any,
          total_routines_completed: undefined as any,
          screen_time_avg: 60,
          exercise_avg: 40,
          last_activity_date: '2024-01-01'
        }
      ];

      const result = calculateMetricsSummary(metrics);

      expect(result.avgWellnessScore).toBe(0); // null becomes 0
      expect(result.totalRoutines).toBe(0); // undefined becomes 0
      expect(result.avgScreenTime).toBe(60);
      expect(result.avgExercise).toBe(40);
      expect(result.childrenCount).toBe(1);
    });
  });
});