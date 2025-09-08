// Feature Flag Utilities for ZenGlow

/**
 * Get environment variable with fallback support for different environments
 */
function getEnvironmentVariable(key: string): string | undefined {
  // Try process.env first (Node.js, tests)
  if (typeof process !== 'undefined' && process.env && process.env[key]) {
    return process.env[key];
  }
  
  // Try Expo Constants (React Native) - wrapped in try-catch for test environments
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Constants = require('expo-constants').default;
    const expoValue = Constants?.expoConfig?.extra?.[key];
    if (expoValue !== undefined) {
      return expoValue;
    }
  } catch {
    // Expo Constants not available, continue with process.env fallback
  }
  
  return undefined;
}

/**
 * Check if metrics-first dashboard is enabled
 * 
 * @returns true if PARENT_DASHBOARD_METRICS feature flag is enabled, false otherwise
 */
export function isMetricsDashboardEnabled(): boolean {
  const flagValue = getEnvironmentVariable('PARENT_DASHBOARD_METRICS');
  
  // Convert string values to boolean, default to false for safety
  if (flagValue === 'true' || flagValue === '1') {
    return true;
  }
  
  return false;
}

/**
 * Log feature flag status at startup
 * This should be called once during app initialization
 */
export function logFeatureFlagStatus(): void {
  const isEnabled = isMetricsDashboardEnabled();
  const pathType = isEnabled ? 'metrics-first' : 'legacy';
  
  console.log(`📊 Dashboard Mode: Using ${pathType} dashboard path (PARENT_DASHBOARD_METRICS=${isEnabled})`);
}

/**
 * Get all feature flag states for debugging
 */
export function getFeatureFlagDebugInfo(): Record<string, any> {
  return {
    PARENT_DASHBOARD_METRICS: {
      enabled: isMetricsDashboardEnabled(),
      rawValue: getEnvironmentVariable('PARENT_DASHBOARD_METRICS')
    }
  };
}