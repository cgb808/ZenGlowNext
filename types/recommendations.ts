/**
 * =================================================================================
 * RECOMMENDATION TYPES - ZenGlow Recommendation System
 * =================================================================================
 * Purpose: Type definitions for the recommendation generation service
 * =================================================================================
 */

export type RecommendationPriority = 'low' | 'medium' | 'high';

export type RecommendationType = 
  | 'mindfulness'
  | 'routine_adjustment'
  | 'activity_suggestion'
  | 'screen_time_management'
  | 'wellness_improvement'
  | 'engagement_boost';

export interface Recommendation {
  id: string;
  type: RecommendationType;
  title: string;
  message: string;
  priority: RecommendationPriority;
  tags: string[];
  sourceSignals: string[];
  generatedAt?: string;
  metadata?: Record<string, any>;
}

export interface MetricsSummary {
  wellnessScore: number;
  avgMood: number;
  routinesCompleted: number;
  trend?: 'upward' | 'downward' | 'stable';
}

export interface ChronotypeInfo {
  type?: 'early_bird' | 'night_owl' | 'intermediate' | null;
  confidence?: number;
}

export interface CausalSignals {
  // Placeholder for future causal inference signals
  interventionEffectiveness?: Record<string, number>;
  contextualFactors?: string[];
}

export interface EngagementSignals {
  streaks: number;
  missedRoutines: number;
  lastActiveDate?: string;
  engagementScore?: number;
}

export interface RecommendationContext {
  childId: string;
  recentMetrics: MetricsSummary;
  chronotype?: ChronotypeInfo;
  causalSignals?: CausalSignals;
  engagementSignals: EngagementSignals;
  screenTimeMinutes?: number;
  additionalContext?: Record<string, any>;
}

export interface RecommendationGenerationOptions {
  maxRecommendations?: number;
  priorityFilter?: RecommendationPriority[];
  typeFilter?: RecommendationType[];
  excludeTags?: string[];
}

export interface RecommendationServiceConfig {
  enabled: boolean;
  debug?: boolean;
  ruleWeights?: Record<string, number>;
}