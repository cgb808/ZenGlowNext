/**
 * =================================================================================
 * PARENT DASHBOARD DATA MANAGEMENT HOOK
 * =================================================================================
 * Purpose: Data loading, caching, and management for Parent Dashboard
 * Used By: ParentDashboardCore component
 * Dependencies: parentDashboardApi, emotionalSystem utilities
 *
 * Manages:
 * - Initial data loading (children, supplements, daily data)
 * - Emotional analysis and pattern recognition
 * - Data caching and updates
 * - Error handling and loading states
 * =================================================================================
 */

import { useEffect } from 'react';
import { usePredictiveInsights } from '../../../hooks/usePredictiveInsights';
import { parentDashboardApi } from '../../../services/parentDashboardApi';
import {
  Child,
  DailyData,
  DailyLimits,
  EmotionalChildState,
  EmotionType,
} from '../../../types/parentDashboard';
import { analyzeEmotionalPattern, createZenMoonState } from '../../../utils/emotionalSystem';
import { formatDateKey } from '../../../utils/parentDashboardUtils';
import { ParentDashboardState } from './useParentDashboardState';

export interface ParentDashboardDataActions {
  loadInitialData: () => Promise<void>;
  refreshData: () => Promise<void>;
  loadDailyDataForDate: (date: Date) => Promise<DailyData>;
  insights: any; // From usePredictiveInsights
}

/**
 * Custom hook for managing Parent Dashboard data operations
 * Handles all data loading, caching, and emotional analysis
 */
export const useParentDashboardData = (state: ParentDashboardState): ParentDashboardDataActions => {
  const {
    setChildren,
    setSupplements,
    setDailyData,
    setDailyLimits,
    setEmotionalStates,
    setZenMoonState,
    setSelectedEmotion,
    setSelectedChild,
    setIsLoading,
    dailyData,
    selectedChild,
    dailyLimits,
  } = state;

  // Predictive insights based on current data
  const insights = usePredictiveInsights(dailyData, selectedChild, dailyLimits);

  /**
   * Load initial data including children, supplements, and recent daily data
   */
  const loadInitialData = async (): Promise<void> => {
    try {
      setIsLoading(true);

      // Load children and supplements in parallel
      const [childrenData, supplementsData] = await Promise.all([
        parentDashboardApi.getChildren(),
        parentDashboardApi.getSupplements(),
      ]);

      setChildren(childrenData);
      setSupplements(supplementsData);

      // Set initial selected child
      if (childrenData.length > 0) {
        setSelectedChild(childrenData[0].name);
      }

      // Set default daily limits based on age
      const limits: { [key: string]: DailyLimits } = {};
      childrenData.forEach((child) => {
        // Age-appropriate default limits
        const screenTime = child.age <= 6 ? 60 : child.age <= 10 ? 90 : 120;
        const exercise = child.age <= 6 ? 30 : child.age <= 10 ? 45 : 60;

        limits[child.name] = {
          screenTime,
          exercise,
        };
      });
      setDailyLimits(limits);

      // Load recent daily data for analysis (last 7 days)
      await loadRecentDailyData();

      // Perform emotional analysis for each child
      await analyzeChildrenEmotionalStates(childrenData);
    } catch (error) {
      console.error('Failed to load initial data:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Load recent daily data for predictive insights
   */
  const loadRecentDailyData = async (): Promise<void> => {
    const recentData: { [key: string]: DailyData } = {};
    const today = new Date();

    // Load last 7 days of data
    for (let i = 0; i < 7; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      const data = await parentDashboardApi.getDailyDataForDate(date);
      recentData[formatDateKey(date)] = data;
    }

    setDailyData(recentData);
  };

  /**
   * Analyze emotional patterns and create emotional states for each child
   */
  const analyzeChildrenEmotionalStates = async (children: Child[]): Promise<void> => {
    const emotionalStatesMap: { [childName: string]: EmotionalChildState } = {};

    for (const child of children) {
      // In a real app, this would load actual emotional interaction history
      // For now, we'll use mock data that represents typical patterns
      const recentEmotions: EmotionType[] = await loadChildEmotionalHistory(child.id);

      const analysis = analyzeEmotionalPattern(recentEmotions);

      emotionalStatesMap[child.name] = {
        ...child,
        currentEmotion: analysis.dominantEmotion,
        zenMoonState: createZenMoonState(analysis.dominantEmotion, 'gentle'),
        recentInteractions: [],
        emotionalTrends: {
          dominant_emotion: analysis.dominantEmotion,
          stability_score: analysis.stabilityScore,
          recent_patterns: generateEmotionalInsights(analysis),
        },
      };
    }

    setEmotionalStates(emotionalStatesMap);

    // Set initial ZenMoon state based on first child
    if (children.length > 0) {
      const firstChild = children[0];
      const firstChildState = emotionalStatesMap[firstChild.name];
      if (firstChildState) {
        setZenMoonState(firstChildState.zenMoonState);
        setSelectedEmotion(firstChildState.currentEmotion);
      }
    }
  };

  /**
   * Load emotional history for a specific child
   * In production, this would query the database for actual interaction data
   */
  const loadChildEmotionalHistory = async (childId: number): Promise<EmotionType[]> => {
    // Use the API mock for emotional history
    // @ts-ignore: parentDashboardApi returns string[] but we want EmotionType[]
    return await parentDashboardApi.getEmotionalHistoryForChild(childId);
  };

  /**
   * Generate emotional insights based on analysis
   */
  const generateEmotionalInsights = (analysis: any): string[] => {
    const insights = [];

    if (analysis.stabilityScore > 0.7) {
      insights.push('Generally positive emotional state');
    }

    if (analysis.dominantEmotion === 'calm' || analysis.dominantEmotion === 'happy') {
      insights.push('Good emotional regulation');
    }

    if (analysis.dominantEmotion === 'curious') {
      insights.push('Shows healthy curiosity and engagement');
    }

    insights.push('Enjoys meditation and mindfulness activities');

    return insights;
  };

  /**
   * Refresh all data
   */
  const refreshData = async (): Promise<void> => {
    await loadInitialData();
  };

  /**
   * Load daily data for a specific date
   */
  const loadDailyDataForDate = async (date: Date): Promise<DailyData> => {
    try {
      const data = await parentDashboardApi.getDailyDataForDate(date);

      // Update cached data
      setDailyData((prevData) => ({
        ...prevData,
        [formatDateKey(date)]: data,
      }));

      return data;
    } catch (error) {
      console.error('Failed to load daily data for date:', error);
      throw error;
    }
  };

  // Auto-load initial data on mount
  useEffect(() => {
    loadInitialData().catch(console.error);
  }, []); // Only run once on mount

  return {
    loadInitialData,
    refreshData,
    loadDailyDataForDate,
    insights,
  };
};

export default useParentDashboardData;
