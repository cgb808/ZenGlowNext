/**
 * =================================================================================
 * FEATURE FLAGS CONFIGURATION
 * =================================================================================
 * Purpose: Centralized feature flag definitions with default values
 * 
 * Features:
 * - Default flag values
 * - Type safety with TypeScript
 * - Environment variable overrides
 * - Remote configuration support
 * =================================================================================
 */

/**
 * Feature flag definitions with default values
 */
export const DEFAULT_FEATURE_FLAGS = {
  // Core Features
  ENHANCED_AUDIO: false,
  PREDICTIVE_INSIGHTS: true,
  AVATAR_ANIMATIONS: true,
  
  // UI Features
  NEW_DASHBOARD: false,
  DARK_MODE_TOGGLE: true,
  QUICK_ACTIONS: false,
  
  // Experimental Features
  AI_RECOMMENDATIONS: false,
  VOICE_CONTROL: false,
  GESTURE_NAVIGATION: false,
  
  // Development Features
  DEBUG_PANELS: false,
  PERFORMANCE_MONITORING: false,
  
  // Security Features
  BIOMETRIC_AUTH: false,
  ENHANCED_ENCRYPTION: true,
} as const;

/**
 * Type definition for feature flag names
 */
export type FeatureFlagName = keyof typeof DEFAULT_FEATURE_FLAGS;

/**
 * Type definition for feature flag values
 */
export type FeatureFlagValue = boolean;

/**
 * Type definition for feature flag configuration
 */
export type FeatureFlagConfig = Record<FeatureFlagName, FeatureFlagValue>;

/**
 * Remote feature flag configuration endpoint
 */
export const FEATURE_FLAG_CONFIG = {
  REMOTE_ENDPOINT: 'https://api.zenglow.app/feature-flags',
  CACHE_TTL: 5 * 60 * 1000, // 5 minutes
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
} as const;

/**
 * Environment variable prefix for feature flags
 */
export const FLAG_ENV_PREFIX = 'FLAG_';

/**
 * Storage keys for feature flags
 */
export const STORAGE_KEYS = {
  USER_OVERRIDES: 'feature_flags_user_overrides',
  REMOTE_CONFIG: 'feature_flags_remote_config',
  LAST_FETCH: 'feature_flags_last_fetch',
} as const;