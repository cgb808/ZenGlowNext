/**
 * Tests for Zen Score Calculation Utilities
 */

import {
  calculateZenScore,
  isValidZenScore,
  calculateWeeklyAverage,
  getZenScoreTrend,
  generateZenInsights,
} from '../../src/utils/zenScore';

describe('zenScore utilities', () => {
  describe('calculateZenScore', () => {
    it('calculates base score with no activities', () => {
      const result = calculateZenScore({});
      expect(result).toBe(55); // 50 base + 5 for fair sleep
    });

    it('adds activity points correctly', () => {
      const activities = [
        { zenScoreContribution: 10 },
        { zenScoreContribution: 15 },
      ];
      const result = calculateZenScore({ activities });
      expect(result).toBe(80); // 50 base + 25 activity + 5 sleep
    });

    it('caps activity points at 30', () => {
      const activities = [
        { zenScoreContribution: 20 },
        { zenScoreContribution: 20 },
        { zenScoreContribution: 20 },
      ];
      const result = calculateZenScore({ activities });
      expect(result).toBe(85); // 50 base + 30 activity (capped) + 5 sleep
    });

    it('applies mood bonuses correctly', () => {
      expect(calculateZenScore({ mood: 'happy' })).toBe(75); // +20 for happy
      expect(calculateZenScore({ mood: 'calm' })).toBe(70); // +15 for calm
      expect(calculateZenScore({ mood: 'excited' })).toBe(65); // +10 for excited
      expect(calculateZenScore({ mood: 'neutral' })).toBe(55); // +0 for neutral
    });

    it('applies mood penalties correctly', () => {
      expect(calculateZenScore({ mood: 'sad' })).toBe(45); // -10 for sad
      expect(calculateZenScore({ mood: 'angry' })).toBe(40); // -15 for angry
    });

    it('applies screen time penalties', () => {
      expect(calculateZenScore({ screenTime: 60 })).toBe(45); // -10 for 1 hour
      expect(calculateZenScore({ screenTime: 120 })).toBe(35); // -20 for 2 hours (max penalty)
      expect(calculateZenScore({ screenTime: 180 })).toBe(35); // Still -20 (capped)
    });

    it('applies sleep quality bonuses/penalties', () => {
      expect(calculateZenScore({ sleepQuality: 'excellent' })).toBe(65); // +15
      expect(calculateZenScore({ sleepQuality: 'good' })).toBe(60); // +10
      expect(calculateZenScore({ sleepQuality: 'fair' })).toBe(55); // +5
      expect(calculateZenScore({ sleepQuality: 'poor' })).toBe(45); // -5
    });

    it('ensures score stays within 0-100 range', () => {
      // Test minimum boundary
      const lowScore = calculateZenScore({
        mood: 'angry',
        screenTime: 300,
        sleepQuality: 'poor',
      });
      expect(lowScore).toBeGreaterThanOrEqual(0);

      // Test maximum boundary  
      const activities = Array(10).fill({ zenScoreContribution: 10 });
      const highScore = calculateZenScore({
        activities,
        mood: 'happy',
        sleepQuality: 'excellent',
      });
      expect(highScore).toBeLessThanOrEqual(100);
    });

    it('returns integer values', () => {
      const result = calculateZenScore({ screenTime: 35 }); // Should create decimal
      expect(Number.isInteger(result)).toBe(true);
    });
  });

  describe('isValidZenScore', () => {
    it('returns true for valid scores', () => {
      expect(isValidZenScore(0)).toBe(true);
      expect(isValidZenScore(50)).toBe(true);
      expect(isValidZenScore(100)).toBe(true);
    });

    it('returns false for invalid scores', () => {
      expect(isValidZenScore(-1)).toBe(false);
      expect(isValidZenScore(101)).toBe(false);
      expect(isValidZenScore(50.5)).toBe(false);
      expect(isValidZenScore('50')).toBe(false);
      expect(isValidZenScore(null)).toBe(false);
      expect(isValidZenScore(undefined)).toBe(false);
    });
  });

  describe('calculateWeeklyAverage', () => {
    it('calculates average correctly', () => {
      const scores = [70, 80, 90];
      expect(calculateWeeklyAverage(scores)).toBe(80);
    });

    it('rounds to nearest integer', () => {
      const scores = [70, 80, 85];
      expect(calculateWeeklyAverage(scores)).toBe(78); // 78.33... rounded
    });

    it('filters out invalid scores', () => {
      const scores = [70, -5, 80, 150, 90];
      expect(calculateWeeklyAverage(scores)).toBe(80); // Only 70, 80, 90
    });

    it('returns 0 for empty array', () => {
      expect(calculateWeeklyAverage([])).toBe(0);
    });

    it('returns 0 for non-array input', () => {
      expect(calculateWeeklyAverage(null)).toBe(0);
      expect(calculateWeeklyAverage('invalid')).toBe(0);
    });

    it('returns 0 when all scores are invalid', () => {
      const scores = [-10, 150, 'invalid'];
      expect(calculateWeeklyAverage(scores)).toBe(0);
    });
  });

  describe('getZenScoreTrend', () => {
    it('returns "improving" for upward trend', () => {
      const scores = [40, 50, 60, 70, 80];
      expect(getZenScoreTrend(scores)).toBe('improving');
    });

    it('returns "declining" for downward trend', () => {
      const scores = [80, 70, 60, 50, 40];
      expect(getZenScoreTrend(scores)).toBe('declining');
    });

    it('returns "stable" for stable scores', () => {
      const scores = [70, 72, 68, 71, 69];
      expect(getZenScoreTrend(scores)).toBe('stable');
    });

    it('returns "stable" for insufficient data', () => {
      expect(getZenScoreTrend([70])).toBe('stable');
      expect(getZenScoreTrend([])).toBe('stable');
    });

    it('filters out invalid scores', () => {
      const scores = [40, -10, 50, 150, 70, 80];
      expect(getZenScoreTrend(scores)).toBe('improving');
    });
  });

  describe('generateZenInsights', () => {
    it('generates positive insight for high scores', () => {
      const insights = generateZenInsights({ 
        currentScore: 85,
        activities: [{ zenScoreContribution: 20 }] // Add activities to avoid the suggestion
      });
      expect(insights).toHaveLength(1);
      expect(insights[0].type).toBe('positive');
      expect(insights[0].message).toContain('Excellent');
    });

    it('generates neutral insight for medium scores', () => {
      const insights = generateZenInsights({ 
        currentScore: 65,
        activities: [{ zenScoreContribution: 15 }] // Add activities to avoid the suggestion
      });
      expect(insights).toHaveLength(1);
      expect(insights[0].type).toBe('neutral');
      expect(insights[0].message).toContain('Good');
    });

    it('generates suggestion for low scores', () => {
      const insights = generateZenInsights({ currentScore: 35 });
      expect(insights).toHaveLength(2); // Low score + no activities
      expect(insights[0].type).toBe('suggestion');
      expect(insights[1].type).toBe('suggestion');
    });

    it('suggests activities when none completed', () => {
      const insights = generateZenInsights({ 
        currentScore: 70,
        activities: []
      });
      expect(insights.some(insight => 
        insight.type === 'suggestion' && 
        insight.message.includes('activity')
      )).toBe(true);
    });

    it('praises multiple activities', () => {
      const activities = [
        { zenScoreContribution: 10 },
        { zenScoreContribution: 15 },
        { zenScoreContribution: 20 },
      ];
      const insights = generateZenInsights({ 
        currentScore: 70,
        activities
      });
      expect(insights.some(insight => 
        insight.type === 'positive' && 
        insight.message.includes('multiple activities')
      )).toBe(true);
    });

    it('recognizes improving trends', () => {
      const insights = generateZenInsights({ 
        currentScore: 80,
        previousScores: [50, 60, 70]
      });
      expect(insights.some(insight => 
        insight.type === 'positive' && 
        insight.message.includes('improving')
      )).toBe(true);
    });

    it('suggests improvement for declining trends', () => {
      const insights = generateZenInsights({ 
        currentScore: 50,
        previousScores: [80, 70, 60]
      });
      expect(insights.some(insight => 
        insight.type === 'suggestion' && 
        insight.message.includes('back up')
      )).toBe(true);
    });

    it('returns empty array for invalid score', () => {
      const insights = generateZenInsights({ currentScore: 150 });
      expect(insights).toHaveLength(0);
    });

    it('includes icons in all insights', () => {
      const insights = generateZenInsights({ 
        currentScore: 75,
        activities: [{ zenScoreContribution: 20 }],
        previousScores: [60, 65, 70]
      });
      insights.forEach(insight => {
        expect(insight.icon).toBeDefined();
        expect(typeof insight.icon).toBe('string');
      });
    });
  });
});