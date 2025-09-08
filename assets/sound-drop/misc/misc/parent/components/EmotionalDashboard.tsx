/**
 * =================================================================================
 * EMOTIONAL DASHBOARD COMPONENT - React Native Component
 * =================================================================================
 * Purpose: Emotional awareness and ZenMoon interaction interface
 * Dependencies: emotional types, ZenMoon avatar, mood ring
 * Used By: ParentDashboardContainer
 * Backend: Emotional audio service
 * Integration: React Native, Expo AV, emotional audio system
 *
 * Key Features:
 * - ZenMoon avatar with emotional state display
 * - Emotional mood ring for observation
 * - Audio feedback integration
 * - Predictive emotional insights
 *
 * Design Philosophy:
 * - Parent as observer, not controller
 * - Gentle emotional awareness
 * - Hum-based audio feedback
 * - Non-invasive insight presentation
 * =================================================================================
 */

import React, { useEffect } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { emotionalAudioService } from '../../../services/emotionalAudio';
import { EmotionalChildState, EmotionType, ZenMoonState } from '../../../types/parentDashboard';
import { analyzeEmotionalPattern, createZenMoonState } from '../../../utils/emotionalSystem';
import { EmotionalMoodRing } from '../../emotional/EmotionalMoodRing';
import { ZenMoonAvatar } from '../../emotional/ZenMoonAvatar';

interface EmotionalDashboardProps {
  selectedChild: string;
  selectedEmotion: EmotionType;
  emotionalStates: { [childName: string]: EmotionalChildState };
  zenMoonState: ZenMoonState;
  showEmotionalInsights: boolean;
  onEmotionSelect: (emotion: EmotionType) => void;
  onUpdateEmotionalState: (childName: string, state: EmotionalChildState) => void;
  onToggleInsights: () => void;
}

export const EmotionalDashboard: React.FC<EmotionalDashboardProps> = ({
  selectedChild,
  selectedEmotion,
  emotionalStates,
  zenMoonState,
  showEmotionalInsights,
  onEmotionSelect,
  onUpdateEmotionalState,
  onToggleInsights,
}) => {
  // Available emotions for the mood ring
  const availableEmotions: EmotionType[] = [
    'calm',
    'happy',
    'curious',
    'loved',
    'overwhelmed',
    'sleepy',
  ];

  // =================================================================================
  // AUDIO FEEDBACK INTEGRATION
  // =================================================================================
  useEffect(() => {
    const initializeAudio = async () => {
      try {
        await emotionalAudioService.initialize();
      } catch (error) {
        console.error('Error initializing emotional audio:', error);
      }
    };

    initializeAudio();

    return () => {
      emotionalAudioService.cleanup();
    };
  }, []);

  // =================================================================================
  // EMOTIONAL INTERACTION HANDLERS
  // =================================================================================
  const handleEmotionSelect = async (emotion: EmotionType) => {
    onEmotionSelect(emotion);

    // Update ZenMoon state based on emotion
    const newZenMoonState = createZenMoonState(emotion, 'gentle');

    // Update emotional state for selected child
    if (selectedChild) {
      const currentState = emotionalStates[selectedChild];
      const pattern = analyzeEmotionalPattern([emotion], Date.now());

      const newEmotionalState: EmotionalChildState = {
        ...currentState,
        currentEmotion: emotion,
        zenMoonState: newZenMoonState,
        recentInteractions: [
          ...(currentState?.recentInteractions || []),
          {
            emotion,
            intensity: 'moderate',
            audioFeedback: 'gentle-hum',
            visualResponse: 'glow',
            timestamp: new Date(),
          },
        ],
        emotionalTrends: {
          dominant_emotion: emotion,
          stability_score: 75,
          recent_patterns: [`Recent ${emotion} observation`],
        },
      };

      onUpdateEmotionalState(selectedChild, newEmotionalState);

      // Trigger audio feedback
      try {
        await emotionalAudioService.playEmotionalResponse(emotion, 'gentle');
      } catch (error) {
        console.error('Error playing emotional audio:', error);
      }
    }
  };

  const getCurrentEmotionalState = (): EmotionalChildState | null => {
    if (!selectedChild) return null;
    return emotionalStates[selectedChild] || null;
  };

  const getEmotionalInsight = (): string => {
    const currentState = getCurrentEmotionalState();
    if (!currentState) return 'Select a child to see emotional insights';

    const { currentEmotion, pattern } = currentState;
    const trends = pattern?.trends || [];

    if (trends.length === 0) {
      return `${selectedChild} is feeling ${currentEmotion} right now.`;
    }

    const recentTrend = trends[trends.length - 1];
    return `${selectedChild} is ${currentEmotion} and has been ${recentTrend.direction} over the ${recentTrend.period}.`;
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Emotional Awareness</Text>
        <TouchableOpacity
          style={styles.insightsButton}
          onPress={onToggleInsights}
          accessibilityLabel="Toggle emotional insights"
        >
          <Text style={styles.insightsButtonText}>
            {showEmotionalInsights ? 'Hide' : 'Show'} Insights
          </Text>
        </TouchableOpacity>
      </View>

      {/* ZenMoon Avatar */}
      <View style={styles.avatarSection}>
        <Text style={styles.sectionTitle}>ZenMoon Companion</Text>
        <ZenMoonAvatar
          emotion={zenMoonState.emotion}
          intensity={zenMoonState.intensity}
          glowColor={zenMoonState.glowColor}
          expression={zenMoonState.expression}
          size="large"
        />
        <Text style={styles.avatarDescription}>
          ZenMoon reflects {selectedChild ? `${selectedChild}'s` : 'the'} emotional energy
        </Text>
      </View>

      {/* Emotional Mood Ring */}
      <View style={styles.moodRingSection}>
        <Text style={styles.sectionTitle}>How does {selectedChild || 'your child'} seem?</Text>
        <EmotionalMoodRing
          emotions={availableEmotions}
          selectedEmotion={selectedEmotion}
          onEmotionSelect={handleEmotionSelect}
          size="medium"
        />
        <Text style={styles.moodRingDescription}>
          Parent observation tool - tap to reflect what you notice
        </Text>
      </View>

      {/* Emotional Insights */}
      {showEmotionalInsights && (
        <View style={styles.insightsSection}>
          <Text style={styles.sectionTitle}>Gentle Insights</Text>
          <View style={styles.insightCard}>
            <Text style={styles.insightText}>{getEmotionalInsight()}</Text>
          </View>

          {getCurrentEmotionalState()?.emotionalTrends?.recent_patterns && (
            <View style={styles.recommendationsCard}>
              <Text style={styles.recommendationsTitle}>Recent Patterns</Text>
              {getCurrentEmotionalState()?.emotionalTrends?.recent_patterns?.map(
                (pattern, index) => (
                  <Text key={index} style={styles.recommendationItem}>
                    • {pattern}
                  </Text>
                ),
              )}
            </View>
          )}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#F8FFFE',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  insightsButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#E8F4FD',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#B3D9F2',
  },
  insightsButtonText: {
    fontSize: 14,
    color: '#2C3E50',
    fontWeight: '500',
  },
  avatarSection: {
    alignItems: 'center',
    marginBottom: 32,
    paddingVertical: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
    borderRadius: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2C3E50',
    marginBottom: 16,
  },
  avatarDescription: {
    fontSize: 12,
    color: '#7F8C8D',
    textAlign: 'center',
    marginTop: 12,
    fontStyle: 'italic',
  },
  moodRingSection: {
    alignItems: 'center',
    marginBottom: 32,
  },
  moodRingDescription: {
    fontSize: 12,
    color: '#7F8C8D',
    textAlign: 'center',
    marginTop: 16,
    maxWidth: 280,
  },
  insightsSection: {
    marginTop: 16,
  },
  insightCard: {
    backgroundColor: '#FFF4E6',
    padding: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#F39C12',
    marginBottom: 16,
  },
  insightText: {
    fontSize: 14,
    color: '#2C3E50',
    lineHeight: 20,
  },
  recommendationsCard: {
    backgroundColor: '#E8F4FD',
    padding: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#3498DB',
  },
  recommendationsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2C3E50',
    marginBottom: 12,
  },
  recommendationItem: {
    fontSize: 12,
    color: '#2C3E50',
    marginBottom: 6,
    lineHeight: 18,
  },
});

export default EmotionalDashboard;
