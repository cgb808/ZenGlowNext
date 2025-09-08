/**
 * =================================================================================
 * RECOMMENDATION SERVICE - ZenGlow Recommendation Generation
 * =================================================================================
 * Purpose: Generate structured wellness recommendations for parent dashboard
 * Architecture: Rule-based engine (ML integration planned for future)
 * =================================================================================
 */

import { v4 as uuidv4 } from 'uuid';
import type {
  Recommendation,
  RecommendationContext,
  RecommendationGenerationOptions,
  RecommendationPriority,
  RecommendationType,
  MetricsSummary,
  EngagementSignals,
  ChronotypeInfo
} from '../../../types/recommendations';
import { isRecommendationsEnabled } from '../../utils/SecurityConfig';

/**
 * Rule-based recommendation engine
 */
class RecommendationEngine {
  private debug: boolean;

  constructor(debug: boolean = false) {
    this.debug = debug;
  }

  /**
   * Generate recommendations based on context and rules
   */
  async generateRecommendations(
    childId: string,
    context: RecommendationContext,
    options: RecommendationGenerationOptions = {}
  ): Promise<Recommendation[]> {
    if (!isRecommendationsEnabled()) {
      if (this.debug) {
        console.log('🔒 Recommendations feature is disabled');
      }
      return [];
    }

    const recommendations: Recommendation[] = [];
    const maxRecommendations = options.maxRecommendations || 5;

    try {
      // Rule 1: Low wellness score & downward trend => mindfulness/breathing exercise
      this.checkWellnessScoreRule(context, recommendations);

      // Rule 2: Night owl chronotype + poor morning routines => evening prep routine
      this.checkChronotypeRule(context, recommendations);

      // Rule 3: Flat mood + low engagement => short playful activity
      this.checkMoodEngagementRule(context, recommendations);

      // Rule 4: High screen time => schedule device-free routine
      this.checkScreenTimeRule(context, recommendations);

      // Rule 5: Low engagement signals => engagement boost
      this.checkEngagementRule(context, recommendations);

      // Apply filters and limits
      let filteredRecommendations = this.applyFilters(recommendations, options);
      
      // Sort by priority (high -> medium -> low) and limit results
      filteredRecommendations = this.sortAndLimit(filteredRecommendations, maxRecommendations);

      if (this.debug) {
        console.log(`✅ Generated ${filteredRecommendations.length} recommendations for child ${childId}`);
      }

      return filteredRecommendations;

    } catch (error) {
      console.error('❌ Error generating recommendations:', error);
      return [];
    }
  }

  /**
   * Rule 1: Wellness score and trend analysis
   */
  private checkWellnessScoreRule(context: RecommendationContext, recommendations: Recommendation[]): void {
    const { recentMetrics } = context;
    
    if (recentMetrics.wellnessScore < 50 && recentMetrics.trend === 'downward') {
      recommendations.push({
        id: uuidv4(),
        type: 'mindfulness',
        title: 'Wellness Boost Needed',
        message: 'Recent wellness scores suggest mindfulness activities could help. Try a 5-minute breathing exercise or guided meditation.',
        priority: 'high',
        tags: ['wellness', 'mindfulness', 'breathing', 'meditation'],
        sourceSignals: ['low_wellness_score', 'downward_trend'],
        generatedAt: new Date().toISOString(),
        metadata: {
          wellnessScore: recentMetrics.wellnessScore,
          trend: recentMetrics.trend
        }
      });
    } else if (recentMetrics.wellnessScore < 60) {
      recommendations.push({
        id: uuidv4(),
        type: 'wellness_improvement',
        title: 'Gentle Wellness Support',
        message: 'Consider incorporating relaxing activities into the daily routine to support overall wellness.',
        priority: 'medium',
        tags: ['wellness', 'relaxation', 'routine'],
        sourceSignals: ['moderate_wellness_score'],
        generatedAt: new Date().toISOString(),
        metadata: {
          wellnessScore: recentMetrics.wellnessScore
        }
      });
    }
  }

  /**
   * Rule 2: Chronotype-based routine suggestions
   */
  private checkChronotypeRule(context: RecommendationContext, recommendations: Recommendation[]): void {
    const { chronotype, recentMetrics } = context;
    
    if (chronotype?.type === 'night_owl' && recentMetrics.routinesCompleted < 3) {
      recommendations.push({
        id: uuidv4(),
        type: 'routine_adjustment',
        title: 'Evening Prep Routine',
        message: 'As a night owl, try setting up evening routines to prepare for the next day. This can help with morning transitions.',
        priority: 'medium',
        tags: ['chronotype', 'night_owl', 'evening_routine', 'preparation'],
        sourceSignals: ['night_owl_chronotype', 'low_routine_completion'],
        generatedAt: new Date().toISOString(),
        metadata: {
          chronotype: chronotype.type,
          routinesCompleted: recentMetrics.routinesCompleted
        }
      });
    } else if (chronotype?.type === 'early_bird' && recentMetrics.routinesCompleted < 3) {
      recommendations.push({
        id: uuidv4(),
        type: 'routine_adjustment', 
        title: 'Morning Routine Optimization',
        message: 'Take advantage of your early bird nature with energizing morning activities and goal-setting routines.',
        priority: 'medium',
        tags: ['chronotype', 'early_bird', 'morning_routine', 'energy'],
        sourceSignals: ['early_bird_chronotype', 'low_routine_completion'],
        generatedAt: new Date().toISOString(),
        metadata: {
          chronotype: chronotype.type,
          routinesCompleted: recentMetrics.routinesCompleted
        }
      });
    }
  }

  /**
   * Rule 3: Mood and engagement correlation
   */
  private checkMoodEngagementRule(context: RecommendationContext, recommendations: Recommendation[]): void {
    const { recentMetrics, engagementSignals } = context;
    
    // Flat mood (around neutral) + low engagement
    if (recentMetrics.avgMood >= 4 && recentMetrics.avgMood <= 6 && engagementSignals.engagementScore && engagementSignals.engagementScore < 0.4) {
      recommendations.push({
        id: uuidv4(),
        type: 'activity_suggestion',
        title: 'Fun Activity Break',
        message: 'Try a short, playful activity to boost mood and engagement. Consider a quick game, creative exercise, or movement break.',
        priority: 'medium',
        tags: ['mood_boost', 'engagement', 'playful', 'activity', 'creativity'],
        sourceSignals: ['flat_mood', 'low_engagement'],
        generatedAt: new Date().toISOString(),
        metadata: {
          avgMood: recentMetrics.avgMood,
          engagementScore: engagementSignals.engagementScore
        }
      });
    }
  }

  /**
   * Rule 4: Screen time management
   */
  private checkScreenTimeRule(context: RecommendationContext, recommendations: Recommendation[]): void {
    const { screenTimeMinutes } = context;
    
    if (screenTimeMinutes && screenTimeMinutes > 120) { // More than 2 hours
      recommendations.push({
        id: uuidv4(),
        type: 'screen_time_management',
        title: 'Device-Free Time',
        message: 'Screen time is quite high recently. Consider scheduling device-free periods with outdoor activities or hands-on hobbies.',
        priority: screenTimeMinutes > 180 ? 'high' : 'medium',
        tags: ['screen_time', 'digital_wellness', 'outdoor', 'hobbies', 'balance'],
        sourceSignals: ['high_screen_time'],
        generatedAt: new Date().toISOString(),
        metadata: {
          screenTimeMinutes
        }
      });
    }
  }

  /**
   * Rule 5: Engagement and routine adherence
   */
  private checkEngagementRule(context: RecommendationContext, recommendations: Recommendation[]): void {
    const { engagementSignals } = context;
    
    if (engagementSignals.streaks === 0 && engagementSignals.missedRoutines > 3) {
      recommendations.push({
        id: uuidv4(),
        type: 'engagement_boost',
        title: 'Fresh Start Approach',
        message: 'Let\'s restart with simpler, shorter activities to rebuild momentum. Small consistent wins lead to bigger successes!',
        priority: 'high',
        tags: ['engagement', 'motivation', 'fresh_start', 'simple_activities'],
        sourceSignals: ['no_streaks', 'multiple_missed_routines'],
        generatedAt: new Date().toISOString(),
        metadata: {
          streaks: engagementSignals.streaks,
          missedRoutines: engagementSignals.missedRoutines
        }
      });
    } else if (engagementSignals.streaks > 0 && engagementSignals.streaks < 3) {
      recommendations.push({
        id: uuidv4(),
        type: 'engagement_boost',
        title: 'Building Momentum',
        message: 'Great start with your current streak! Try adding one new small routine to build on this positive momentum.',
        priority: 'low',
        tags: ['engagement', 'streak_building', 'momentum', 'encouragement'],
        sourceSignals: ['small_streak'],
        generatedAt: new Date().toISOString(),
        metadata: {
          streaks: engagementSignals.streaks
        }
      });
    }
  }

  /**
   * Apply filters based on options
   */
  private applyFilters(recommendations: Recommendation[], options: RecommendationGenerationOptions): Recommendation[] {
    let filtered = recommendations;

    if (options.priorityFilter && options.priorityFilter.length > 0) {
      filtered = filtered.filter(rec => options.priorityFilter!.includes(rec.priority));
    }

    if (options.typeFilter && options.typeFilter.length > 0) {
      filtered = filtered.filter(rec => options.typeFilter!.includes(rec.type));
    }

    if (options.excludeTags && options.excludeTags.length > 0) {
      filtered = filtered.filter(rec => 
        !rec.tags.some(tag => options.excludeTags!.includes(tag))
      );
    }

    return filtered;
  }

  /**
   * Sort by priority and limit results
   */
  private sortAndLimit(recommendations: Recommendation[], maxCount: number): Recommendation[] {
    const priorityOrder: Record<RecommendationPriority, number> = {
      'high': 3,
      'medium': 2,
      'low': 1
    };

    return recommendations
      .sort((a, b) => priorityOrder[b.priority] - priorityOrder[a.priority])
      .slice(0, maxCount);
  }
}

// Create singleton instance
const recommendationEngine = new RecommendationEngine(process.env.NODE_ENV === 'development');

/**
 * Main service function for generating recommendations
 */
export async function generateRecommendations(
  childId: string,
  context: RecommendationContext,
  options?: RecommendationGenerationOptions
): Promise<Recommendation[]> {
  return recommendationEngine.generateRecommendations(childId, context, options);
}

/**
 * Export the engine class for testing
 */
export { RecommendationEngine };

/**
 * Default export - the main service function
 */
export default generateRecommendations;