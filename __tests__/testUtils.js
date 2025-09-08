/**
 * Test Utilities for ZenGlow Testing Framework
 * Provides helper functions for testing components, hooks, and services
 */

import { testChildren, testDailyData, testAudioFiles } from '../testData/fixtures';

/**
 * Creates a mock React Navigation navigation object
 */
export const createMockNavigation = () => ({
  navigate: jest.fn(),
  goBack: jest.fn(),
  reset: jest.fn(),
  setParams: jest.fn(),
  dispatch: jest.fn(),
  canGoBack: jest.fn(() => true),
  getId: jest.fn(() => 'test-navigation-id'),
  getParent: jest.fn(),
  getState: jest.fn(() => ({
    routes: [],
    index: 0,
  })),
});

/**
 * Creates a mock route object for React Navigation
 */
export const createMockRoute = (params = {}) => ({
  key: 'test-route-key',
  name: 'TestScreen',
  params,
  path: undefined,
});

/**
 * Creates mock Supabase client for testing
 */
export const createMockSupabaseClient = () => ({
  auth: {
    getUser: jest.fn(() => Promise.resolve({ 
      data: { user: { id: 'test-user', email: 'test@example.com' } }, 
      error: null 
    })),
    signInWithPassword: jest.fn(),
    signUp: jest.fn(),
    signOut: jest.fn(),
    onAuthStateChange: jest.fn(),
  },
  from: jest.fn(() => ({
    select: jest.fn().mockReturnThis(),
    insert: jest.fn().mockReturnThis(),
    update: jest.fn().mockReturnThis(),
    delete: jest.fn().mockReturnThis(),
    eq: jest.fn().mockReturnThis(),
    order: jest.fn().mockReturnThis(),
    limit: jest.fn().mockReturnThis(),
    single: jest.fn(() => Promise.resolve({ data: testDailyData, error: null })),
  })),
  storage: {
    from: jest.fn(() => ({
      upload: jest.fn(),
      download: jest.fn(),
      remove: jest.fn(),
      list: jest.fn(),
    })),
  },
});

/**
 * Creates mock audio service for testing
 */
export const createMockAudioService = () => ({
  loadAudio: jest.fn(() => Promise.resolve({
    sound: {
      playAsync: jest.fn(),
      pauseAsync: jest.fn(),
      stopAsync: jest.fn(),
      unloadAsync: jest.fn(),
      setPositionAsync: jest.fn(),
      getStatusAsync: jest.fn(() => Promise.resolve({
        isLoaded: true,
        isPlaying: false,
        durationMillis: 300000,
        positionMillis: 0,
      })),
    },
  })),
  playAudio: jest.fn(),
  pauseAudio: jest.fn(),
  stopAudio: jest.fn(),
  setVolume: jest.fn(),
  getCurrentPosition: jest.fn(() => 0),
  getDuration: jest.fn(() => 300000),
  isPlaying: jest.fn(() => false),
});

/**
 * Utility to wait for async operations in tests
 */
export const waitFor = (ms = 0) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Utility to wait for condition to be true
 */
export const waitForCondition = async (condition, timeout = 5000, interval = 100) => {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return;
    }
    await waitFor(interval);
  }
  
  throw new Error(`Condition not met within ${timeout}ms`);
};

/**
 * Creates a test context provider wrapper
 */
export const createTestWrapper = (providers = {}) => {
  return ({ children }) => {
    let content = children;
    
    // Wrap with providers in reverse order
    Object.entries(providers).reverse().forEach(([name, Provider]) => {
      content = <Provider>{content}</Provider>;
    });
    
    return content;
  };
};

/**
 * Mock AsyncStorage for testing
 */
export const createMockAsyncStorage = () => {
  let storage = {};
  
  return {
    getItem: jest.fn((key) => Promise.resolve(storage[key] || null)),
    setItem: jest.fn((key, value) => {
      storage[key] = value;
      return Promise.resolve();
    }),
    removeItem: jest.fn((key) => {
      delete storage[key];
      return Promise.resolve();
    }),
    clear: jest.fn(() => {
      storage = {};
      return Promise.resolve();
    }),
    getAllKeys: jest.fn(() => Promise.resolve(Object.keys(storage))),
    multiGet: jest.fn((keys) => 
      Promise.resolve(keys.map(key => [key, storage[key] || null]))
    ),
    multiSet: jest.fn((keyValuePairs) => {
      keyValuePairs.forEach(([key, value]) => {
        storage[key] = value;
      });
      return Promise.resolve();
    }),
    multiRemove: jest.fn((keys) => {
      keys.forEach(key => delete storage[key]);
      return Promise.resolve();
    }),
  };
};

/**
 * Creates mock date functions for consistent testing
 */
export const createMockDate = (fixedDate = '2024-08-14T12:00:00Z') => {
  const mockDate = new Date(fixedDate);
  const originalDate = global.Date;
  
  global.Date = jest.fn(() => mockDate);
  global.Date.now = jest.fn(() => mockDate.getTime());
  global.Date.UTC = originalDate.UTC;
  global.Date.parse = originalDate.parse;
  
  return () => {
    global.Date = originalDate;
  };
};

/**
 * Performance testing utility
 */
export const measurePerformance = async (testFunction, expectedMaxTime) => {
  const startTime = performance.now();
  const result = await testFunction();
  const endTime = performance.now();
  const duration = endTime - startTime;
  
  return {
    result,
    duration,
    withinExpected: duration <= expectedMaxTime,
  };
};

/**
 * Memory usage testing utility
 */
export const measureMemoryUsage = () => {
  if (global.gc && typeof global.gc === 'function') {
    global.gc();
  }
  
  return process.memoryUsage();
};

/**
 * Validates Zen score (0-100)
 */
export const isValidZenScore = (score) => {
  return typeof score === 'number' && score >= 0 && score <= 100;
};

/**
 * Validates child safety content
 */
export const isChildSafeContent = (content) => {
  const unsafeKeywords = ['violent', 'scary', 'dangerous', 'inappropriate'];
  const lowercaseContent = content.toLowerCase();
  
  return !unsafeKeywords.some(keyword => lowercaseContent.includes(keyword));
};

/**
 * Validates audio file format
 */
export const isValidAudioFormat = (filename) => {
  const validExtensions = ['.mp3', '.wav', '.aac', '.m4a'];
  return validExtensions.some(ext => filename.toLowerCase().endsWith(ext));
};

/**
 * Creates test data for specific scenarios
 */
export const createTestData = {
  child: (overrides = {}) => ({
    ...testChildren[0],
    ...overrides,
  }),
  
  dailyData: (overrides = {}) => ({
    ...testDailyData['2024-08-14'],
    ...overrides,
  }),
  
  audioFile: (overrides = {}) => ({
    ...testAudioFiles[0],
    ...overrides,
  }),
  
  activity: (overrides = {}) => ({
    id: 'test-activity',
    type: 'breathing',
    duration: 300,
    completedAt: new Date().toISOString(),
    zenScoreContribution: 20,
    ...overrides,
  }),
};

/**
 * Error simulation utilities
 */
export const simulateError = {
  network: () => {
    throw new Error('Network request failed');
  },
  
  authentication: () => {
    throw new Error('Authentication failed');
  },
  
  validation: (field) => {
    throw new Error(`Validation failed for field: ${field}`);
  },
  
  audioLoad: () => {
    throw new Error('Audio file could not be loaded');
  },
};

/**
 * Test assertion helpers
 */
export const assertions = {
  expectZenScore: (score) => {
    expect(score).toBeValidZenScore();
  },
  
  expectChildSafeContent: (content) => {
    expect(isChildSafeContent(content)).toBe(true);
  },
  
  expectValidAudioFormat: (filename) => {
    expect(isValidAudioFormat(filename)).toBe(true);
  },
  
  expectPerformanceWithin: (duration, maxTime) => {
    expect(duration).toBeLessThanOrEqual(maxTime);
  },
};

/**
 * Cleanup utility for tests
 */
export const cleanup = () => {
  jest.clearAllMocks();
  jest.clearAllTimers();
  if (global.gc && typeof global.gc === 'function') {
    global.gc();
  }
};