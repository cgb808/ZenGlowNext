/**
 * Jest Setup for ZenGlow Testing Framework
 * This file is executed before each test file
 */

// Mock React Native modules that aren't available in test environment
jest.mock('react-native', () => {
  const ReactNative = jest.requireActual('react-native');
  
  // Mock components that might not work in test environment
  ReactNative.NativeModules = {
    ...ReactNative.NativeModules,
    RNSound: {
      playSoundFile: jest.fn(),
      setCategory: jest.fn(),
    },
    AudioRecorderManager: {
      startRecording: jest.fn(),
      stopRecording: jest.fn(),
    },
  };
  
  return ReactNative;
});

// Mock Expo modules
jest.mock('expo-av', () => ({
  Audio: {
    setAudioModeAsync: jest.fn(),
    Sound: {
      createAsync: jest.fn(() => 
        Promise.resolve({
          sound: {
            playAsync: jest.fn(),
            pauseAsync: jest.fn(),
            stopAsync: jest.fn(),
            unloadAsync: jest.fn(),
            setPositionAsync: jest.fn(),
            getStatusAsync: jest.fn(() => 
              Promise.resolve({
                isLoaded: true,
                isPlaying: false,
                durationMillis: 30000,
                positionMillis: 0,
              })
            ),
          },
        })
      ),
    },
  },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(),
  notificationAsync: jest.fn(),
  selectionAsync: jest.fn(),
}));

jest.mock('expo-font', () => ({
  loadAsync: jest.fn(),
  isLoaded: jest.fn(() => true),
}));

jest.mock('expo-linear-gradient', () => ({
  LinearGradient: 'LinearGradient',
}));

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  getAllKeys: jest.fn(),
  multiGet: jest.fn(),
  multiSet: jest.fn(),
  multiRemove: jest.fn(),
}));

// Mock React Navigation
jest.mock('@react-navigation/native', () => ({
  useNavigation: () => ({
    navigate: jest.fn(),
    goBack: jest.fn(),
    reset: jest.fn(),
    canGoBack: jest.fn(() => true),
  }),
  useRoute: () => ({
    params: {},
  }),
  useFocusEffect: (callback) => {
    callback();
  },
  NavigationContainer: ({ children }) => children,
}));

jest.mock('@react-navigation/native-stack', () => ({
  createNativeStackNavigator: () => ({
    Navigator: ({ children }) => children,
    Screen: ({ children }) => children,
  }),
}));

// Mock expo-sqlite
jest.mock('expo-sqlite', () => ({
  openDatabaseAsync: jest.fn(),
}));

// Mock Supabase
jest.mock('@supabase/supabase-js', () => ({
  createClient: jest.fn(() => ({
    auth: {
      signIn: jest.fn(),
      signOut: jest.fn(),
      signUp: jest.fn(),
      getUser: jest.fn(),
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
      single: jest.fn(() => Promise.resolve({ data: null, error: null })),
    })),
    storage: {
      from: jest.fn(() => ({
        upload: jest.fn(),
        download: jest.fn(),
        remove: jest.fn(),
        list: jest.fn(),
      })),
    },
  })),
}));

// Mock React Native Paper components
jest.mock('react-native-paper', () => ({
  Button: 'Button',
  Card: 'Card',
  Text: 'Text',
  Surface: 'Surface',
  Provider: ({ children }) => children,
  Portal: ({ children }) => children,
  Modal: ({ children }) => children,
  DefaultTheme: {},
}));

// Mock React Native Vector Icons
jest.mock('react-native-vector-icons/MaterialIcons', () => 'MaterialIcons');
jest.mock('react-native-vector-icons/Ionicons', () => 'Ionicons');

// Mock dimensions
jest.mock('react-native/Libraries/Utilities/Dimensions', () => ({
  get: jest.fn(() => ({ width: 375, height: 812 })),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
}));

// Global test utilities
global.console = {
  ...console,
  // Suppress console.warn in tests unless needed
  warn: jest.fn(),
  error: jest.fn(),
};

// Add custom matchers if needed
expect.extend({
  toBeValidZenScore(received) {
    const isValid = typeof received === 'number' && received >= 0 && received <= 100;
    return {
      pass: isValid,
      message: () => 
        isValid 
          ? `Expected ${received} not to be a valid Zen score (0-100)`
          : `Expected ${received} to be a valid Zen score (0-100)`,
    };
  },
});

// Set up test timeout
jest.setTimeout(10000);

// Silence warnings that we don't care about in tests
const originalWarn = console.warn;
console.warn = (...args) => {
  if (
    args[0] &&
    (args[0].includes('Warning: ReactDOM.render is deprecated') ||
     args[0].includes('Warning: validateDOMNesting') ||
     args[0].includes('expo-linear-gradient'))
  ) {
    return;
  }
  originalWarn.apply(console, args);
};