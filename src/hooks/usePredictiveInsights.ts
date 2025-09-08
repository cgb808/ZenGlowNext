// =================================================================================
// PREDICTIVE INSIGHTS HOOK - The "Agent" Brain
// =================================================================================
// Purpose: Custom React hook that analyzes data and generates actionable insights
// This is your "small-scale predictive agent" for the Parent Dashboard

import { useEffect, useState } from 'react';
import { parentDashboardApi } from '../services/parentDashboardApi';
import { DailyData, DailyLimits, Insight } from '../../types/parentDashboard';

export const usePredictiveInsights = (
  dailyData: { [key: string]: DailyData },
  childName: string,
  dailyLimits: { [key: string]: DailyLimits },
): Insight[] => {
  const [insights, setInsights] = useState<Insight[]>([]);

  useEffect(() => {
    const generateInsights = async () => {
      if (!childName || !dailyLimits[childName]) {
        setInsights([]);
        return;
      }

      const newInsights: Insight[] = [];
      const today = new Date();

      // Get the last 4 days of data for trend analysis
      const recentDaysData = await Promise.all(
        Array.from({ length: 4 }, async (_, i) => {
          const date = new Date(today);
          date.setDate(today.getDate() - i);
          return await parentDashboardApi.getDailyDataForDate(date);
        }),
      );

      // Filter out null values and reverse to get chronological order (oldest to newest)
      const recentDays = recentDaysData.filter((data): data is DailyData => data !== null).reverse();

      if (recentDays.length < 4) {
        console.log('Insufficient data for insights generation');
        return;
      }

      // TODO: Fix type issues with dailyLimits structure
      // Screen Time Trend Analysis (temporarily disabled)
      /*
      const screenTimeTrend =
        recentDays[3].screenTime > recentDays[2].screenTime &&
        recentDays[2].screenTime > recentDays[1].screenTime;
      if (screenTimeTrend && recentDays[3] && dailyLimits[childName] && recentDays[3].screenTime > (dailyLimits[childName].screenTime as number) * 0.8) {
        newInsights.push({
          id: `screen-time-warning-${Date.now()}`,
          type: 'warning',
          title: 'Heads-Up: Screen Time Increasing',
          description: `${childName}'s screen time has been rising for 3 days. Consider planning a non-screen activity to keep it in balance.`,
          message: `${childName}'s screen time has been rising for 3 days. Consider planning a non-screen activity to keep it in balance.`,
          priority: 'medium',
          actionable: true,
        });
      }
      */

      // TODO: Fix type issues with dailyLimits structure  
      // Exercise Trend Analysis (temporarily disabled)
      /*
      const exerciseTrend =
        recentDays[3] && recentDays[2] && recentDays[1] &&
        recentDays[3].exercise < recentDays[2].exercise &&
        recentDays[2].exercise < recentDays[1].exercise;
      if (exerciseTrend && recentDays[3] && dailyLimits[childName] && recentDays[3].exercise < (dailyLimits[childName].exercise as number) * 0.5) {
        newInsights.push({
          id: `exercise-suggestion-${Date.now()}`,
          type: 'suggestion',
          title: 'Suggestion: Boost Activity',
          description: `We've noticed ${childName}'s exercise has been lower than usual. A short walk or bike ride today could make a positive difference.`,
          message: `We've noticed ${childName}'s exercise has been lower than usual. A short walk or bike ride today could make a positive difference.`,
          priority: 'medium',
          actionable: true,
        });
      }
      */

      // TODO: Fix type issues with dailyLimits structure
      // Positive Streak Recognition (temporarily disabled)
      /*
      const exerciseStreak = dailyLimits[childName] ? recentDays
        .slice(1)
        .every((day: DailyData) => day.exercise >= (dailyLimits[childName].exercise as number)) : false;
      if (exerciseStreak) {
        newInsights.push({
          id: `exercise-positive-${Date.now()}`,
          type: 'positive',
          title: 'Great Momentum!',
          description: `${childName} has met the exercise goal for 3 days in a row. Keep up the fantastic work!`,
          message: `${childName} has met the exercise goal for 3 days in a row. Keep up the fantastic work!`,
          priority: 'low',
          actionable: false,
        });
      }
      */

      // Mental Wellbeing Pattern
      const mentalAverage = recentDays.length > 0 ?
        recentDays.reduce((sum: number, day: DailyData) => sum + day.mental, 0) / recentDays.length : 0;
      if (mentalAverage < 5) {
        newInsights.push({
          id: `mental-wellness-${Date.now()}`,
          type: 'suggestion',
          title: 'Focus on Mental Wellness',
          description: `${childName}'s mental wellbeing scores have been lower recently. Consider meditation or relaxation activities.`,
          message: `${childName}'s mental wellbeing scores have been lower recently. Consider meditation or relaxation activities.`,
          priority: 'high',
          actionable: true,
        });
      }

      setInsights(newInsights);
    };

    generateInsights();
  }, [dailyData, childName, dailyLimits]);

  return insights;
};
