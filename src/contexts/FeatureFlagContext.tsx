/**
 * =================================================================================
 * FEATURE FLAG CONTEXT
 * =================================================================================
 * Purpose: React Context for feature flag state management and subscriptions
 * 
 * Features:
 * - Global state management for feature flags
 * - Automatic initialization
 * - Real-time updates via subscriptions
 * - Type-safe access to flags
 * =================================================================================
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { featureFlagService } from '../services/FeatureFlagService';
import { 
  FeatureFlagName, 
  FeatureFlagValue, 
  FeatureFlagConfig,
  DEFAULT_FEATURE_FLAGS 
} from '../config/featureFlags';

/**
 * Feature Flag Context Value Interface
 */
interface FeatureFlagContextValue {
  flags: FeatureFlagConfig;
  getFlag: (name: FeatureFlagName) => FeatureFlagValue;
  setFlag: (name: FeatureFlagName, value: FeatureFlagValue) => Promise<void>;
  resetFlag: (name: FeatureFlagName) => Promise<void>;
  refreshRemoteConfig: () => Promise<void>;
  isInitialized: boolean;
}

/**
 * Feature Flag Context
 */
const FeatureFlagContext = createContext<FeatureFlagContextValue | null>(null);

/**
 * Feature Flag Provider Props
 */
interface FeatureFlagProviderProps {
  children: ReactNode;
}

/**
 * Feature Flag Provider Component
 */
export const FeatureFlagProvider: React.FC<FeatureFlagProviderProps> = ({ children }) => {
  const [flags, setFlags] = useState<FeatureFlagConfig>(DEFAULT_FEATURE_FLAGS);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let unsubscribeFunction: (() => void) | null = null;

    // Initialize feature flag service
    const initializeFlags = async () => {
      try {
        await featureFlagService.initialize();
        
        if (isMounted) {
          setFlags(featureFlagService.getAllFlags());
          setIsInitialized(true);
        }
      } catch (error) {
        console.error('❌ Failed to initialize feature flags:', error);
        if (isMounted) {
          setFlags(DEFAULT_FEATURE_FLAGS);
          setIsInitialized(true);
        }
      }
    };

    // Subscribe to flag changes
    unsubscribeFunction = featureFlagService.subscribe((updatedFlags) => {
      if (isMounted) {
        setFlags(updatedFlags);
      }
    });

    initializeFlags();

    return () => {
      isMounted = false;
      if (unsubscribeFunction) {
        unsubscribeFunction();
      }
    };
  }, []);

  /**
   * Get a specific feature flag value
   */
  const getFlag = (name: FeatureFlagName): FeatureFlagValue => {
    return featureFlagService.getFlag(name);
  };

  /**
   * Set a feature flag value (dev only)
   */
  const setFlag = async (name: FeatureFlagName, value: FeatureFlagValue): Promise<void> => {
    await featureFlagService.setFlag(name, value);
  };

  /**
   * Reset a feature flag to its default value (dev only)
   */
  const resetFlag = async (name: FeatureFlagName): Promise<void> => {
    await featureFlagService.resetFlag(name);
  };

  /**
   * Refresh remote configuration
   */
  const refreshRemoteConfig = async (): Promise<void> => {
    await featureFlagService.refreshRemoteConfig();
  };

  const contextValue: FeatureFlagContextValue = {
    flags,
    getFlag,
    setFlag,
    resetFlag,
    refreshRemoteConfig,
    isInitialized,
  };

  return (
    <FeatureFlagContext.Provider value={contextValue}>
      {children}
    </FeatureFlagContext.Provider>
  );
};

/**
 * Hook to access feature flag context
 */
export const useFeatureFlagContext = (): FeatureFlagContextValue => {
  const context = useContext(FeatureFlagContext);
  
  if (!context) {
    throw new Error(
      'useFeatureFlagContext must be used within a FeatureFlagProvider. ' +
      'Make sure to wrap your app with <FeatureFlagProvider>.'
    );
  }
  
  return context;
};