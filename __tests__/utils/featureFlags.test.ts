import { isMetricsDashboardEnabled, logFeatureFlagStatus, getFeatureFlagDebugInfo } from '../../src/utils/featureFlags';

// Mock console.log for testing
const originalLog = console.log;
let logOutput: string[] = [];

beforeEach(() => {
  logOutput = [];
  console.log = jest.fn((message: string) => {
    logOutput.push(message);
  });
  
  // Clear environment variables
  delete process.env.PARENT_DASHBOARD_METRICS;
});

afterEach(() => {
  console.log = originalLog;
});

describe('Feature Flags', () => {
  describe('isMetricsDashboardEnabled', () => {
    it('should return false by default when flag is not set', () => {
      expect(isMetricsDashboardEnabled()).toBe(false);
    });

    it('should return true when flag is set to "true"', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'true';
      expect(isMetricsDashboardEnabled()).toBe(true);
    });

    it('should return true when flag is set to "1"', () => {
      process.env.PARENT_DASHBOARD_METRICS = '1';
      expect(isMetricsDashboardEnabled()).toBe(true);
    });

    it('should return false when flag is set to "false"', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'false';
      expect(isMetricsDashboardEnabled()).toBe(false);
    });

    it('should return false when flag is set to "0"', () => {
      process.env.PARENT_DASHBOARD_METRICS = '0';
      expect(isMetricsDashboardEnabled()).toBe(false);
    });

    it('should return false for invalid flag values', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'invalid';
      expect(isMetricsDashboardEnabled()).toBe(false);
    });

    it('should return false for empty string', () => {
      process.env.PARENT_DASHBOARD_METRICS = '';
      expect(isMetricsDashboardEnabled()).toBe(false);
    });
  });

  describe('logFeatureFlagStatus', () => {
    it('should log legacy dashboard path when flag is disabled', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'false';
      
      logFeatureFlagStatus();
      
      expect(logOutput).toHaveLength(1);
      expect(logOutput[0]).toContain('📊 Dashboard Mode: Using legacy dashboard path');
      expect(logOutput[0]).toContain('PARENT_DASHBOARD_METRICS=false');
    });

    it('should log metrics-first dashboard path when flag is enabled', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'true';
      
      logFeatureFlagStatus();
      
      expect(logOutput).toHaveLength(1);
      expect(logOutput[0]).toContain('📊 Dashboard Mode: Using metrics-first dashboard path');
      expect(logOutput[0]).toContain('PARENT_DASHBOARD_METRICS=true');
    });

    it('should log default legacy path when flag is not set', () => {
      logFeatureFlagStatus();
      
      expect(logOutput).toHaveLength(1);
      expect(logOutput[0]).toContain('📊 Dashboard Mode: Using legacy dashboard path');
      expect(logOutput[0]).toContain('PARENT_DASHBOARD_METRICS=false');
    });
  });

  describe('getFeatureFlagDebugInfo', () => {
    it('should return debug info when flag is enabled', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'true';
      
      const debugInfo = getFeatureFlagDebugInfo();
      
      expect(debugInfo).toEqual({
        PARENT_DASHBOARD_METRICS: {
          enabled: true,
          rawValue: 'true'
        }
      });
    });

    it('should return debug info when flag is disabled', () => {
      process.env.PARENT_DASHBOARD_METRICS = 'false';
      
      const debugInfo = getFeatureFlagDebugInfo();
      
      expect(debugInfo).toEqual({
        PARENT_DASHBOARD_METRICS: {
          enabled: false,
          rawValue: 'false'
        }
      });
    });

    it('should return debug info when flag is not set', () => {
      const debugInfo = getFeatureFlagDebugInfo();
      
      expect(debugInfo).toEqual({
        PARENT_DASHBOARD_METRICS: {
          enabled: false,
          rawValue: undefined
        }
      });
    });
  });
});