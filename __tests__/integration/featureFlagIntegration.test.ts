import { isMetricsDashboardEnabled, logFeatureFlagStatus, getFeatureFlagDebugInfo } from '../../src/utils/featureFlags';

describe('Feature Flag Integration Test', () => {
  const originalLog = console.log;
  let logOutput: string[] = [];

  beforeEach(() => {
    logOutput = [];
    console.log = jest.fn((message: string) => {
      logOutput.push(message);
    });
  });

  afterEach(() => {
    console.log = originalLog;
  });

  it('should demonstrate complete feature flag workflow', () => {
    // Test default behavior (flag not set)
    delete process.env.PARENT_DASHBOARD_METRICS;
    expect(isMetricsDashboardEnabled()).toBe(false);
    
    logFeatureFlagStatus();
    expect(logOutput[0]).toContain('Using legacy dashboard path');
    
    let debugInfo = getFeatureFlagDebugInfo();
    expect(debugInfo.PARENT_DASHBOARD_METRICS.enabled).toBe(false);
    expect(debugInfo.PARENT_DASHBOARD_METRICS.rawValue).toBeUndefined();

    // Test flag enabled
    logOutput.length = 0;
    process.env.PARENT_DASHBOARD_METRICS = 'true';
    expect(isMetricsDashboardEnabled()).toBe(true);
    
    logFeatureFlagStatus();
    expect(logOutput[0]).toContain('Using metrics-first dashboard path');
    
    debugInfo = getFeatureFlagDebugInfo();
    expect(debugInfo.PARENT_DASHBOARD_METRICS.enabled).toBe(true);
    expect(debugInfo.PARENT_DASHBOARD_METRICS.rawValue).toBe('true');

    // Test flag disabled
    logOutput.length = 0;
    process.env.PARENT_DASHBOARD_METRICS = 'false';
    expect(isMetricsDashboardEnabled()).toBe(false);
    
    logFeatureFlagStatus();
    expect(logOutput[0]).toContain('Using legacy dashboard path');
    
    debugInfo = getFeatureFlagDebugInfo();
    expect(debugInfo.PARENT_DASHBOARD_METRICS.enabled).toBe(false);
    expect(debugInfo.PARENT_DASHBOARD_METRICS.rawValue).toBe('false');

    // Test numeric flag
    logOutput.length = 0;
    process.env.PARENT_DASHBOARD_METRICS = '1';
    expect(isMetricsDashboardEnabled()).toBe(true);
    
    logFeatureFlagStatus();
    expect(logOutput[0]).toContain('Using metrics-first dashboard path');
    
    debugInfo = getFeatureFlagDebugInfo();
    expect(debugInfo.PARENT_DASHBOARD_METRICS.enabled).toBe(true);
    expect(debugInfo.PARENT_DASHBOARD_METRICS.rawValue).toBe('1');
  });
});