/**
 * =================================================================================
 * FEATURE FLAG SERVICE
 * =================================================================================
 * Purpose: Core service for managing feature flags with remote and local support
 * 
 * Features:
 * - Environment variable overrides
 * - Remote configuration fetching
 * - Local storage persistence
 * - Safe fallback handling
 * =================================================================================
 */

import { SecureStorage } from '../utils/SecureDataStorage';
import { getFeatureFlagEnv } from '../../utils/env';
import { 
  DEFAULT_FEATURE_FLAGS, 
  FeatureFlagName, 
  FeatureFlagValue, 
  FeatureFlagConfig,
  FEATURE_FLAG_CONFIG,
  FLAG_ENV_PREFIX,
  STORAGE_KEYS
} from '../config/featureFlags';

/**
 * Feature Flag Service Class
 */
export class FeatureFlagService {
  private static instance: FeatureFlagService | null = null;
  private flags: FeatureFlagConfig = { ...DEFAULT_FEATURE_FLAGS };
  private listeners: Set<(flags: FeatureFlagConfig) => void> = new Set();
  private lastFetch: number = 0;

  /**
   * Singleton pattern for global access
   */
  static getInstance(): FeatureFlagService {
    if (!FeatureFlagService.instance) {
      FeatureFlagService.instance = new FeatureFlagService();
    }
    return FeatureFlagService.instance;
  }

  /**
   * Initialize the feature flag service
   */
  async initialize(): Promise<void> {
    try {
      // 1. Start with default values
      this.flags = { ...DEFAULT_FEATURE_FLAGS };

      // 2. Apply environment variable overrides
      this.applyEnvironmentOverrides();

      // 3. Load user overrides from storage
      await this.loadUserOverrides();

      // 4. Attempt to fetch remote configuration
      await this.fetchRemoteConfig();

      console.log('✅ Feature flags initialized:', this.flags);
    } catch (error) {
      console.warn('⚠️ Feature flag initialization failed, using defaults:', error);
      this.flags = { ...DEFAULT_FEATURE_FLAGS };
    }
  }

  /**
   * Get a specific feature flag value
   */
  getFlag(name: FeatureFlagName): FeatureFlagValue {
    return this.flags[name] ?? DEFAULT_FEATURE_FLAGS[name];
  }

  /**
   * Get all feature flags
   */
  getAllFlags(): FeatureFlagConfig {
    return { ...this.flags };
  }

  /**
   * Set a feature flag (for development/debugging)
   */
  async setFlag(name: FeatureFlagName, value: FeatureFlagValue): Promise<void> {
    if (__DEV__) {
      this.flags[name] = value;
      await this.saveUserOverrides();
      this.notifyListeners();
      console.log(`🚩 Feature flag updated: ${name} = ${value}`);
    } else {
      console.warn('🚫 Feature flag modification only allowed in development');
    }
  }

  /**
   * Reset a feature flag to its default value
   */
  async resetFlag(name: FeatureFlagName): Promise<void> {
    if (__DEV__) {
      this.flags[name] = DEFAULT_FEATURE_FLAGS[name];
      await this.saveUserOverrides();
      this.notifyListeners();
      console.log(`🔄 Feature flag reset: ${name} = ${DEFAULT_FEATURE_FLAGS[name]}`);
    }
  }

  /**
   * Subscribe to feature flag changes
   */
  subscribe(listener: (flags: FeatureFlagConfig) => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Apply environment variable overrides
   */
  private applyEnvironmentOverrides(): void {
    const envFlags = getFeatureFlagEnv();
    
    Object.entries(envFlags).forEach(([flagName, value]) => {
      if (flagName in DEFAULT_FEATURE_FLAGS && typeof value === 'boolean') {
        this.flags[flagName as FeatureFlagName] = value;
        console.log(`🌍 Environment override: ${flagName} = ${value}`);
      }
    });
  }

  /**
   * Load user overrides from storage
   */
  private async loadUserOverrides(): Promise<void> {
    try {
      const userOverrides = await SecureStorage.getUserPreferences('feature_flags');
      if (userOverrides && typeof userOverrides === 'object') {
        Object.entries(userOverrides).forEach(([key, value]) => {
          if (key in DEFAULT_FEATURE_FLAGS && typeof value === 'boolean') {
            this.flags[key as FeatureFlagName] = value;
          }
        });
        console.log('📱 Loaded user flag overrides from storage');
      }
    } catch (error) {
      console.warn('⚠️ Failed to load user overrides:', error);
    }
  }

  /**
   * Save user overrides to storage
   */
  private async saveUserOverrides(): Promise<void> {
    try {
      // Only save flags that differ from defaults
      const overrides: Partial<FeatureFlagConfig> = {};
      Object.entries(this.flags).forEach(([key, value]) => {
        const flagName = key as FeatureFlagName;
        if (value !== DEFAULT_FEATURE_FLAGS[flagName]) {
          overrides[flagName] = value;
        }
      });

      await SecureStorage.setUserPreferences('feature_flags', overrides);
      console.log('💾 Saved user flag overrides to storage');
    } catch (error) {
      console.error('❌ Failed to save user overrides:', error);
    }
  }

  /**
   * Fetch remote configuration
   */
  private async fetchRemoteConfig(): Promise<void> {
    // Check if we need to fetch (respect cache TTL)
    const now = Date.now();
    if (now - this.lastFetch < FEATURE_FLAG_CONFIG.CACHE_TTL) {
      return;
    }

    try {
      const response = await fetch(FEATURE_FLAG_CONFIG.REMOTE_ENDPOINT, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 5000, // 5 second timeout
      });

      if (response.ok) {
        const remoteFlags = await response.json();
        
        // Validate and apply remote flags
        if (remoteFlags && typeof remoteFlags === 'object') {
          Object.entries(remoteFlags).forEach(([key, value]) => {
            if (key in DEFAULT_FEATURE_FLAGS && typeof value === 'boolean') {
              // Apply remote flags, but don't override user preferences in dev mode
              this.flags[key as FeatureFlagName] = value;
            }
          });
          
          this.lastFetch = now;
          this.notifyListeners();
          console.log('🌐 Applied remote feature flag configuration');
        }
      }
    } catch (error) {
      console.warn('⚠️ Failed to fetch remote configuration, using local fallback:', error);
    }
  }

  /**
   * Get current user overrides
   */
  private async getUserOverrides(): Promise<Partial<FeatureFlagConfig>> {
    try {
      const userOverrides = await SecureStorage.getUserPreferences('feature_flags');
      return userOverrides || {};
    } catch {
      return {};
    }
  }

  /**
   * Notify all listeners of flag changes
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener({ ...this.flags });
      } catch (error) {
        console.error('❌ Error in feature flag listener:', error);
      }
    });
  }

  /**
   * Refresh remote configuration manually
   */
  async refreshRemoteConfig(): Promise<void> {
    this.lastFetch = 0; // Reset cache
    await this.fetchRemoteConfig();
  }
}

/**
 * Global feature flag service instance
 */
export const featureFlagService = FeatureFlagService.getInstance();