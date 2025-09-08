/**
 * Test Data Fixtures for ZenGlow Testing Framework
 * Provides realistic test datasets for various components and scenarios
 */

export const testChildren = [
  {
    id: '1',
    name: 'Emma',
    age: 8,
    avatar: 'moon-happy',
    parentId: 'parent-1',
    createdAt: '2024-01-15T00:00:00Z',
    preferences: {
      favoriteColors: ['purple', 'blue'],
      bedtime: '20:00',
      wakeupTime: '07:00',
      favoriteActivities: ['breathing', 'stories'],
    },
  },
  {
    id: '2',
    name: 'Alex',
    age: 10,
    avatar: 'moon-calm',
    parentId: 'parent-1',
    createdAt: '2024-01-16T00:00:00Z',
    preferences: {
      favoriteColors: ['green', 'yellow'],
      bedtime: '21:00',
      wakeupTime: '07:30',
      favoriteActivities: ['meditation', 'music'],
    },
  },
];

export const testDailyData = {
  '2024-08-14': {
    childId: '1',
    date: '2024-08-14',
    zenScore: 75,
    mood: 'happy',
    activities: [
      {
        id: 'activity-1',
        type: 'breathing',
        duration: 300, // 5 minutes
        completedAt: '2024-08-14T19:00:00Z',
        zenScoreContribution: 20,
      },
      {
        id: 'activity-2', 
        type: 'story',
        duration: 900, // 15 minutes
        completedAt: '2024-08-14T19:30:00Z',
        zenScoreContribution: 25,
      },
    ],
    screenTime: 1800, // 30 minutes
    bedtime: '20:15',
    sleepQuality: 'good',
    notes: 'Had a great day, loved the new breathing exercise',
  },
  '2024-08-13': {
    childId: '1',
    date: '2024-08-13',
    zenScore: 82,
    mood: 'calm',
    activities: [
      {
        id: 'activity-3',
        type: 'meditation',
        duration: 600, // 10 minutes
        completedAt: '2024-08-13T18:45:00Z',
        zenScoreContribution: 30,
      },
    ],
    screenTime: 1200, // 20 minutes
    bedtime: '20:00',
    sleepQuality: 'excellent',
    notes: 'Very relaxed today',
  },
};

export const testAudioFiles = [
  {
    id: 'audio-1',
    title: 'Ocean Waves',
    category: 'nature',
    duration: 600,
    file: 'ocean-waves.mp3',
    isChildSafe: true,
    ageRating: 'all',
  },
  {
    id: 'audio-2',
    title: 'Gentle Breathing',
    category: 'breathing',
    duration: 300,
    file: 'gentle-breathing.mp3',
    isChildSafe: true,
    ageRating: 'all',
  },
  {
    id: 'audio-3',
    title: 'Bedtime Story',
    category: 'story',
    duration: 1200,
    file: 'bedtime-story.mp3',
    isChildSafe: true,
    ageRating: '6+',
  },
];

export const testExercises = [
  {
    id: 'exercise-1',
    title: 'Rainbow Breathing',
    type: 'breathing',
    duration: 300,
    description: 'Breathe in all the colors of the rainbow',
    instructions: [
      'Sit comfortably',
      'Imagine a rainbow',
      'Breathe in red... breathe out red',
      'Continue with all colors',
    ],
    ageGroup: '6-12',
    difficulty: 'easy',
    zenScoreValue: 20,
  },
  {
    id: 'exercise-2',
    title: 'Body Scan Adventure',
    type: 'meditation',
    duration: 600,
    description: 'Take an adventure through your body',
    instructions: [
      'Lie down comfortably',
      'Close your eyes',
      'Start at your toes',
      'Notice how each part feels',
    ],
    ageGroup: '8-12',
    difficulty: 'medium',
    zenScoreValue: 30,
  },
];

export const testUserProfiles = [
  {
    id: 'parent-1',
    type: 'parent',
    email: 'parent@example.com',
    name: 'Sarah Johnson',
    children: ['1', '2'],
    preferences: {
      notifications: true,
      dailyReports: true,
      emergencyAlerts: true,
    },
    createdAt: '2024-01-01T00:00:00Z',
  },
];

export const testSecurityData = {
  validTokens: [
    'valid-jwt-token-123',
    'valid-refresh-token-456',
  ],
  invalidTokens: [
    'expired-token',
    'malformed-token',
    'null',
    '',
  ],
  testPasswords: {
    valid: ['SecurePass123!', 'MyStrongP@ssw0rd'],
    invalid: ['123', 'password', 'abc', ''],
  },
  encryptionKeys: {
    valid: 'test-encryption-key-32-characters',
    invalid: 'short-key',
  },
};

export const testErrorScenarios = [
  {
    name: 'Network Error',
    error: new Error('Network request failed'),
    expectedBehavior: 'Show offline mode',
  },
  {
    name: 'Authentication Error',
    error: new Error('Unauthorized'),
    expectedBehavior: 'Redirect to login',
  },
  {
    name: 'Data Validation Error',
    error: new Error('Invalid data format'),
    expectedBehavior: 'Show validation message',
  },
  {
    name: 'Audio Loading Error',
    error: new Error('Audio file not found'),
    expectedBehavior: 'Show audio error state',
  },
];

export const testPerformanceMetrics = {
  expectedLoadTimes: {
    appLaunch: 3000, // 3 seconds
    screenTransition: 500, // 0.5 seconds
    audioLoad: 2000, // 2 seconds
    databaseQuery: 1000, // 1 second
  },
  memoryLimits: {
    maxHeapSize: 100 * 1024 * 1024, // 100MB
    maxAudioBuffers: 10,
  },
};

// Mock API responses
export const mockApiResponses = {
  supabase: {
    success: {
      data: testDailyData,
      error: null,
      status: 200,
      statusText: 'OK',
    },
    error: {
      data: null,
      error: {
        message: 'Database connection failed',
        details: 'Network timeout',
        hint: 'Check your internet connection',
      },
      status: 500,
      statusText: 'Internal Server Error',
    },
  },
  audio: {
    loadSuccess: {
      isLoaded: true,
      isPlaying: false,
      durationMillis: 300000,
      positionMillis: 0,
    },
    playSuccess: {
      isLoaded: true,
      isPlaying: true,
      durationMillis: 300000,
      positionMillis: 5000,
    },
  },
};

// Child safety test cases
export const childSafetyTestCases = {
  contentFilters: [
    {
      input: 'This is a nice story for children',
      expected: true,
      description: 'Safe content should pass',
    },
    {
      input: 'violent content with scary words',
      expected: false,
      description: 'Violent content should be blocked',
    },
    {
      input: 'Beautiful rainbow and unicorns',
      expected: true,
      description: 'Positive imagery should pass',
    },
  ],
  ageAppropriate: [
    {
      content: 'Simple breathing exercise',
      ageGroup: '6+',
      expected: true,
    },
    {
      content: 'Complex meditation technique',
      ageGroup: '12+',
      expected: false,
      testAge: 8,
    },
  ],
};