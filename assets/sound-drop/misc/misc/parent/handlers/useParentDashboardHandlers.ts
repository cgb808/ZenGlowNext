/**
 * =================================================================================
 * PARENT DASHBOARD HANDLERS HOOK
 * =================================================================================
 * Purpose: Event handlers and interaction logic for Parent Dashboard
 * Used By: ParentDashboardCore component
 * Dependencies: parentDashboardApi, emotionalAudio service
 *
 * Manages:
 * - Modal open/close handlers
 * - Child selection and view mode changes
 * - Daily log updates and data persistence
 * - Emotional interaction handling with ZenMoon
 * - Audio feedback coordination
 * =================================================================================
 */

import { Alert } from 'react-native';
import { emotionalAudioService } from '../../../services/emotionalAudio';
import { parentDashboardApi } from '../../../services/parentDashboardApi';
import {
  DailyData,
  EmotionType,
  EmotionalChildState,
  EmotionalInteraction,
  Supplement,
  ViewMode,
} from '../../../types/parentDashboard';
import { createZenMoonState } from '../../../utils/emotionalSystem';
import { formatDateKey } from '../../../utils/parentDashboardUtils';

export interface ParentDashboardHandlersProps {
  // State accessors
  selectedDate: Date;
  selectedChild: string;
  emotionalStates: { [childName: string]: EmotionalChildState };

  // State setters
  setCurrentLogData: (data: DailyData | null) => void;
  setIsLogModalOpen: (open: boolean) => void;
  setSelectedSupplementInfo: (supplement: Supplement | null) => void;
  setIsInfoModalOpen: (open: boolean) => void;
  setSelectedChild: (child: string) => void;
  setViewMode: (mode: ViewMode) => void;
  setDailyData: (
    data:
      | { [key: string]: DailyData }
      | ((prev: { [key: string]: DailyData }) => { [key: string]: DailyData }),
  ) => void;
  setSelectedEmotion: (emotion: EmotionType) => void;
  setZenMoonState: (state: any) => void;
  setEmotionalStates: (
    states:
      | { [childName: string]: EmotionalChildState }
      | ((prev: { [childName: string]: EmotionalChildState }) => {
          [childName: string]: EmotionalChildState;
        }),
  ) => void;
  setShowEmotionalInsights: (show: boolean | ((prev: boolean) => boolean)) => void;
  showEmotionalInsights: boolean;
}

export interface ParentDashboardHandlers {
  // Modal handlers
  handleOpenLogModal: () => Promise<void>;
  handleUpdateDayLog: (updatedLog: DailyData) => Promise<void>;
  handleSupplementClick: (supplement: Supplement) => void;

  // Navigation handlers
  handleChildSelect: (childName: string) => void;
  handleViewModeChange: (mode: ViewMode) => void;

  // Emotional interaction handlers
  handleEmotionSelect: (emotion: EmotionType) => Promise<void>;
  handleZenMoonInteraction: (interaction: EmotionalInteraction) => void;
  toggleEmotionalInsights: () => void;
}

/**
 * Custom hook for Parent Dashboard event handling
 * Provides all interaction handlers with proper error handling and feedback
 */
export const useParentDashboardHandlers = (
  props: ParentDashboardHandlersProps,
): ParentDashboardHandlers => {
  const {
    selectedDate,
    selectedChild,
    emotionalStates,
    setCurrentLogData,
    setIsLogModalOpen,
    setSelectedSupplementInfo,
    setIsInfoModalOpen,
    setSelectedChild,
    setViewMode,
    setDailyData,
    setSelectedEmotion,
    setZenMoonState,
    setEmotionalStates,
    setShowEmotionalInsights,
    showEmotionalInsights,
  } = props;

  // =================================================================================
  // MODAL HANDLERS
  // =================================================================================

  /**
   * Open daily log modal with current data
   */
  const handleOpenLogModal = async (): Promise<void> => {
    try {
      const todayLog = await parentDashboardApi.getDailyDataForDate(selectedDate);
      setCurrentLogData(todayLog);
      setIsLogModalOpen(true);
    } catch (error) {
      console.error('Failed to load log data:', error);
      Alert.alert('Error', 'Failed to load log data.');
    }
  };

  /**
   * Update daily log with new data
   */
  const handleUpdateDayLog = async (updatedLog: DailyData): Promise<void> => {
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
    } catch (error) {
      console.error('Failed to update log:', error);
      Alert.alert('Error', 'Failed to save log. Please try again.');
    }
  };

  /**
   * Handle supplement info modal
   */
  const handleSupplementClick = (supplement: Supplement): void => {
    setSelectedSupplementInfo(supplement);
    setIsInfoModalOpen(true);
  };

  // =================================================================================
  // NAVIGATION HANDLERS
  // =================================================================================

  /**
   * Handle child selection with emotional state sync
   */
  const handleChildSelect = (childName: string): void => {
    setSelectedChild(childName);

    // Update ZenMoon state to match selected child's emotion
    const childState = emotionalStates[childName];
    if (childState) {
      setZenMoonState(childState.zenMoonState);
      setSelectedEmotion(childState.currentEmotion);
    }
  };

  /**
   * Handle view mode changes
   */
  const handleViewModeChange = (mode: ViewMode): void => {
    setViewMode(mode);
  };

  // =================================================================================
  // EMOTIONAL INTERACTION HANDLERS
  // =================================================================================

  /**
   * Handle parent's observation of child's emotion
   * Includes audio feedback and state updates
   */
  const handleEmotionSelect = async (emotion: EmotionType): Promise<void> => {
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

  /**
   * Handle ZenMoon avatar interactions
   * Processes interaction feedback and updates state
   */
  const handleZenMoonInteraction = (interaction: EmotionalInteraction): void => {
    console.log('ZenMoon interaction:', interaction);

    // In a real app, this would:
    // 1. Play the appropriate hum sound based on interaction.feedback.audioHum
    // 2. Trigger visual animations based on interaction.feedback.visualEffect
    // 3. Log the interaction for emotional analytics
    // 4. Possibly suggest parent interventions if needed

    // Update the ZenMoon state with the interaction response
    setZenMoonState(interaction.zenMoonResponse);
  };

  /**
   * Toggle emotional insights display
   */
  const toggleEmotionalInsights = (): void => {
    setShowEmotionalInsights(!showEmotionalInsights);
  };

  return {
    // Modal handlers
    handleOpenLogModal,
    handleUpdateDayLog,
    handleSupplementClick,

    // Navigation handlers
    handleChildSelect,
    handleViewModeChange,

    // Emotional interaction handlers
    handleEmotionSelect,
    handleZenMoonInteraction,
    toggleEmotionalInsights,
  };
};

export default useParentDashboardHandlers;
