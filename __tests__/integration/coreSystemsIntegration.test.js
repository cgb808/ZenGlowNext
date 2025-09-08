/**
 * Integration Tests for ZenGlow Core Systems
 * Tests how different modules work together
 */

import { calculateZenScore, generateZenInsights } from '../../src/utils/zenScore';
import { validateContentSafety, validateSessionSecurity } from '../../src/utils/childSafety';
import { testChildren, testDailyData, testAudioFiles } from '../../testData/fixtures';

describe('ZenGlow Integration Tests', () => {
  describe('Zen Score to Content Safety Integration', () => {
    it('generates safe insights based on zen score calculations', () => {
      // Calculate zen score
      const activities = [
        { zenScoreContribution: 20 },
        { zenScoreContribution: 15 },
      ];
      const zenScore = calculateZenScore({
        activities,
        mood: 'happy',
        screenTime: 30,
        sleepQuality: 'good',
      });

      // Generate insights
      const insights = generateZenInsights({
        currentScore: zenScore,
        activities,
        mood: 'happy',
      });

      // Validate that all insight messages are child-safe
      insights.forEach(insight => {
        const contentSafety = validateContentSafety(insight.message, 8);
        expect(contentSafety.isSafe).toBe(true);
        expect(contentSafety.ageAppropriate).toBe(true);
      });

      expect(insights.length).toBeGreaterThan(0);
      expect(zenScore).toBeGreaterThan(70); // Should be high with good activities and mood
    });

    it('provides safe recommendations for low zen scores', () => {
      const lowZenScore = calculateZenScore({
        activities: [],
        mood: 'sad',
        screenTime: 120,
        sleepQuality: 'poor',
      });

      const insights = generateZenInsights({
        currentScore: lowZenScore,
        activities: [],
        mood: 'sad',
      });

      // All recommendations should be child-safe and appropriate
      insights.forEach(insight => {
        const contentSafety = validateContentSafety(insight.message, 8);
        expect(contentSafety.isSafe).toBe(true);
        
        // Should be suggestions to help improve
        if (insight.type === 'suggestion') {
          expect(insight.message).toMatch(/Try|Complete|Consider/i);
        }
      });

      expect(lowZenScore).toBeLessThan(50);
    });
  });

  describe('Session Security and Child Data Integration', () => {
    it('validates complete child session workflow', () => {
      const child = testChildren[0];
      const session = {
        userId: 'user-123',
        childId: child.id,
        parentId: child.parentId,
        startedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        expiresAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
        failedAttempts: 0,
      };

      // Validate session security
      const sessionSecurity = validateSessionSecurity(session);
      expect(sessionSecurity.isSecure).toBe(true);
      expect(sessionSecurity.shouldTerminate).toBe(false);

      // Calculate zen score for the child
      const dailyData = testDailyData['2024-08-14'];
      const zenScore = calculateZenScore({
        activities: dailyData.activities,
        mood: dailyData.mood,
        screenTime: dailyData.screenTime / 60, // Convert to minutes
        sleepQuality: dailyData.sleepQuality,
      });

      // Verify the calculated score matches expected range
      expect(zenScore).toBeGreaterThanOrEqual(0);
      expect(zenScore).toBeLessThanOrEqual(100);

      // Generate insights based on the score
      const insights = generateZenInsights({
        currentScore: zenScore,
        activities: dailyData.activities,
        mood: dailyData.mood,
      });

      // All insights should be safe for the child's age
      insights.forEach(insight => {
        const contentSafety = validateContentSafety(insight.message, child.age);
        expect(contentSafety.isSafe).toBe(true);
        expect(contentSafety.ageAppropriate).toBe(true);
      });
    });

    it('handles age-appropriate content filtering across systems', () => {
      const youngerChild = { ...testChildren[0], age: 6 };
      const olderChild = { ...testChildren[1], age: 11 };

      const audioFiles = testAudioFiles.filter(audio => audio.isChildSafe);

      audioFiles.forEach(audio => {
        // Check content safety for different ages
        const youngerChildSafety = validateContentSafety(audio.title, youngerChild.age);
        const olderChildSafety = validateContentSafety(audio.title, olderChild.age);

        // All content should be safe
        expect(youngerChildSafety.isSafe).toBe(true);
        expect(olderChildSafety.isSafe).toBe(true);

        // Age appropriateness may vary
        if (audio.ageRating === '6+') {
          expect(youngerChildSafety.ageAppropriate).toBe(true);
          expect(olderChildSafety.ageAppropriate).toBe(true);
        }
      });
    });
  });

  describe('Complete Activity Workflow Integration', () => {
    it('processes complete activity completion workflow', () => {
      const child = testChildren[0];
      const activity = {
        id: 'breathing-exercise-1',
        type: 'breathing',
        duration: 300, // 5 minutes
        completedAt: new Date().toISOString(),
        zenScoreContribution: 25,
      };

      // 1. Validate activity content is safe
      const activityTitle = 'Rainbow Breathing Exercise';
      const contentSafety = validateContentSafety(activityTitle, child.age);
      expect(contentSafety.isSafe).toBe(true);
      expect(contentSafety.ageAppropriate).toBe(true);

      // 2. Calculate zen score contribution
      const previousScore = 60;
      const newScore = calculateZenScore({
        activities: [activity],
        mood: 'calm',
        screenTime: 20,
        sleepQuality: 'good',
      });

      expect(newScore).toBeGreaterThan(previousScore);

      // 3. Generate insights for progress
      const insights = generateZenInsights({
        currentScore: newScore,
        activities: [activity],
        previousScores: [previousScore],
      });

      // 4. Validate all insights are appropriate
      insights.forEach(insight => {
        const insightSafety = validateContentSafety(insight.message, child.age);
        expect(insightSafety.isSafe).toBe(true);
        expect(insight.icon).toBeDefined();
      });

      // Should have positive feedback for completing activity
      expect(insights.some(insight => 
        insight.type === 'positive' || insight.type === 'neutral'
      )).toBe(true);
    });

    it('maintains child safety throughout mood tracking workflow', () => {
      const child = testChildren[0];
      const moods = ['happy', 'calm', 'excited', 'sad'];

      moods.forEach(mood => {
        // Calculate zen score for each mood
        const zenScore = calculateZenScore({
          activities: [{ zenScoreContribution: 15 }],
          mood,
          screenTime: 30,
          sleepQuality: 'good',
        });

        // Generate mood-specific insights
        const insights = generateZenInsights({
          currentScore: zenScore,
          mood,
          activities: [{ zenScoreContribution: 15 }],
        });

        // All insights should be appropriate regardless of mood
        insights.forEach(insight => {
          const contentSafety = validateContentSafety(insight.message, child.age);
          expect(contentSafety.isSafe).toBe(true);
          
          // Even for sad moods, suggestions should be positive and helpful
          if (mood === 'sad' && insight.type === 'suggestion') {
            expect(insight.message).not.toContain('bad');
            expect(insight.message).not.toContain('wrong');
          }
        });
      });
    });
  });

  describe('Error Handling Integration', () => {
    it('maintains safety during error conditions', () => {
      // Simulate various error conditions
      const errorScenarios = [
        { zenScore: -1, expectedValid: false },
        { zenScore: 150, expectedValid: false },
        { zenScore: null, expectedValid: false },
        { zenScore: 75, expectedValid: true },
      ];

      errorScenarios.forEach(scenario => {
        let insights = [];
        let isValidScore = false;

        try {
          isValidScore = typeof scenario.zenScore === 'number' && 
                        scenario.zenScore >= 0 && 
                        scenario.zenScore <= 100;
          
          if (isValidScore) {
            insights = generateZenInsights({
              currentScore: scenario.zenScore,
              activities: [],
            });
          }
        } catch (error) {
          // Errors should be handled gracefully
          expect(error).toBeInstanceOf(Error);
        }

        expect(isValidScore).toBe(scenario.expectedValid);

        if (isValidScore) {
          // Any generated insights should still be safe
          insights.forEach(insight => {
            const contentSafety = validateContentSafety(insight.message, 8);
            expect(contentSafety.isSafe).toBe(true);
          });
        }
      });
    });

    it('handles invalid user input safely across systems', () => {
      const safeInput = 'I feel happy and calm today';
      const unsafeInput = 'This violent and scary content should be blocked';
      
      // Test safe input
      const safeContentCheck = validateContentSafety(safeInput, 8);
      expect(safeContentCheck.isSafe).toBe(true);
      
      // Test unsafe input
      const unsafeContentCheck = validateContentSafety(unsafeInput, 8);
      expect(unsafeContentCheck.isSafe).toBe(false);
      
      // Test invalid inputs
      expect(validateContentSafety(null, 8).isSafe).toBe(false);
      expect(validateContentSafety(undefined, 8).isSafe).toBe(false);
    });
  });

  describe('Performance Integration', () => {
    it('maintains performance while ensuring safety', async () => {
      // Process multiple children's data simultaneously
      const promises = testChildren.map(async (child) => {
        // Validate content safety
        const contentSafety = validateContentSafety(
          `Welcome ${child.name}, let's start your zen journey!`, 
          child.age
        );
        
        // Calculate zen score
        const zenScore = calculateZenScore({
          activities: [{ zenScoreContribution: 20 }],
          mood: 'happy',
          screenTime: 30,
          sleepQuality: 'good',
        });
        
        // Generate insights
        const insights = generateZenInsights({
          currentScore: zenScore,
          activities: [{ zenScoreContribution: 20 }],
        });
        
        return {
          child,
          contentSafety,
          zenScore,
          insights,
        };
      });
      
      const results = await Promise.all(promises);
      
      // All results should be valid and safe
      expect(results.length).toBe(testChildren.length);
      results.forEach(result => {
        expect(result.contentSafety.isSafe).toBe(true);
        expect(result.zenScore).toBeGreaterThanOrEqual(0);
        expect(result.zenScore).toBeLessThanOrEqual(100);
        expect(result.insights.length).toBeGreaterThan(0);
      });
    });
  });
});