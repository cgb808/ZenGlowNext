/**
 * Metrics Utilities for Parent Dashboard
 * 
 * Pure utility functions for processing dashboard metrics, trends, and summaries.
 * These functions are extracted from parentDashboardApi.ts to improve testability
 * and maintainability.
 */

import type { 
  ChildData, 
  ParentDashboardMetrics, 
  Insight,
  DailyData
} from '../../types/parentDashboard';

/**
 * Maps raw child data with dashboard metrics to create enhanced ChildData
 * 
 * @param child - Raw child data from database
 * @param metrics - Dashboard metrics for all children
 * @returns Enhanced ChildData with metrics included
 */
export function mapMetricsRow(
  child: Omit<ChildData, 'currentMood' | 'zenScore' | 'activityLevel' | 'recentMoodTrend' | 'totalRoutinesCompleted' | 'screenTimeAvg' | 'exerciseAvg' | 'lastActivityDate'>,
  metrics: ParentDashboardMetrics[]
): ChildData {
  const childMetrics = metrics.find(m => m.child_id === child.id);
  
  return {
    id: child.id,
    name: child.name,
    age: child.age,
    avatar: child.avatar,
    status: child.status,
    device: child.device,
    currentMood: childMetrics?.recent_mood_trend || 'unknown',
    zenScore: Math.round(childMetrics?.avg_wellness_score || 0),
    activityLevel: childMetrics?.exercise_avg || 0,
    recentMoodTrend: childMetrics?.recent_mood_trend,
    totalRoutinesCompleted: childMetrics?.total_routines_completed,
    screenTimeAvg: childMetrics?.screen_time_avg,
    exerciseAvg: childMetrics?.exercise_avg,
    lastActivityDate: childMetrics?.last_activity_date
  };
}

/**
 * Generates insights by summarizing metrics data for children
 * 
 * @param children - Array of children data
 * @param metrics - Dashboard metrics for the children
 * @returns Array of insights based on the metrics analysis
 */
export function summarize(
  children: ChildData[],
  metrics: ParentDashboardMetrics[]
): Insight[] {
  const insights: Insight[] = [];

  for (const child of children) {
    const childMetrics = metrics.find(m => m.child_id === child.id);
    
    if (!childMetrics) continue;

    // Wellness score insights
    if (childMetrics.avg_wellness_score < 50) {
      insights.push({
        id: `wellness-${child.id}`,
        type: 'warning',
        title: `${child.name}'s Wellness Needs Attention`,
        description: `Average wellness score is ${Math.round(childMetrics.avg_wellness_score)}`,
        priority: 'high',
        actionable: true,
        data: { childId: child.id, score: childMetrics.avg_wellness_score }
      });
    } else if (childMetrics.avg_wellness_score >= 80) {
      insights.push({
        id: `wellness-good-${child.id}`,
        type: 'positive',
        title: `${child.name} is Doing Great!`,
        description: `Excellent wellness score of ${Math.round(childMetrics.avg_wellness_score)}`,
        priority: 'low',
        actionable: false,
        data: { childId: child.id, score: childMetrics.avg_wellness_score }
      });
    }

    // Screen time insights
    if (childMetrics.screen_time_avg > 120) {
      insights.push({
        id: `screen-time-${child.id}`,
        type: 'suggestion',
        title: `Consider Reducing ${child.name}'s Screen Time`,
        description: `Averaging ${childMetrics.screen_time_avg} minutes daily`,
        priority: 'medium',
        actionable: true,
        data: { childId: child.id, screenTime: childMetrics.screen_time_avg }
      });
    }

    // Exercise insights
    if (childMetrics.exercise_avg < 30) {
      insights.push({
        id: `exercise-${child.id}`,
        type: 'tip',
        title: `${child.name} Could Use More Physical Activity`,
        description: `Only ${childMetrics.exercise_avg} minutes of exercise daily`,
        priority: 'medium',
        actionable: true,
        data: { childId: child.id, exercise: childMetrics.exercise_avg }
      });
    }
  }

  return insights;
}

/**
 * Determines the trend direction for a series of numeric values
 * 
 * @param values - Array of numeric values in chronological order
 * @param threshold - Minimum change percentage to consider significant (default: 5%)
 * @returns Trend direction: 'improving', 'declining', or 'stable'
 */
export function trend(values: number[], threshold: number = 5): 'improving' | 'declining' | 'stable' {
  if (!Array.isArray(values) || values.length < 2) {
    return 'stable';
  }

  // Filter out null/undefined values
  const validValues = values.filter(v => typeof v === 'number' && !isNaN(v));
  
  if (validValues.length < 2) {
    return 'stable';
  }

  const first = validValues[0];
  const last = validValues[validValues.length - 1];
  const percentChange = ((last - first) / first) * 100;

  if (percentChange > threshold) {
    return 'improving';
  } else if (percentChange < -threshold) {
    return 'declining';
  } else {
    return 'stable';
  }
}

/**
 * Analyzes trend in wellness scores for a child over time
 * 
 * @param dailyData - Array of daily data entries in chronological order
 * @returns Trend analysis result with direction and percentage change
 */
export function analyzeWellnessTrend(dailyData: DailyData[]): {
  direction: 'improving' | 'declining' | 'stable';
  percentChange: number;
  dataPoints: number;
} {
  const wellnessScores = dailyData
    .filter(d => d.wellness_score > 0)
    .map(d => d.wellness_score);
  
  if (wellnessScores.length < 2) {
    return {
      direction: 'stable',
      percentChange: 0,
      dataPoints: wellnessScores.length
    };
  }

  const first = wellnessScores[0];
  const last = wellnessScores[wellnessScores.length - 1];
  const percentChange = ((last - first) / first) * 100;
  
  return {
    direction: trend(wellnessScores),
    percentChange: Math.round(percentChange * 100) / 100,
    dataPoints: wellnessScores.length
  };
}

/**
 * Calculates average values from dashboard metrics
 * 
 * @param metrics - Array of dashboard metrics
 * @returns Summary statistics across all children
 */
export function calculateMetricsSummary(metrics: ParentDashboardMetrics[]): {
  avgWellnessScore: number;
  avgScreenTime: number;
  avgExercise: number;
  totalRoutines: number;
  childrenCount: number;
} {
  if (metrics.length === 0) {
    return {
      avgWellnessScore: 0,
      avgScreenTime: 0,
      avgExercise: 0,
      totalRoutines: 0,
      childrenCount: 0
    };
  }

  const totals = metrics.reduce((acc, metric) => ({
    wellness: acc.wellness + (metric.avg_wellness_score || 0),
    screenTime: acc.screenTime + (metric.screen_time_avg || 0),
    exercise: acc.exercise + (metric.exercise_avg || 0),
    routines: acc.routines + (metric.total_routines_completed || 0)
  }), { wellness: 0, screenTime: 0, exercise: 0, routines: 0 });

  return {
    avgWellnessScore: Math.round(totals.wellness / metrics.length),
    avgScreenTime: Math.round(totals.screenTime / metrics.length),
    avgExercise: Math.round(totals.exercise / metrics.length),
    totalRoutines: totals.routines,
    childrenCount: metrics.length
  };
}