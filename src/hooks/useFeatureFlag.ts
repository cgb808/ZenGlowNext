/**
 * =================================================================================
 * USE FEATURE FLAG HOOK
 * =================================================================================
 * Purpose: Simple hook for consuming individual feature flags
 * 
 * Features:
 * - Easy access to individual flags
 * - Automatic re-renders on flag changes
 * - Type safety
 * - Fallback to default values
 * =================================================================================
 */

import { useFeatureFlagContext } from '../contexts/FeatureFlagContext';
import { FeatureFlagName, FeatureFlagValue, DEFAULT_FEATURE_FLAGS } from '../config/featureFlags';

/**
 * Hook to get a specific feature flag value
 * 
 * @param name - The name of the feature flag
 * @returns The current value of the feature flag
 * 
 * @example
 * ```tsx
 * const isDarkModeEnabled = useFeatureFlag('DARK_MODE_TOGGLE');
 * const showNewDashboard = useFeatureFlag('NEW_DASHBOARD');
 * 
 * return (
 *   <View>
 *     {showNewDashboard ? <NewDashboard /> : <LegacyDashboard />}
 *     {isDarkModeEnabled && <DarkModeButton />}
 *   </View>
 * );
 * ```
 */
export function useFeatureFlag(name: FeatureFlagName): FeatureFlagValue {
  try {
    const { getFlag, isInitialized } = useFeatureFlagContext();
    
    // If not yet initialized, return default value
    if (!isInitialized) {
      return DEFAULT_FEATURE_FLAGS[name];
    }
    
    return getFlag(name);
  } catch (error) {
    // Fallback to default if context is not available
    console.warn(`⚠️ Feature flag context not available for ${name}, using default value`);
    return DEFAULT_FEATURE_FLAGS[name];
  }
}

/**
 * Hook to get multiple feature flags at once
 * 
 * @param names - Array of feature flag names
 * @returns Object with flag names as keys and their values
 * 
 * @example
 * ```tsx
 * const flags = useFeatureFlags(['DARK_MODE_TOGGLE', 'NEW_DASHBOARD', 'AI_RECOMMENDATIONS']);
 * 
 * return (
 *   <View>
 *     {flags.NEW_DASHBOARD ? <NewDashboard /> : <LegacyDashboard />}
 *     {flags.AI_RECOMMENDATIONS && <AIPanel />}
 *   </View>
 * );
 * ```
 */
export function useFeatureFlags<T extends FeatureFlagName[]>(
  names: T
): Record<T[number], FeatureFlagValue> {
  try {
    const { flags, isInitialized } = useFeatureFlagContext();
    
    const result = {} as Record<T[number], FeatureFlagValue>;
    
    names.forEach((name) => {
      if (!isInitialized) {
        result[name] = DEFAULT_FEATURE_FLAGS[name];
      } else {
        result[name] = flags[name] ?? DEFAULT_FEATURE_FLAGS[name];
      }
    });
    
    return result;
  } catch (error) {
    // Fallback to defaults if context is not available
    console.warn('⚠️ Feature flag context not available, using default values');
    const result = {} as Record<T[number], FeatureFlagValue>;
    names.forEach((name) => {
      result[name] = DEFAULT_FEATURE_FLAGS[name];
    });
    return result;
  }
}

/**
 * Hook for development flag management
 * Only available in development mode
 * 
 * @returns Development utilities for managing flags
 */
export function useFeatureFlagDev() {
  const context = useFeatureFlagContext();
  
  if (!__DEV__) {
    return {
      setFlag: () => Promise.resolve(),
      resetFlag: () => Promise.resolve(),
      refreshRemoteConfig: () => Promise.resolve(),
      getAllFlags: () => ({}),
    };
  }
  
  return {
    setFlag: context.setFlag,
    resetFlag: context.resetFlag,
    refreshRemoteConfig: context.refreshRemoteConfig,
    getAllFlags: () => context.flags,
  };
}