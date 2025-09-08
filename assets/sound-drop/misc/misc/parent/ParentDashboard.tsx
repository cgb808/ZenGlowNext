/**
 * =================================================================================
 * PARENT DASHBOARD - Main React Native Component
 * =================================================================================
 * Purpose: Central orchestrator for the Parent Dashboard module with emotional awareness
 * Dependencies:
 *   - ../../hooks/usePredictiveInsights (emotional pattern analysis)
 *   - ../../services/emotionalAudio (hum-based feedback system)
 *   - ../../services/parentDashboardApi (data layer abstraction)
 *   - ../../types/parentDashboard (complete type system)
 *   - ../../utils/emotionalSystem (ZenMoon state management)
 *   - ../emotional/ZenMoonAvatar (interactive emotional avatar)
 *   - ../emotional/EmotionalMoodRing (emotion selector)
 *
 * Used By: App navigation system (screen container)
 * Backend: Supabase (via parentDashboardApi abstraction layer)
 * Integration: React Navigation, Expo AV, emotional state management
 *
 * Key Features:
 * - Multi-child dashboard with emotional state tracking
 * - ZenMoon avatar integration with real-time emotional feedback
 * - Emotional mood ring for parent observation of child states
 * - Predictive insights based on emotional pattern analysis
 * - Audio feedback initialization and lifecycle management
 * - Daily data logging and supplement tracking
 * - Gentle transitions and neurodivergent-friendly design
 *
 * State Management:
 * - Children data and selection
 * - Emotional states per child with trend analysis
 * - ZenMoon interaction state and audio coordination
 * - Daily data, limits, and supplement information
 * - Modal states for data input and information display
 *
 * Design Philosophy:
 * - Parent as observer and supporter, not controller
 * - Emotional awareness as primary dashboard focus
 * - ZenGlow color psychology throughout interface
 * - Gentle, non-invasive data presentation
 * =================================================================================
 */

// =================================================================================
// PARENT DASHBOARD - Main React Native Component
// =================================================================================
// Purpose: Central orchestrator for the Parent Dashboard module
// Handles state management, data loading, and component coordination

import React, { useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { handleError } from '../../../src/utils/errorHandler';
import { usePredictiveInsights } from '../../hooks/usePredictiveInsights';
import { emotionalAudioService } from '../../services/emotionalAudio';
import { parentDashboardApi } from '../../services/parentDashboardApi';
import {
  Child,
  DailyData,
  DailyLimits,
  EmotionalChildState,
  EmotionalInteraction,
  EmotionType,
  Supplement,
  ViewMode,
  ZenMoonState,
} from '../../types/parentDashboard';
import { analyzeEmotionalPattern, createZenMoonState } from '../../utils/emotionalSystem';
import { formatDateKey } from '../../utils/parentDashboardUtils';
import { EmotionalMoodRing } from '../emotional/EmotionalMoodRing';
import { ZenMoonAvatar } from '../emotional/ZenMoonAvatar';
import DailyView from './views/DailyView';
import TrendsView from './views/TrendsView';
import WeeklyView from './views/WeeklyView';
import ZenScoreView from './views/ZenScoreView';

/**
 * ParentDashboard - Main React Native Component for Parent Dashboard
 * Handles state management, data loading, emotional analysis, and component coordination
 * @returns JSX.Element
 */
export const ParentDashboard: React.FC = () => {
  // =================================================================================
  // STATE MANAGEMENT
  // =================================================================================
  const [children, setChildren] = useState<Child[]>([]);
  const [supplements, setSupplements] = useState<Supplement[]>([]);
  const [dailyData, setDailyData] = useState<{ [key: string]: DailyData }>({});
  const [dailyLimits, setDailyLimits] = useState<{
    [key: string]: DailyLimits;
  }>({});

  const [selectedChild, setSelectedChild] = useState<string>('');
  const [viewMode, setViewMode] = useState<ViewMode>('daily');
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(true);

  // Modal states
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [currentLogData, setCurrentLogData] = useState<DailyData | null>(null);
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
  const [selectedSupplementInfo, setSelectedSupplementInfo] = useState<Supplement | null>(null);

  // =================================================================================
  // EMOTIONAL SYSTEM STATE
  // =================================================================================
  const [emotionalStates, setEmotionalStates] = useState<{
    [childName: string]: EmotionalChildState;
  }>({});
  const [zenMoonState, setZenMoonState] = useState<ZenMoonState>(
    createZenMoonState('neutral', 'gentle'),
  );
  const [selectedEmotion, setSelectedEmotion] = useState<EmotionType>('neutral');
  const [showEmotionalInsights, setShowEmotionalInsights] = useState(false);

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
  // PREDICTIVE INSIGHTS
  // =================================================================================
  const insights = usePredictiveInsights(dailyData, selectedChild, dailyLimits);

  // =================================================================================
  // DATA LOADING
  // =================================================================================
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setIsLoading(true);

        // Load children and supplements
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

        // Set default daily limits (in real app, this would come from database)
        const limits: { [key: string]: DailyLimits } = {};
        childrenData.forEach((child) => {
          // Age-based default limits
          const screenTime = child.age <= 6 ? 60 : child.age <= 10 ? 90 : 120;
          const exercise = child.age <= 6 ? 30 : child.age <= 10 ? 45 : 60;

          limits[child.name] = {
            screenTime,
            exercise,
          };
        });
        setDailyLimits(limits);

        // Load recent daily data for insights
        const recentData: { [key: string]: DailyData } = {};
        const today = new Date();

        for (let i = 0; i < 7; i++) {
          const date = new Date(today);
          date.setDate(today.getDate() - i);
          const data = await parentDashboardApi.getDailyDataForDate(date);
          recentData[formatDateKey(date)] = data;
        }

        setDailyData(recentData);

        // =================================================================================
        // EMOTIONAL ANALYSIS
        // =================================================================================
        // Analyze emotional patterns for each child
        const emotionalStatesMap: { [childName: string]: EmotionalChildState } = {};

        childrenData.forEach((child) => {
          // Mock emotional history (in real app, this would come from child interactions)
          const recentEmotions: EmotionType[] = [
            'happy',
            'calm',
            'curious',
            'neutral',
            'happy',
            'loved',
            'calm',
          ];

          const analysis = analyzeEmotionalPattern(recentEmotions);

          emotionalStatesMap[child.name] = {
            ...child,
            currentEmotion: analysis.dominantEmotion,
            zenMoonState: createZenMoonState(analysis.dominantEmotion, 'gentle'),
            recentInteractions: [],
            emotionalTrends: {
              dominant_emotion: analysis.dominantEmotion,
              stability_score: analysis.stabilityScore,
              recent_patterns: [
                'Generally positive',
                'Good emotional regulation',
                'Enjoys meditation',
              ],
            },
          };
        });

        setEmotionalStates(emotionalStatesMap);

        // Set initial ZenMoon state based on first child
        if (childrenData.length > 0) {
          const firstChild = childrenData[0];
          const firstChildState = emotionalStatesMap[firstChild.name];
          if (firstChildState) {
            setZenMoonState(firstChildState.zenMoonState);
            setSelectedEmotion(firstChildState.currentEmotion);
          }
        }
      } catch (error) {
        console.error('Failed to load initial data:', error);
        Alert.alert('Error', 'Failed to load dashboard data. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    loadInitialData();

    // Initialize emotional audio service
    emotionalAudioService.initialize().catch((error) => {
      console.warn('Audio service initialization failed:', error);
    });

    // Cleanup on unmount
    return () => {
      emotionalAudioService.cleanup();
    };
  }, []);

  // =================================================================================
  // EVENT HANDLERS
  // =================================================================================
  const handleOpenLogModal = async () => {
    try {
      const todayLog = await parentDashboardApi.getDailyDataForDate(selectedDate);
      setCurrentLogData(todayLog);
      setIsLogModalOpen(true);
    } catch (err) {
      Alert.alert('Error', handleError(err, 'Failed to load log data.'));
    }
  };

  const handleUpdateDayLog = async (updatedLog: DailyData) => {
    try {
      const success = await parentDashboardApi.updateDailyLog(selectedDate, updatedLog);
      if (success) {
        const key = formatDateKey(selectedDate);
        setDailyData((prevData) => ({ ...prevData, [key]: updatedLog }));
        setIsLogModalOpen(false);
        Alert.alert('Success', 'Daily log updated successfully!');
      } else {
        Alert.alert('Error', 'Failed to save log. Please try again.');
      }
    } catch (err) {
      Alert.alert('Error', handleError(err, 'Failed to save log. Please try again.'));
    }
  };

  const handleSupplementClick = (supplement: Supplement) => {
    /**
     * Opens supplement info modal for selected supplement
     * @param supplement - Supplement object
     */
    setSelectedSupplementInfo(supplement);
    setIsInfoModalOpen(true);
  };

  const handleChildSelect = (childName: string) => {
    /**
     * Handles child selection and updates ZenMoon state
     * @param childName - Name of selected child
     */
    setSelectedChild(childName);

    // Update ZenMoon state to match selected child's emotion
    const childState = emotionalStates[childName];
    if (childState) {
      setZenMoonState(childState.zenMoonState);
      setSelectedEmotion(childState.currentEmotion);
    }
  };

  const handleViewModeChange = (mode: ViewMode) => {
    /**
     * Changes dashboard view mode
     * @param mode - ViewMode string
     */
    setViewMode(mode);
  };

  // =================================================================================
  // EMOTIONAL INTERACTION HANDLERS
  // =================================================================================
  const handleEmotionSelect = async (emotion: EmotionType) => {
    /**
     * Handles parent observation of child's emotion
     * @param emotion - EmotionType string
     */
    console.log(`Parent observing child's emotion: ${emotion}`);

    // Update selected emotion
    setSelectedEmotion(emotion);

    // Create new ZenMoon state based on selected emotion
    const newZenMoonState = createZenMoonState(emotion, 'gentle');
    setZenMoonState(newZenMoonState);

    // Play emotional feedback audio
    try {
      await emotionalAudioService.playEmotionalFeedback(emotion, true, 0.5);
    } catch (error) {
      console.warn('Audio feedback failed:', error);
    }

    // Update the emotional state for the selected child
    if (selectedChild && emotionalStates[selectedChild]) {
      const updatedChildState: EmotionalChildState = {
        ...emotionalStates[selectedChild],
        currentEmotion: emotion,
        zenMoonState: newZenMoonState,
      };

      setEmotionalStates((prev) => ({
        ...prev,
        [selectedChild]: updatedChildState,
      }));
    }
  };

  const handleZenMoonInteraction = (interaction: EmotionalInteraction) => {
    console.log('ZenMoon interaction:', interaction);

    // In a real app, this would:
    // 1. Play the appropriate hum sound based on interaction.feedback.audioHum
    // 2. Trigger visual animations based on interaction.feedback.visualEffect
    // 3. Log the interaction for emotional analytics
    // 4. Possibly suggest parent interventions if needed

    // For now, we'll just update the ZenMoon state
    setZenMoonState(interaction.zenMoonResponse);
  };

  const toggleEmotionalInsights = () => {
    setShowEmotionalInsights(!showEmotionalInsights);
  };

  // =================================================================================
  // LOADING STATE
  // =================================================================================
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading Dashboard...</Text>
      </View>
    );
  }

  // =================================================================================
  // NO CHILDREN STATE
  // =================================================================================
  if (children.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyTitle}>Welcome to Parent Dashboard</Text>
        <Text style={styles.emptyText}>
          Add your first child to start tracking their wellness journey!
        </Text>
      </View>
    );
  }

  // =================================================================================
  // MAIN RENDER
  // =================================================================================
  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.content}>
        {/* Header Section */}
        <View style={styles.header}>
          <Text style={styles.title}>Parent Dashboard</Text>
          <Text style={styles.subtitle}>
            A holistic view of your children's wellness and activities
          </Text>
          <Text style={styles.dateText}>
            {new Date().toLocaleDateString('en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </Text>
        </View>

        {/* Child Selector */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Select Child</Text>
          <View style={styles.childSelector}>
            {children.map((child) => (
              <Text
                key={child.id}
                style={[
                  styles.childButton,
                  selectedChild === child.name && styles.childButtonSelected,
                ]}
                onPress={() => handleChildSelect(child.name)}
              >
                {child.avatar} {child.name}
              </Text>
            ))}
          </View>
        </View>

        {/* =================================================================================
             EMOTIONAL AWARENESS SECTION
             ================================================================================= */}
        {selectedChild && emotionalStates[selectedChild] && (
          <View style={[styles.section, styles.emotionalSection]}>
            <Text style={styles.sectionTitle}>Emotional Wellness</Text>

            <View style={styles.emotionalContainer}>
              {/* ZenMoon Avatar */}
              <View style={styles.zenMoonContainer}>
                <ZenMoonAvatar
                  state={zenMoonState}
                  size="large"
                  interactive={true}
                  onInteraction={handleZenMoonInteraction}
                />
                <Text style={styles.zenMoonLabel}>
                  {emotionalStates[selectedChild].emotionalTrends.recent_patterns[0]}
                </Text>
              </View>

              {/* Emotional Mood Ring */}
              <View style={styles.moodRingContainer}>
                <EmotionalMoodRing
                  emotions={availableEmotions}
                  selectedEmotion={selectedEmotion}
                  onEmotionSelect={handleEmotionSelect}
                  glowIntensity="gentle"
                  showLabels={true}
                />
              </View>
            </View>

            {/* Emotional Insights Toggle */}
            <Text style={styles.insightsToggle} onPress={toggleEmotionalInsights}>
              {showEmotionalInsights ? '▼' : '▶'} Emotional Insights
            </Text>

            {showEmotionalInsights && (
              <View style={styles.emotionalInsights}>
                <Text style={styles.insightText}>
                  🧠 Stability Score:{' '}
                  {emotionalStates[selectedChild].emotionalTrends.stability_score.toFixed(0)}%
                </Text>
                <Text style={styles.insightText}>
                  🌟 Dominant Emotion:{' '}
                  {emotionalStates[selectedChild].emotionalTrends.dominant_emotion}
                </Text>
                {emotionalStates[selectedChild].emotionalTrends.recent_patterns.map(
                  (pattern, index) => (
                    <Text key={index} style={styles.insightText}>
                      • {pattern}
                    </Text>
                  ),
                )}
              </View>
            )}
          </View>
        )}

        {/* Selected Child Info */}
        {selectedChild && (
          <View style={styles.section}>
            <View style={styles.childInfo}>
              <Text style={styles.childName}>
                {children.find((c) => c.name === selectedChild)?.avatar} {selectedChild}
              </Text>
              <Text style={styles.childDetails}>
                Age {children.find((c) => c.name === selectedChild)?.age} • Screen Limit:{' '}
                {dailyLimits[selectedChild]?.screenTime || 0}min • Exercise Goal:{' '}
                {dailyLimits[selectedChild]?.exercise || 0}min
              </Text>
            </View>
          </View>
        )}

        {/* Insights Panel */}
        {insights.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Insights for {selectedChild}</Text>
            {insights.map((insight, index) => (
              <View
                key={index}
                style={[
                  styles.insightCard,
                  insight.type === 'warning' && styles.insightWarning,
                  insight.type === 'suggestion' && styles.insightSuggestion,
                  insight.type === 'positive' && styles.insightPositive,
                ]}
              >
                <Text style={styles.insightTitle}>{insight.title}</Text>
                <Text style={styles.insightMessage}>{insight.message}</Text>
              </View>
            ))}
          </View>
        )}

        {/* View Mode Selector */}
        <View style={styles.section}>
          <View style={styles.viewModeSelector}>
            {(['daily', 'weekly', 'trends'] as ViewMode[]).map((mode) => (
              <Text
                key={mode}
                style={[styles.viewModeButton, viewMode === mode && styles.viewModeButtonSelected]}
                onPress={() => handleViewModeChange(mode)}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </Text>
            ))}
          </View>
        </View>

        {/* Zen Score Aggregated View */}
        <View style={styles.section}>
          <ZenScoreView childrenList={children} dailyData={dailyData} />
        </View>

        {/* Dashboard Content */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            {viewMode.charAt(0).toUpperCase() + viewMode.slice(1)} View
          </Text>

          {/* Dashboard views now use real components (scaffolded) */}
          <View style={styles.dashboardContent}>
            {viewMode === 'daily' && (
              <DailyView
                selectedChild={selectedChild}
                childrenList={children}
                dailyData={dailyData}
                supplements={supplements}
              />
            )}
            {viewMode === 'weekly' && (
              <WeeklyView
                selectedChild={selectedChild}
                childrenList={children}
                dailyData={dailyData}
                supplements={supplements}
              />
            )}
            {viewMode === 'trends' && (
              <TrendsView
                selectedChild={selectedChild}
                childrenList={children}
                dailyData={dailyData}
                supplements={supplements}
              />
            )}
          </View>
        </View>

        {/* Quick Stats */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Stats</Text>
          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{children.length}</Text>
              <Text style={styles.statLabel}>Children</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{supplements.length}</Text>
              <Text style={styles.statLabel}>Supplements</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{insights.length}</Text>
              <Text style={styles.statLabel}>Insights</Text>
            </View>
          </View>
        </View>

        {/* Development Info */}
        <View style={styles.devInfo}>
          <Text style={styles.devText}>
            🚧 Parent Dashboard is in development. Full UI components coming soon!
          </Text>
          <Text style={styles.devText}>
            Current Status: Data layer ✅ | Insights ✅ | UI Components 🚧
          </Text>
        </View>
      </View>
    </ScrollView>
  );
};

// =================================================================================
// STYLES
// =================================================================================
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  content: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
  },
  loadingText: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 24,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
    marginBottom: 8,
  },
  dateText: {
    fontSize: 14,
    color: '#94a3b8',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 12,
  },
  childSelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  childButton: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#ffffff',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    fontSize: 16,
    fontWeight: '500',
    color: '#475569',
  },
  childButtonSelected: {
    borderColor: '#3b82f6',
    backgroundColor: '#eff6ff',
    color: '#1d4ed8',
  },
  childInfo: {
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  childName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  childDetails: {
    fontSize: 14,
    color: '#64748b',
  },
  insightCard: {
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
    borderLeftWidth: 4,
  },
  insightWarning: {
    backgroundColor: '#fefce8',
    borderLeftColor: '#eab308',
  },
  insightSuggestion: {
    backgroundColor: '#eff6ff',
    borderLeftColor: '#3b82f6',
  },
  insightPositive: {
    backgroundColor: '#f0fdf4',
    borderLeftColor: '#22c55e',
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  insightMessage: {
    fontSize: 14,
    color: '#475569',
    lineHeight: 20,
  },
  viewModeSelector: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 4,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  viewModeButton: {
    flex: 1,
    textAlign: 'center',
    paddingVertical: 12,
    fontSize: 14,
    fontWeight: '500',
    color: '#64748b',
    borderRadius: 8,
  },
  viewModeButtonSelected: {
    backgroundColor: '#3b82f6',
    color: '#ffffff',
  },
  dashboardContent: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  dailyView: {
    minHeight: 100,
  },
  weeklyView: {
    minHeight: 100,
  },
  trendsView: {
    minHeight: 100,
  },
  placeholderText: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    fontStyle: 'italic',
    lineHeight: 20,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#64748b',
    textTransform: 'uppercase',
    fontWeight: '500',
  },
  devInfo: {
    marginTop: 20,
    padding: 16,
    backgroundColor: '#fef3c7',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f59e0b',
  },
  devText: {
    fontSize: 12,
    color: '#92400e',
    textAlign: 'center',
    marginBottom: 4,
  },
  // =================================================================================
  // EMOTIONAL SYSTEM STYLES
  // =================================================================================
  emotionalSection: {
    backgroundColor: '#f8fafc',
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#e2e8f0',
  },
  emotionalContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 10,
  },
  zenMoonContainer: {
    alignItems: 'center',
    flex: 0.4,
  },
  zenMoonLabel: {
    fontSize: 12,
    color: '#64748b',
    textAlign: 'center',
    marginTop: 8,
    fontWeight: '500',
  },
  moodRingContainer: {
    flex: 0.6,
    alignItems: 'center',
  },
  insightsToggle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#3b82f6',
    paddingVertical: 12,
    textAlign: 'center',
  },
  emotionalInsights: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  insightText: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
    lineHeight: 20,
  },
});

export default ParentDashboard;
