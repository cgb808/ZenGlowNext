import React, { useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useUIElements } from '../contexts/UIElementContext';
import { companionAccessibility } from '../utils/CompanionAccessibility';

/**
 * Example screen showing how to integrate with the Enhanced ZenGlow Companion
 * This demonstrates:
 * - UI element registration for companion awareness
 * - Accessibility integration
 * - Context-aware interactions
 */
export const CompanionExampleScreen: React.FC = () => {
  const { registerElement, unregisterElement } = useUIElements();

  useEffect(() => {
    // Provide contextual help when screen loads
    companionAccessibility.provideContextualHelp({
      currentScreen: 'example',
      lastUserAction: 'navigation',
      timeIdle: 0,
      timeOfDay: 'afternoon',
      sessionDuration: 30000,
    });

    return () => {
      // Cleanup any registered elements
      unregisterElement('welcome-card');
      unregisterElement('action-button');
      unregisterElement('settings-button');
    };
  }, [registerElement, unregisterElement]);

  const handleWelcomeCardLayout = (event: any) => {
    const { layout } = event.nativeEvent;
    registerElement('welcome-card', {
      ...layout,
      id: 'welcome-card',
      type: 'card',
      priority: 'high',
      interactive: true,
      accessible: true,
      metadata: {
        title: 'Welcome Card',
        description: 'Main welcome message for users',
      },
    });
  };

  const handleActionButtonLayout = (event: any) => {
    const { layout } = event.nativeEvent;
    registerElement('action-button', {
      ...layout,
      id: 'action-button',
      type: 'button',
      priority: 'medium',
      interactive: true,
      accessible: true,
      metadata: {
        title: 'Start Meditation',
        description: 'Primary action button',
      },
    });
  };

  const handleSettingsButtonLayout = (event: any) => {
    const { layout } = event.nativeEvent;
    registerElement('settings-button', {
      ...layout,
      id: 'settings-button',
      type: 'button',
      priority: 'low',
      interactive: true,
      accessible: true,
      metadata: {
        title: 'Settings',
        description: 'Access app settings',
      },
    });
  };

  const handleActionPress = () => {
    // Provide accessibility guidance
    companionAccessibility.announceForScreenReader(
      'Meditation session started. The companion will guide you through the process.',
      'assertive'
    );
  };

  const handleSettingsPress = () => {
    companionAccessibility.provideTouchGuidance('Settings Menu', { x: 100, y: 200 });
  };

  return (
    <View style={styles.container}>
      <View 
        style={styles.welcomeCard}
        onLayout={handleWelcomeCardLayout}
      >
        <Text style={styles.welcomeTitle}>Welcome to ZenGlow!</Text>
        <Text style={styles.welcomeText}>
          Your AI companion is here to help you on your mindfulness journey.
          Try interacting with different elements to see how the companion responds!
        </Text>
      </View>

      <TouchableOpacity
        style={styles.actionButton}
        onLayout={handleActionButtonLayout}
        onPress={handleActionPress}
        accessibilityLabel="Start meditation session"
        accessibilityHint="Double tap to begin a guided meditation"
      >
        <Text style={styles.actionButtonText}>Start Meditation</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.settingsButton}
        onLayout={handleSettingsButtonLayout}
        onPress={handleSettingsPress}
        accessibilityLabel="Open settings"
        accessibilityHint="Double tap to access companion and app settings"
      >
        <Text style={styles.settingsButtonText}>⚙️ Settings</Text>
      </TouchableOpacity>

      <View style={styles.infoBox}>
        <Text style={styles.infoTitle}>Companion Features:</Text>
        <Text style={styles.infoText}>
          • Intelligent context awareness{'\n'}
          • Voice announcements for accessibility{'\n'}
          • Mood-based animations{'\n'}
          • Proactive assistance{'\n'}
          • Personalized interactions
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  welcomeCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  welcomeTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  welcomeText: {
    fontSize: 16,
    color: '#666',
    lineHeight: 24,
  },
  actionButton: {
    backgroundColor: '#4FC3F7',
    borderRadius: 25,
    paddingVertical: 15,
    paddingHorizontal: 30,
    marginBottom: 15,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  actionButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  settingsButton: {
    backgroundColor: '#E0E0E0',
    borderRadius: 20,
    paddingVertical: 10,
    paddingHorizontal: 20,
    marginBottom: 20,
    alignItems: 'center',
  },
  settingsButtonText: {
    color: '#666',
    fontSize: 16,
  },
  infoBox: {
    backgroundColor: '#E3F2FD',
    borderRadius: 10,
    padding: 15,
    borderLeftWidth: 4,
    borderLeftColor: '#4FC3F7',
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1976D2',
    marginBottom: 10,
  },
  infoText: {
    fontSize: 14,
    color: '#424242',
    lineHeight: 20,
  },
});