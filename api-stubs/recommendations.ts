/**
 * =================================================================================
 * RECOMMENDATIONS API ENDPOINT - ZenGlow Recommendation Service
 * =================================================================================
 * Purpose: API endpoint for generating recommendations for authenticated parents
 * Authentication: Consistent with existing patterns
 * =================================================================================
 */

import { NextApiRequest, NextApiResponse } from 'next';
import { generateRecommendations } from '../../src/services/recommendations/recommendationService';
import { isRecommendationsEnabled } from '../../src/utils/SecurityConfig';
import type { RecommendationContext, RecommendationGenerationOptions } from '../../types/recommendations';

/**
 * Recommendations API Handler
 * GET /api/recommendations?childId=<id>&userId=<userId>
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Feature flag check
  if (!isRecommendationsEnabled()) {
    console.log('📝 Recommendations feature disabled - returning empty response');
    return res.status(204).end();
  }

  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Extract parameters
    const { childId, userId } = req.query;

    // Basic validation
    if (!childId || typeof childId !== 'string') {
      return res.status(400).json({ error: 'childId parameter is required' });
    }

    // Mock authentication check (consistent with existing patterns)
    // In production, this would verify JWT token or session
    if (!userId || typeof userId !== 'string') {
      return res.status(401).json({ error: 'Unauthorized: userId required' });
    }

    // Mock context data - in production, this would come from database
    const mockContext: RecommendationContext = {
      childId: childId,
      recentMetrics: {
        wellnessScore: 45, // Low score to trigger wellness rule
        avgMood: 5.2, // Neutral mood 
        routinesCompleted: 2, // Low completion
        trend: 'downward'
      },
      chronotype: {
        type: 'night_owl',
        confidence: 0.75
      },
      causalSignals: {
        interventionEffectiveness: {},
        contextualFactors: []
      },
      engagementSignals: {
        streaks: 1,
        missedRoutines: 4,
        lastActiveDate: '2024-01-10',
        engagementScore: 0.3
      },
      screenTimeMinutes: 150, // 2.5 hours - high screen time
      additionalContext: {
        timeOfDay: 'evening',
        parentRequestedSuggestion: false
      }
    };

    // Parse options from query parameters
    const options: RecommendationGenerationOptions = {};
    
    if (req.query.maxRecommendations) {
      const max = parseInt(req.query.maxRecommendations as string);
      if (!isNaN(max) && max > 0) {
        options.maxRecommendations = Math.min(max, 10); // Cap at 10
      }
    }

    if (req.query.priority) {
      const priorities = (req.query.priority as string).split(',');
      options.priorityFilter = priorities.filter(p => ['low', 'medium', 'high'].includes(p)) as any[];
    }

    if (req.query.excludeTags) {
      options.excludeTags = (req.query.excludeTags as string).split(',');
    }

    // Generate recommendations
    const recommendations = await generateRecommendations(childId, mockContext, options);

    // Log for development
    if (process.env.NODE_ENV === 'development') {
      console.log(`📊 Generated ${recommendations.length} recommendations for child ${childId}`);
    }

    // Return recommendations
    return res.status(200).json({
      success: true,
      childId,
      recommendationsCount: recommendations.length,
      recommendations,
      generatedAt: new Date().toISOString(),
      context: {
        featureEnabled: true,
        wellnessScore: mockContext.recentMetrics.wellnessScore,
        chronotype: mockContext.chronotype?.type || 'unknown'
      }
    });

  } catch (error) {
    console.error('❌ Error in recommendations API:', error);
    
    return res.status(500).json({
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : 'Failed to generate recommendations'
    });
  }
}