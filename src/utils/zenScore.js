/**
 * Zen Score Calculation Utilities
 * Functions for calculating and validating Zen scores in ZenGlow
 */

/**
 * Calculates a Zen score based on activity completion and mood
 * @param {Object} params - Parameters for calculation
 * @param {Array} params.activities - Array of completed activities
 * @param {string} params.mood - Current mood ('happy', 'calm', 'excited', 'sad', 'angry')
 * @param {number} params.screenTime - Screen time in minutes
 * @param {string} params.sleepQuality - Sleep quality ('excellent', 'good', 'fair', 'poor')
 * @returns {number} Zen score between 0-100
 */
export function calculateZenScore({ activities = [], mood = 'neutral', screenTime = 0, sleepQuality = 'fair' }) {
  let score = 50; // Base score
  
  // Activity contribution (max 30 points)
  const activityPoints = activities.reduce((total, activity) => {
    return total + (activity.zenScoreContribution || 0);
  }, 0);
  score += Math.min(activityPoints, 30);
  
  // Mood contribution (max 20 points)
  const moodPoints = {
    'happy': 20,
    'calm': 15,
    'excited': 10,
    'neutral': 0,
    'sad': -10,
    'angry': -15,
  };
  score += moodPoints[mood] || 0;
  
  // Screen time penalty (max -20 points)
  const screenTimePenalty = Math.min(screenTime / 60 * 10, 20); // 10 points per hour
  score -= screenTimePenalty;
  
  // Sleep quality contribution (max 15 points)
  const sleepPoints = {
    'excellent': 15,
    'good': 10,
    'fair': 5,
    'poor': -5,
  };
  score += sleepPoints[sleepQuality] || 0;
  
  // Ensure score is within valid range
  return Math.max(0, Math.min(100, Math.round(score)));
}

/**
 * Validates if a Zen score is within acceptable range
 * @param {number} score - The score to validate
 * @returns {boolean} True if valid (0-100), false otherwise
 */
export function isValidZenScore(score) {
  return typeof score === 'number' && score >= 0 && score <= 100 && Number.isInteger(score);
}

/**
 * Calculates weekly average Zen score
 * @param {Array} dailyScores - Array of daily Zen scores
 * @returns {number} Average score rounded to nearest integer
 */
export function calculateWeeklyAverage(dailyScores) {
  if (!Array.isArray(dailyScores) || dailyScores.length === 0) {
    return 0;
  }
  
  const validScores = dailyScores.filter(score => isValidZenScore(score));
  if (validScores.length === 0) {
    return 0;
  }
  
  const sum = validScores.reduce((total, score) => total + score, 0);
  return Math.round(sum / validScores.length);
}

/**
 * Determines Zen score trend over time
 * @param {Array} scores - Array of scores in chronological order
 * @returns {string} 'improving', 'declining', or 'stable'
 */
export function getZenScoreTrend(scores) {
  if (!Array.isArray(scores) || scores.length < 2) {
    return 'stable';
  }
  
  const validScores = scores.filter(score => isValidZenScore(score));
  if (validScores.length < 2) {
    return 'stable';
  }
  
  const firstHalf = validScores.slice(0, Math.floor(validScores.length / 2));
  const secondHalf = validScores.slice(Math.floor(validScores.length / 2));
  
  const firstAvg = firstHalf.reduce((sum, score) => sum + score, 0) / firstHalf.length;
  const secondAvg = secondHalf.reduce((sum, score) => sum + score, 0) / secondHalf.length;
  
  const difference = secondAvg - firstAvg;
  
  if (difference > 5) return 'improving';
  if (difference < -5) return 'declining';
  return 'stable';
}

/**
 * Generates insights based on Zen score data
 * @param {Object} data - Score data and context
 * @returns {Array} Array of insight objects
 */
export function generateZenInsights(data) {
  const { currentScore, previousScores = [], activities = [], mood } = data;
  const insights = [];
  
  if (!isValidZenScore(currentScore)) {
    return insights;
  }
  
  // Score range insights
  if (currentScore >= 80) {
    insights.push({
      type: 'positive',
      message: 'Excellent Zen score! You\'re having a great day.',
      icon: '🌟'
    });
  } else if (currentScore >= 60) {
    insights.push({
      type: 'neutral',
      message: 'Good Zen score! Keep up the mindful activities.',
      icon: '👍'
    });
  } else if (currentScore < 40) {
    insights.push({
      type: 'suggestion',
      message: 'Try a breathing exercise to boost your Zen score.',
      icon: '🧘'
    });
  }
  
  // Activity insights
  if (activities.length === 0) {
    insights.push({
      type: 'suggestion',
      message: 'Complete a mindfulness activity to improve your day!',
      icon: '✨'
    });
  } else if (activities.length >= 3) {
    insights.push({
      type: 'positive',
      message: 'Amazing! You\'ve completed multiple activities today.',
      icon: '🎯'
    });
  }
  
  // Trend insights
  if (previousScores.length >= 3) {
    const trend = getZenScoreTrend([...previousScores, currentScore]);
    if (trend === 'improving') {
      insights.push({
        type: 'positive',
        message: 'Your Zen scores are improving over time!',
        icon: '📈'
      });
    } else if (trend === 'declining') {
      insights.push({
        type: 'suggestion',
        message: 'Let\'s work on bringing your Zen score back up.',
        icon: '💪'
      });
    }
  }
  
  return insights;
}