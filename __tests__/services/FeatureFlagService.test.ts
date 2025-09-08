/**
 * Feature Flag Tests
 */

import { DEFAULT_FEATURE_FLAGS, FeatureFlagName } from '../../src/config/featureFlags';
import { FeatureFlagService } from '../../src/services/FeatureFlagService';

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

// Mock SecureStorage
jest.mock('../../src/utils/SecureDataStorage', () => ({
  SecureStorage: {
    getUserPreferences: jest.fn().mockResolvedValue({}),
    setUserPreferences: jest.fn().mockResolvedValue(true),
  },
}));

// Mock fetch for remote config
global.fetch = jest.fn();

describe('FeatureFlagService', () => {
  let service: FeatureFlagService;

  beforeEach(() => {
    // Reset service instance
    (FeatureFlagService as any).instance = null;
    service = FeatureFlagService.getInstance();
    (fetch as jest.Mock).mockClear();
  });

  describe('initialization', () => {
    it('should initialize with default values', async () => {
      await service.initialize();
      
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO);
      expect(service.getFlag('PREDICTIVE_INSIGHTS')).toBe(DEFAULT_FEATURE_FLAGS.PREDICTIVE_INSIGHTS);
    });

    it('should be a singleton', () => {
      const service1 = FeatureFlagService.getInstance();
      const service2 = FeatureFlagService.getInstance();
      
      expect(service1).toBe(service2);
    });
  });

  describe('flag management', () => {
    beforeEach(async () => {
      await service.initialize();
    });

    it('should get flag values', () => {
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(false);
      expect(service.getFlag('PREDICTIVE_INSIGHTS')).toBe(true);
    });

    it('should get all flags', () => {
      const allFlags = service.getAllFlags();
      
      expect(allFlags).toHaveProperty('ENHANCED_AUDIO');
      expect(allFlags).toHaveProperty('PREDICTIVE_INSIGHTS');
      expect(Object.keys(allFlags).length).toBeGreaterThan(0);
    });

    it('should set flags in development mode', async () => {
      const originalDev = (global as any).__DEV__;
      (global as any).__DEV__ = true;

      await service.setFlag('ENHANCED_AUDIO', true);
      
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(true);

      (global as any).__DEV__ = originalDev;
    });

    it('should not set flags in production mode', async () => {
      const originalDev = (global as any).__DEV__;
      (global as any).__DEV__ = false;

      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      await service.setFlag('ENHANCED_AUDIO', true);
      
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO);
      expect(consoleSpy).toHaveBeenCalledWith('🚫 Feature flag modification only allowed in development');

      consoleSpy.mockRestore();
      (global as any).__DEV__ = originalDev;
    });

    it('should reset flags to default values', async () => {
      const originalDev = (global as any).__DEV__;
      (global as any).__DEV__ = true;

      await service.setFlag('ENHANCED_AUDIO', true);
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(true);

      await service.resetFlag('ENHANCED_AUDIO');
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO);

      (global as any).__DEV__ = originalDev;
    });
  });

  describe('subscriptions', () => {
    beforeEach(async () => {
      await service.initialize();
    });

    it('should notify subscribers when flags change', async () => {
      const originalDev = (global as any).__DEV__;
      (global as any).__DEV__ = true;

      const mockListener = jest.fn();
      const unsubscribe = service.subscribe(mockListener);

      await service.setFlag('ENHANCED_AUDIO', true);

      expect(mockListener).toHaveBeenCalledWith(
        expect.objectContaining({
          ENHANCED_AUDIO: true,
        })
      );

      unsubscribe();
      (global as any).__DEV__ = originalDev;
    });

    it('should handle listener errors gracefully', async () => {
      const originalDev = (global as any).__DEV__;
      (global as any).__DEV__ = true;

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const errorListener = jest.fn(() => {
        throw new Error('Listener error');
      });

      service.subscribe(errorListener);
      await service.setFlag('ENHANCED_AUDIO', true);

      expect(consoleSpy).toHaveBeenCalledWith(
        '❌ Error in feature flag listener:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
      (global as any).__DEV__ = originalDev;
    });
  });

  describe('remote configuration', () => {
    beforeEach(async () => {
      await service.initialize();
    });

    it('should fetch remote configuration successfully', async () => {
      const mockResponse = {
        ENHANCED_AUDIO: true,
        NEW_DASHBOARD: true,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse),
      });

      await service.refreshRemoteConfig();

      expect(fetch).toHaveBeenCalledWith(
        'https://api.zenglow.app/feature-flags',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 5000,
        })
      );
    });

    it('should handle remote fetch errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await service.refreshRemoteConfig();

      expect(consoleSpy).toHaveBeenCalledWith(
        '⚠️ Failed to fetch remote configuration, using local fallback:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('should handle invalid remote response', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await service.refreshRemoteConfig();

      // Should not throw or crash, just log warning
      expect(service.getFlag('ENHANCED_AUDIO')).toBe(DEFAULT_FEATURE_FLAGS.ENHANCED_AUDIO);
    });
  });
});