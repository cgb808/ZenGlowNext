/**
 * Unit Tests for Recommendation Service
 */

import { generateRecommendations, RecommendationEngine } from '../../../src/services/recommendations/recommendationService';
import type { RecommendationContext, RecommendationGenerationOptions } from '../../../types/recommendations';
import { isRecommendationsEnabled } from '../../../src/utils/SecurityConfig';

// Mock the feature flag
jest.mock('../../../src/utils/SecurityConfig', () => ({
  isRecommendationsEnabled: jest.fn()
}));

// Mock uuid
jest.mock('uuid', () => ({
  v4: () => 'mock-uuid-1234'
}));

const mockIsRecommendationsEnabled = isRecommendationsEnabled as jest.MockedFunction<typeof isRecommendationsEnabled>;

describe('RecommendationService', () => {
  let engine: RecommendationEngine;
  const mockChildId = 'child-123';

  beforeEach(() => {
    engine = new RecommendationEngine(true);
    mockIsRecommendationsEnabled.mockReturnValue(true);
    jest.clearAllMocks();
  });

  describe('generateRecommendations', () => {
    it('should return empty array when feature flag is disabled', async () => {
      mockIsRecommendationsEnabled.mockReturnValue(false);
      
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30,
          avgMood: 4,
          routinesCompleted: 1
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 5
        }
      };

      const result = await generateRecommendations(mockChildId, mockContext);
      expect(result).toEqual([]);
    });

    it('should generate wellness improvement recommendation for low wellness score and downward trend', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30,
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 2
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({
        type: 'mindfulness',
        title: 'Wellness Boost Needed',
        priority: 'high',
        tags: expect.arrayContaining(['wellness', 'mindfulness']),
        sourceSignals: expect.arrayContaining(['low_wellness_score', 'downward_trend'])
      });
    });

    it('should generate moderate wellness recommendation for moderate scores', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 55,
          avgMood: 5,
          routinesCompleted: 2
        },
        engagementSignals: {
          streaks: 1,
          missedRoutines: 1
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      expect(result.length).toBeGreaterThan(0);
      const wellnessRec = result.find(r => r.type === 'wellness_improvement');
      expect(wellnessRec).toBeDefined();
      expect(wellnessRec?.priority).toBe('medium');
    });

    it('should generate chronotype-based recommendation for night owl with low routine completion', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 6,
          routinesCompleted: 2
        },
        chronotype: {
          type: 'night_owl',
          confidence: 0.8
        },
        engagementSignals: {
          streaks: 1,
          missedRoutines: 1
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const chronotypeRec = result.find(r => r.type === 'routine_adjustment');
      expect(chronotypeRec).toBeDefined();
      expect(chronotypeRec?.title).toBe('Evening Prep Routine');
      expect(chronotypeRec?.tags).toContain('night_owl');
      expect(chronotypeRec?.sourceSignals).toContain('night_owl_chronotype');
    });

    it('should generate early bird recommendation', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 6,
          routinesCompleted: 1
        },
        chronotype: {
          type: 'early_bird',
          confidence: 0.9
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 2
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const chronotypeRec = result.find(r => r.type === 'routine_adjustment');
      expect(chronotypeRec).toBeDefined();
      expect(chronotypeRec?.title).toBe('Morning Routine Optimization');
      expect(chronotypeRec?.tags).toContain('early_bird');
    });

    it('should generate playful activity suggestion for flat mood and low engagement', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 5.5, // Neutral mood
          routinesCompleted: 3
        },
        engagementSignals: {
          streaks: 1,
          missedRoutines: 1,
          engagementScore: 0.3 // Low engagement
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const activityRec = result.find(r => r.type === 'activity_suggestion');
      expect(activityRec).toBeDefined();
      expect(activityRec?.title).toBe('Fun Activity Break');
      expect(activityRec?.tags).toContain('playful');
      expect(activityRec?.sourceSignals).toContain('flat_mood');
      expect(activityRec?.sourceSignals).toContain('low_engagement');
    });

    it('should generate screen time management recommendation for high screen time', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 6,
          routinesCompleted: 3
        },
        engagementSignals: {
          streaks: 2,
          missedRoutines: 0
        },
        screenTimeMinutes: 150 // 2.5 hours
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const screenTimeRec = result.find(r => r.type === 'screen_time_management');
      expect(screenTimeRec).toBeDefined();
      expect(screenTimeRec?.title).toBe('Device-Free Time');
      expect(screenTimeRec?.priority).toBe('medium');
      expect(screenTimeRec?.tags).toContain('screen_time');
    });

    it('should generate high priority screen time recommendation for very high usage', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 6,
          routinesCompleted: 3
        },
        engagementSignals: {
          streaks: 2,
          missedRoutines: 0
        },
        screenTimeMinutes: 200 // Over 3 hours
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const screenTimeRec = result.find(r => r.type === 'screen_time_management');
      expect(screenTimeRec).toBeDefined();
      expect(screenTimeRec?.priority).toBe('high');
    });

    it('should generate fresh start recommendation for no streaks and multiple missed routines', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 6,
          routinesCompleted: 1
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 5
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const engagementRec = result.find(r => r.type === 'engagement_boost' && r.title === 'Fresh Start Approach');
      expect(engagementRec).toBeDefined();
      expect(engagementRec?.priority).toBe('high');
      expect(engagementRec?.sourceSignals).toContain('no_streaks');
      expect(engagementRec?.sourceSignals).toContain('multiple_missed_routines');
    });

    it('should generate momentum building recommendation for small streaks', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 70,
          avgMood: 6,
          routinesCompleted: 3
        },
        engagementSignals: {
          streaks: 2,
          missedRoutines: 1
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      const momentumRec = result.find(r => r.type === 'engagement_boost' && r.title === 'Building Momentum');
      expect(momentumRec).toBeDefined();
      expect(momentumRec?.priority).toBe('low');
      expect(momentumRec?.tags).toContain('momentum');
    });
  });

  describe('filtering and options', () => {
    it('should apply priority filter', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30, // Will generate high priority recommendation
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 2, // Will generate low priority recommendation
          missedRoutines: 1
        }
      };

      const options: RecommendationGenerationOptions = {
        priorityFilter: ['high']
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext, options);
      
      expect(result.length).toBeGreaterThan(0);
      result.forEach(rec => {
        expect(rec.priority).toBe('high');
      });
    });

    it('should apply type filter', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30,
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 5
        }
      };

      const options: RecommendationGenerationOptions = {
        typeFilter: ['mindfulness']
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext, options);
      
      expect(result.length).toBeGreaterThan(0);
      result.forEach(rec => {
        expect(rec.type).toBe('mindfulness');
      });
    });

    it('should exclude recommendations with specified tags', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30,
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 5
        }
      };

      const options: RecommendationGenerationOptions = {
        excludeTags: ['mindfulness']
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext, options);
      
      result.forEach(rec => {
        expect(rec.tags).not.toContain('mindfulness');
      });
    });

    it('should limit the number of recommendations', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30,
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 5
        },
        screenTimeMinutes: 150
      };

      const options: RecommendationGenerationOptions = {
        maxRecommendations: 2
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext, options);
      
      expect(result.length).toBeLessThanOrEqual(2);
    });

    it('should sort by priority (high to low)', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30, // High priority
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 2, // Low priority
          missedRoutines: 1
        },
        chronotype: {
          type: 'night_owl' // Medium priority
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      if (result.length > 1) {
        for (let i = 0; i < result.length - 1; i++) {
          const currentPriority = getPriorityValue(result[i].priority);
          const nextPriority = getPriorityValue(result[i + 1].priority);
          expect(currentPriority).toBeGreaterThanOrEqual(nextPriority);
        }
      }
    });
  });

  describe('error handling', () => {
    it('should handle errors gracefully and return empty array', async () => {
      // Create a context that might cause issues
      const mockContext = null as any;

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      expect(result).toEqual([]);
    });
  });

  describe('recommendation metadata', () => {
    it('should include proper metadata in recommendations', async () => {
      const mockContext: RecommendationContext = {
        childId: mockChildId,
        recentMetrics: {
          wellnessScore: 30,
          avgMood: 4,
          routinesCompleted: 1,
          trend: 'downward'
        },
        engagementSignals: {
          streaks: 0,
          missedRoutines: 5
        }
      };

      const result = await engine.generateRecommendations(mockChildId, mockContext);
      
      expect(result.length).toBeGreaterThan(0);
      
      result.forEach(rec => {
        expect(rec).toHaveProperty('id');
        expect(rec).toHaveProperty('type');
        expect(rec).toHaveProperty('title');
        expect(rec).toHaveProperty('message');
        expect(rec).toHaveProperty('priority');
        expect(rec).toHaveProperty('tags');
        expect(rec).toHaveProperty('sourceSignals');
        expect(rec).toHaveProperty('generatedAt');
        expect(rec.id).toBe('mock-uuid-1234'); // UUID should match mock
        expect(typeof rec.generatedAt).toBe('string');
        expect(rec.tags).toBeInstanceOf(Array);
        expect(rec.sourceSignals).toBeInstanceOf(Array);
      });
    });
  });
});

// Helper function for priority sorting test
function getPriorityValue(priority: 'high' | 'medium' | 'low'): number {
  switch (priority) {
    case 'high': return 3;
    case 'medium': return 2;
    case 'low': return 1;
    default: return 0;
  }
}