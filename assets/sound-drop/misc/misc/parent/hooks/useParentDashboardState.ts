/**
 * =================================================================================
 * PARENT DASHBOARD STATE HOOK - Custom React Hook
 * =================================================================================
 * Purpose: Centralized state management for Parent Dashboard
 * Dependencies: parentDashboardApi, emotionalSystem utilities
 * Used By: ParentDashboardContainer
 * Backend: Supabase (via parentDashboardApi abstraction layer)
 * Integration: React hooks, emotional state management
 *
 * Key Features:
 * - Children data and selection management
 * - Daily data and limits state
 * - Emotional states per child
 * - Loading states and error handling
 * - Modal state management
 *
 * Design Philosophy:
 * - Separation of concerns from UI components
 * - Reusable state logic
 * - Type-safe state management
 * =================================================================================
 */

import { useEffect, useState } from 'react';
import { parentDashboardApi } from '../../../services/parentDashboardApi';
import {
  Child,
  DailyData,
  DailyLimits,
  EmotionalChildState,
  EmotionType,
  Supplement,
  ViewMode,
  ZenMoonState,
} from '../../../types/parentDashboard';
import { createZenMoonState } from '../../../utils/emotionalSystem';
import { formatDateKey } from '../../../utils/parentDashboardUtils';

export interface ParentDashboardState {
  // Core data
  children: Child[];
  supplements: Supplement[];
  dailyData: { [key: string]: DailyData };
  dailyLimits: { [key: string]: DailyLimits };

  // Selection and view state
  selectedChild: string;
  viewMode: ViewMode;
  selectedDate: Date;
  isLoading: boolean;

  // Modal states
  isLogModalOpen: boolean;
  currentLogData: DailyData | null;
  isInfoModalOpen: boolean;
  selectedSupplementInfo: Supplement | null;

  // Emotional system state
  emotionalStates: { [childName: string]: EmotionalChildState };
  zenMoonState: ZenMoonState;
  selectedEmotion: EmotionType;
  showEmotionalInsights: boolean;
}

export interface ParentDashboardActions {
  // Data actions
  loadInitialData: () => Promise<void>;
  refreshData: () => Promise<void>;

  // Selection actions
  setSelectedChild: (childName: string) => void;
  setViewMode: (mode: ViewMode) => void;
  setSelectedDate: (date: Date) => void;

  // Modal actions
  openLogModal: (data?: DailyData) => void;
  closeLogModal: () => void;
  openInfoModal: (supplement: Supplement) => void;
  closeInfoModal: () => void;

  // Emotional actions
  setSelectedEmotion: (emotion: EmotionType) => void;
  updateEmotionalState: (childName: string, state: EmotionalChildState) => void;
  toggleEmotionalInsights: () => void;
}

export const useParentDashboardState = (): [ParentDashboardState, ParentDashboardActions] => {
  // =================================================================================
  // STATE MANAGEMENT
  // =================================================================================
  const [children, setChildren] = useState<Child[]>([]);
  const [supplements, setSupplements] = useState<Supplement[]>([]);
  const [dailyData, setDailyData] = useState<{ [key: string]: DailyData }>({});
  const [dailyLimits, setDailyLimits] = useState<{ [key: string]: DailyLimits }>({});

  const [selectedChild, setSelectedChild] = useState<string>('');
  const [viewMode, setViewMode] = useState<ViewMode>('daily');
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(true);

  // Modal states
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [currentLogData, setCurrentLogData] = useState<DailyData | null>(null);
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
  const [selectedSupplementInfo, setSelectedSupplementInfo] = useState<Supplement | null>(null);

  // Emotional system state
  const [emotionalStates, setEmotionalStates] = useState<{
    [childName: string]: EmotionalChildState;
  }>({});
  const [zenMoonState, setZenMoonState] = useState<ZenMoonState>(
    createZenMoonState('neutral', 'gentle'),
  );
  const [selectedEmotion, setSelectedEmotion] = useState<EmotionType>('neutral');
  const [showEmotionalInsights, setShowEmotionalInsights] = useState(false);

  // =================================================================================
  // DATA LOADING ACTIONS
  // =================================================================================
  const loadInitialData = async (): Promise<void> => {
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

      // Set default daily limits
      const limits: { [key: string]: DailyLimits } = {};
      childrenData.forEach((child) => {
        const screenTime = child.age <= 6 ? 60 : child.age <= 10 ? 90 : 120;
        const exercise = child.age <= 6 ? 30 : child.age <= 10 ? 45 : 60;

        limits[child.name] = { screenTime, exercise };
      });
      setDailyLimits(limits);

      // Load recent daily data
      const recentData: { [key: string]: DailyData } = {};
      const today = new Date();

      for (let i = 0; i < 7; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateKey = formatDateKey(date);

        const dayData = await parentDashboardApi.getDailyDataForDate(date);
        if (dayData) {
          recentData[dateKey] = dayData;
        }
      }

      setDailyData(recentData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshData = async (): Promise<void> => {
    await loadInitialData();
  };

  // =================================================================================
  // MODAL ACTIONS
  // =================================================================================
  const openLogModal = (data?: DailyData): void => {
    setCurrentLogData(data || null);
    setIsLogModalOpen(true);
  };

  const closeLogModal = (): void => {
    setIsLogModalOpen(false);
    setCurrentLogData(null);
  };

  const openInfoModal = (supplement: Supplement): void => {
    setSelectedSupplementInfo(supplement);
    setIsInfoModalOpen(true);
  };

  const closeInfoModal = (): void => {
    setIsInfoModalOpen(false);
    setSelectedSupplementInfo(null);
  };

  // =================================================================================
  // EMOTIONAL ACTIONS
  // =================================================================================
  const updateEmotionalState = (childName: string, state: EmotionalChildState): void => {
    setEmotionalStates((prev) => ({
      ...prev,
      [childName]: state,
    }));
  };

  const toggleEmotionalInsights = (): void => {
    setShowEmotionalInsights((prev) => !prev);
  };

  // =================================================================================
  // EFFECT HOOKS
  // =================================================================================
  useEffect(() => {
    loadInitialData();
  }, []);

  // =================================================================================
  // RETURN STATE AND ACTIONS
  // =================================================================================
  const state: ParentDashboardState = {
    children,
    supplements,
    dailyData,
    dailyLimits,
    selectedChild,
    viewMode,
    selectedDate,
    isLoading,
    isLogModalOpen,
    currentLogData,
    isInfoModalOpen,
    selectedSupplementInfo,
    emotionalStates,
    zenMoonState,
    selectedEmotion,
    showEmotionalInsights,
  };

  const actions: ParentDashboardActions = {
    loadInitialData,
    refreshData,
    setSelectedChild,
    setViewMode,
    setSelectedDate,
    openLogModal,
    closeLogModal,
    openInfoModal,
    closeInfoModal,
    setSelectedEmotion,
    updateEmotionalState,
    toggleEmotionalInsights,
  };

  return [state, actions];
};

export default useParentDashboardState;
