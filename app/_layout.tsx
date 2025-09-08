import React, { Component, ErrorInfo, ReactNode, useEffect } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { Stack } from 'expo-router';
import { ThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';

import { ZenGlowCompanion } from '../components/Companion/ZenGlowCompanion';
import { UIElementProvider } from '../contexts/UIElementContext';
import { ZenSoundProvider } from '../components/Audio/ZenSoundProvider';
import { useColorScheme } from '../hooks/useColorScheme';
import { AudioBootstrapper } from '../components/Audio/AudioBootstrapper';

import { logFeatureFlagStatus } from '../src/utils/featureFlags';

import { logger } from '../src/lib/logging';


// Error Boundary Component for better error handling
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class AppErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error using centralized logging system
    logger.error('App Error Boundary caught an error', {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      boundary: 'AppErrorBoundary',
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.errorContainer}>
          <Text style={styles.errorTitle}>Something went wrong</Text>
          <Text style={styles.errorMessage}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </Text>
          <TouchableOpacity style={styles.retryButton} onPress={this.handleRetry}>
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return this.props.children;
  }
}

// Companion Error Boundary specifically for the floating companion
class CompanionErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log companion errors with warn level since they don't crash the app
    logger.warn('Companion Error Boundary caught an error', {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      boundary: 'CompanionErrorBoundary',
    });
  }

  render() {
    if (this.state.hasError) {
      // Silently hide the companion if it errors - the main app continues
      return null;
    }

    return this.props.children;
  }
}

// Export error boundaries for testing
export { AppErrorBoundary, CompanionErrorBoundary };

export default function RootLayout() {
  const colorScheme = useColorScheme();

  // Log feature flag status on app startup
  useEffect(() => {
    logFeatureFlagStatus();
  }, []);

  return (
    <SafeAreaProvider>
      <AppErrorBoundary>
        <GestureHandlerRootView style={styles.flex}>
          <ZenSoundProvider>
            <UIElementProvider>
              <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
                <AudioBootstrapper />
                <View style={styles.rootContainer}>
                  {/* Main app content - this is your primary navigation */}
                  <View style={styles.mainContent}>
                    <Stack>
                      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
                      <Stack.Screen name="+not-found" />
                    </Stack>
                  </View>
                  
                  {/* Floating companion with its own error boundary */}
                  <CompanionErrorBoundary>
                    <ZenGlowCompanion />
                  </CompanionErrorBoundary>
                </View>
                <StatusBar style="auto" />
              </ThemeProvider>
            </UIElementProvider>
          </ZenSoundProvider>
        </GestureHandlerRootView>
      </AppErrorBoundary>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  rootContainer: {
    flex: 1,
    position: 'relative', // Ensures proper layering
  },
  mainContent: {
    flex: 1,
    zIndex: 1, // Main content behind companion
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
    textAlign: 'center',
  },
  errorMessage: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 24,
  },
  retryButton: {
    backgroundColor: '#4FC3F7',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 25,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
