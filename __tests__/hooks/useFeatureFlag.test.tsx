/**
 * useFeatureFlag Hook Tests
 */

import React from 'react';
import { renderHook } from '@testing-library/react-native';
import { useFeatureFlag, useFeatureFlags } from '../../src/hooks/useFeatureFlag';
import { FeatureFlagProvider } from '../../src/contexts/FeatureFlagContext';
import { DEFAULT_FEATURE_FLAGS } from '../../src/config/featureFlags';

// Mock expo-constants
jest.mock('expo-constants', () => ({
  __esModule: true,
  default: {
    expoConfig: {
      extra: {
        featureFlags: {},
      },
    },
  },
}));

// Mock utils/env
jest.mock('../../utils/env', () => ({
  getFeatureFlagEnv: jest.fn().mockReturnValue({}),
}));

// Mock the FeatureFlagService
jest.mock('../../src/services/FeatureFlagService', () => ({
  featureFlagService: {
    initialize: jest.fn().mockResolvedValue(undefined),
    getAllFlags: jest.fn().mockReturnValue({
      ENHANCED_AUDIO: false,
      PREDICTIVE_INSIGHTS: true,
      AVATAR_ANIMATIONS: true,
      NEW_DASHBOARD: false,
      DARK_MODE_TOGGLE: true,
      QUICK_ACTIONS: false,
      AI_RECOMMENDATIONS: false,
      VOICE_CONTROL: false,
      GESTURE_NAVIGATION: false,
      DEBUG_PANELS: false,
      PERFORMANCE_MONITORING: false,
      BIOMETRIC_AUTH: false,
      ENHANCED_ENCRYPTION: true,
    }),
    getFlag: jest.fn((name) => {
      const mockFlags = {
        ENHANCED_AUDIO: false,
        PREDICTIVE_INSIGHTS: true,
        AVATAR_ANIMATIONS: true,
        NEW_DASHBOARD: false,
        DARK_MODE_TOGGLE: true,
        QUICK_ACTIONS: false,
        AI_RECOMMENDATIONS: false,
        VOICE_CONTROL: false,
        GESTURE_NAVIGATION: false,
        DEBUG_PANELS: false,
        PERFORMANCE_MONITORING: false,
        BIOMETRIC_AUTH: false,
        ENHANCED_ENCRYPTION: true,
      };
      return mockFlags[name];
    }),
    setFlag: jest.fn().mockResolvedValue(undefined),
    resetFlag: jest.fn().mockResolvedValue(undefined),
    refreshRemoteConfig: jest.fn().mockResolvedValue(undefined),
    subscribe: jest.fn(() => jest.fn()), // Return a proper unsubscribe function
  },
}));

// Mock SecureStorage
jest.mock('../../src/utils/SecureDataStorage', () => ({
  SecureStorage: {
    getUserPreferences: jest.fn().mockResolvedValue({}),
    setUserPreferences: jest.fn().mockResolvedValue(true),
  },
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <FeatureFlagProvider>{children}</FeatureFlagProvider>
);

describe('useFeatureFlag', () => {
  it('should return default value for a feature flag', () => {
    const { result } = renderHook(() => useFeatureFlag('ENHANCED_AUDIO'), { wrapper });
    
    expect(result.current).toBe(DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO);
  });

  it('should return default value when context is not available', () => {
    const { result } = renderHook(() => useFeatureFlag('ENHANCED_AUDIO'));
    
    expect(result.current).toBe(DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO);
  });
});

describe('useFeatureFlags', () => {
  it('should return multiple feature flags', () => {
    const { result } = renderHook(
      () => useFeatureFlags(['ENHANCED_AUDIO', 'PREDICTIVE_INSIGHTS']),
      { wrapper }
    );
    
    expect(result.current).toEqual({
      ENHANCED_AUDIO: DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO,
      PREDICTIVE_INSIGHTS: DEFAULT_FEATURE_FLAGS.PREDICTIVE_INSIGHTS,
    });
  });

  it('should return default values when context is not available', () => {
    const { result } = renderHook(() => useFeatureFlags(['ENHANCED_AUDIO', 'PREDICTIVE_INSIGHTS']));
    
    expect(result.current).toEqual({
      ENHANCED_AUDIO: DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO,
      PREDICTIVE_INSIGHTS: DEFAULT_FEATURE_FLAGS.PREDICTIVE_INSIGHTS,
    });
  });
});