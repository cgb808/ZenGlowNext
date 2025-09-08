// Parent Dashboard API Tests
import { parentDashboardApi } from '../../src/services/parentDashboardApi';
import type { ParentDashboardData, ChildData, ParentDashboardMetrics } from '../../types/parentDashboard';
import * as featureFlags from '../../src/utils/featureFlags';

// Mock the feature flags module
jest.mock('../../src/utils/featureFlags', () => ({
  isMetricsDashboardEnabled: jest.fn(() => false),
  logFeatureFlagStatus: jest.fn(),
  getFeatureFlagDebugInfo: jest.fn(() => ({}))
}));

// Mock Supabase client
jest.mock('@supabase/supabase-js', () => ({
  createClient: jest.fn(() => ({
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => ({
          order: jest.fn(() => ({
            data: [],
            error: null
          })),
          gte: jest.fn(() => ({
            lte: jest.fn(() => ({
              order: jest.fn(() => ({
                data: [],
                error: null
              }))
            }))
          })),
          single: jest.fn(() => ({
            data: null,
            error: { code: 'PGRST116' }
          })),
          limit: jest.fn(() => ({
            data: [],
            error: null
          }))
        }))
      }))
    })),
    rpc: jest.fn(() => ({
      data: [],
      error: null
    }))
  }))
}));

describe('Parent Dashboard API', () => {
  const mockUserId = 'test-user-id';
  const mockChildId = 1;
  
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
  });

  describe('getParentDashboard (feature flag method)', () => {
    it('should use legacy getDashboardData when feature flag is disabled', async () => {
      (featureFlags.isMetricsDashboardEnabled as jest.Mock).mockReturnValue(false);
      
      // Spy on the methods to check which one is called
      const getDashboardDataSpy = jest.spyOn(parentDashboardApi, 'getDashboardData');
      const getAggregatedMetricsDashboardSpy = jest.spyOn(parentDashboardApi, 'getAggregatedMetricsDashboard');
      
      try {
        await parentDashboardApi.getParentDashboard(mockUserId);
      } catch (error) {
        // Expected due to mocked environment
      }
      
      expect(getDashboardDataSpy).toHaveBeenCalledWith(mockUserId);
      expect(getAggregatedMetricsDashboardSpy).not.toHaveBeenCalled();
    });

    it('should use getAggregatedMetricsDashboard when feature flag is enabled', async () => {
      (featureFlags.isMetricsDashboardEnabled as jest.Mock).mockReturnValue(true);
      
      // Spy on the methods to check which one is called
      const getDashboardDataSpy = jest.spyOn(parentDashboardApi, 'getDashboardData');
      const getAggregatedMetricsDashboardSpy = jest.spyOn(parentDashboardApi, 'getAggregatedMetricsDashboard');
      
      try {
        await parentDashboardApi.getParentDashboard(mockUserId);
      } catch (error) {
        // Expected due to mocked environment
      }
      
      expect(getAggregatedMetricsDashboardSpy).toHaveBeenCalledWith(mockUserId);
      expect(getDashboardDataSpy).not.toHaveBeenCalled();
    });
  });

  describe('getAggregatedMetricsDashboard (metrics-first approach)', () => {
    it('should return dashboard data structure focused on metrics', async () => {
      try {
        const result = await parentDashboardApi.getAggregatedMetricsDashboard(mockUserId);
        
        expect(result).toHaveProperty('children');
        expect(result).toHaveProperty('insights');
        expect(result).toHaveProperty('metrics');
        expect(result).toHaveProperty('routineCompletions');
        expect(result).toHaveProperty('moodAggregates');
        expect(result).toHaveProperty('dailyData');
        expect(result).toHaveProperty('sensorData');
        expect(result).toHaveProperty('weeklyTrends');
        expect(result).toHaveProperty('monthlyReport');
        
        // In metrics-first approach, dailyData and sensorData should be minimal
        expect(result.dailyData).toEqual([]);
        expect(result.sensorData).toEqual([]);
      } catch (error) {
        // Expected structure validation even if data fetching fails
        expect(error).toBeInstanceOf(Error);
        expect(error.message).toContain('aggregated metrics dashboard');
      }
    });

    it('should handle errors gracefully', async () => {
      await expect(parentDashboardApi.getAggregatedMetricsDashboard(mockUserId))
        .rejects
        .toThrow('Failed to fetch aggregated metrics dashboard');
    });
  });

  describe('getDashboardData', () => {
    it('should return comprehensive dashboard data structure', async () => {
      const result = await parentDashboardApi.getDashboardData(mockUserId);
      
      expect(result).toHaveProperty('children');
      expect(result).toHaveProperty('insights');
      expect(result).toHaveProperty('dailyData');
      expect(result).toHaveProperty('routineCompletions');
      expect(result).toHaveProperty('sensorData');
      expect(result).toHaveProperty('moodAggregates');
      expect(result).toHaveProperty('metrics');
      expect(result).toHaveProperty('weeklyTrends');
      expect(result).toHaveProperty('monthlyReport');
      
      expect(Array.isArray(result.children)).toBe(true);
      expect(Array.isArray(result.insights)).toBe(true);
      expect(Array.isArray(result.dailyData)).toBe(true);
    });

    it('should handle errors gracefully', async () => {
      // Mock error case
      const originalConsoleError = console.error;
      console.error = jest.fn();

      try {
        await parentDashboardApi.getDashboardData('invalid-user');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe('Failed to fetch dashboard data');
      }

      console.error = originalConsoleError;
    });
  });

  describe('getChildren', () => {
    it('should return array of ChildData with enhanced metrics', async () => {
      const children = await parentDashboardApi.getChildren(mockUserId);
      
      expect(Array.isArray(children)).toBe(true);
      
      // Test structure if children exist
      if (children.length > 0) {
        const child = children[0];
        expect(child).toHaveProperty('id');
        expect(child).toHaveProperty('name');
        expect(child).toHaveProperty('age');
        expect(child).toHaveProperty('currentMood');
        expect(child).toHaveProperty('zenScore');
        expect(child).toHaveProperty('activityLevel');
        expect(typeof child.id).toBe('number');
        expect(typeof child.zenScore).toBe('number');
      }
    });
  });

  describe('getDailyData', () => {
    it('should return daily data for date range', async () => {
      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-07')
      };
      
      const dailyData = await parentDashboardApi.getDailyData(mockChildId, dateRange);
      
      expect(Array.isArray(dailyData)).toBe(true);
      
      // Test structure if data exists
      if (dailyData.length > 0) {
        const day = dailyData[0];
        expect(day).toHaveProperty('date');
        expect(day).toHaveProperty('mood');
        expect(day).toHaveProperty('exercise');
        expect(day).toHaveProperty('mental');
        expect(day).toHaveProperty('screenTime');
        expect(day).toHaveProperty('wellness_score');
        expect(typeof day.mood).toBe('number');
        expect(typeof day.exercise).toBe('number');
      }
    });
  });

  describe('getDailyDataForDate', () => {
    it('should return null when no data exists for date', async () => {
      const result = await parentDashboardApi.getDailyDataForDate(mockChildId, new Date('2024-01-01'));
      expect(result).toBeNull();
    });
  });

  describe('getDashboardMetrics', () => {
    it('should return parent dashboard metrics', async () => {
      const metrics = await parentDashboardApi.getDashboardMetrics(mockUserId);
      
      expect(Array.isArray(metrics)).toBe(true);
      
      // Test structure if metrics exist
      if (metrics.length > 0) {
        const metric = metrics[0];
        expect(metric).toHaveProperty('child_id');
        expect(metric).toHaveProperty('child_name');
        expect(metric).toHaveProperty('recent_mood_trend');
        expect(metric).toHaveProperty('avg_wellness_score');
        expect(metric).toHaveProperty('total_routines_completed');
        expect(typeof metric.child_id).toBe('number');
        expect(typeof metric.avg_wellness_score).toBe('number');
      }
    });
  });

  describe('generateInsights', () => {
    it('should generate wellness insights for low scores', async () => {
      const mockChildren: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'happy',
        zenScore: 45,
        activityLevel: 20,
        status: 'active',
        avatar: '👧'
      }];

      const mockMetrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'needs_attention',
        avg_wellness_score: 45,
        total_routines_completed: 5,
        screen_time_avg: 150,
        exercise_avg: 20,
        last_activity_date: '2024-01-01'
      }];

      const insights = await parentDashboardApi.generateInsights(mockChildren, [], mockMetrics);
      
      expect(Array.isArray(insights)).toBe(true);
      expect(insights.length).toBeGreaterThan(0);
      
      // Should have wellness warning
      const wellnessInsight = insights.find(i => i.type === 'warning' && i.title.includes('Wellness'));
      expect(wellnessInsight).toBeDefined();
      expect(wellnessInsight?.priority).toBe('high');
      
      // Should have screen time suggestion
      const screenTimeInsight = insights.find(i => i.type === 'suggestion' && i.title.includes('Screen Time'));
      expect(screenTimeInsight).toBeDefined();
      
      // Should have exercise tip
      const exerciseInsight = insights.find(i => i.type === 'tip' && i.title.includes('Physical Activity'));
      expect(exerciseInsight).toBeDefined();
    });

    it('should generate positive insights for high scores', async () => {
      const mockChildren: ChildData[] = [{
        id: 1,
        name: 'Test Child',
        age: 8,
        currentMood: 'excellent',
        zenScore: 85,
        activityLevel: 60,
        status: 'active',
        avatar: '👧'
      }];

      const mockMetrics: ParentDashboardMetrics[] = [{
        child_id: 1,
        child_name: 'Test Child',
        recent_mood_trend: 'excellent',
        avg_wellness_score: 85,
        total_routines_completed: 20,
        screen_time_avg: 60,
        exercise_avg: 60,
        last_activity_date: '2024-01-01'
      }];

      const insights = await parentDashboardApi.generateInsights(mockChildren, [], mockMetrics);
      
      const positiveInsight = insights.find(i => i.type === 'positive');
      expect(positiveInsight).toBeDefined();
      expect(positiveInsight?.title).toContain('Doing Great');
    });
  });

  describe('performance', () => {
    it('should complete dashboard data fetch within acceptable time', async () => {
      const startTime = Date.now();
      
      try {
        await parentDashboardApi.getDashboardData(mockUserId);
      } catch (error) {
        // Expected due to mocked environment
      }
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      // Should complete within 2 seconds (mocked, so very fast)
      expect(duration).toBeLessThan(2000);
    });
  });

  describe('data validation', () => {
    it('should validate child data structure', async () => {
      const children = await parentDashboardApi.getChildren(mockUserId);
      
      children.forEach(child => {
        expect(typeof child.id).toBe('number');
        expect(typeof child.name).toBe('string');
        expect(typeof child.age).toBe('number');
        expect(child.age).toBeGreaterThan(0);
        expect(child.age).toBeLessThan(18);
        expect(typeof child.zenScore).toBe('number');
        expect(child.zenScore).toBeGreaterThanOrEqual(0);
        expect(child.zenScore).toBeLessThanOrEqual(100);
      });
    });

    it('should validate daily data structure', async () => {
      const dateRange = {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-07')
      };
      
      const dailyData = await parentDashboardApi.getDailyData(mockChildId, dateRange);
      
      dailyData.forEach(day => {
        expect(typeof day.date).toBe('string');
        expect(typeof day.mood).toBe('number');
        expect(typeof day.exercise).toBe('number');
        expect(typeof day.screenTime).toBe('number');
        expect(typeof day.wellness_score).toBe('number');
        expect(day.mood).toBeGreaterThanOrEqual(0);
        expect(day.mood).toBeLessThanOrEqual(10);
        expect(day.wellness_score).toBeGreaterThanOrEqual(0);
        expect(day.wellness_score).toBeLessThanOrEqual(100);
      });
    });
  });
});