/**
 * =================================================================================
 * FEATURE FLAG USAGE EXAMPLES
 * =================================================================================
 * Purpose: Example components showing how to use the feature flag system
 * =================================================================================
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useFeatureFlag, useFeatureFlags } from '../hooks/useFeatureFlag';
import { DevFlagsScreen } from '../components/DevFlagsScreen';

/**
 * Example: Using a single feature flag
 */
export const AudioControlExample: React.FC = () => {
  const enhancedAudioEnabled = useFeatureFlag('ENHANCED_AUDIO');
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Audio Controls</Text>
      {enhancedAudioEnabled ? (
        <View>
          <Text>🎵 Enhanced Audio Features Available</Text>
          <TouchableOpacity style={styles.button}>
            <Text style={styles.buttonText}>Advanced Audio Settings</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View>
          <Text>🎵 Basic Audio Controls</Text>
          <TouchableOpacity style={styles.button}>
            <Text style={styles.buttonText}>Simple Audio Settings</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

/**
 * Example: Using multiple feature flags
 */
export const DashboardExample: React.FC = () => {
  const flags = useFeatureFlags(['NEW_DASHBOARD', 'QUICK_ACTIONS', 'AI_RECOMMENDATIONS']);
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>
        {flags.NEW_DASHBOARD ? 'New Dashboard' : 'Classic Dashboard'}
      </Text>
      
      <View style={styles.content}>
        <Text>Welcome to ZenGlow!</Text>
        
        {flags.QUICK_ACTIONS && (
          <View style={styles.quickActions}>
            <Text style={styles.sectionTitle}>⚡ Quick Actions</Text>
            <TouchableOpacity style={styles.quickActionButton}>
              <Text>Start Session</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionButton}>
              <Text>View Progress</Text>
            </TouchableOpacity>
          </View>
        )}
        
        {flags.AI_RECOMMENDATIONS && (
          <View style={styles.aiSection}>
            <Text style={styles.sectionTitle}>🤖 AI Recommendations</Text>
            <Text>Based on your recent activity, we recommend:</Text>
            <Text style={styles.recommendation}>• Try a 10-minute meditation</Text>
            <Text style={styles.recommendation}>• Practice breathing exercises</Text>
          </View>
        )}
      </View>
    </View>
  );
};

/**
 * Example: Development flags screen (only shows in dev)
 */
export const DevToolsExample: React.FC = () => {
  if (!__DEV__) {
    return null;
  }
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Development Tools</Text>
      <DevFlagsScreen />
    </View>
  );
};

/**
 * Example: Conditional UI based on experimental features
 */
export const ExperimentalFeaturesExample: React.FC = () => {
  const flags = useFeatureFlags(['VOICE_CONTROL', 'GESTURE_NAVIGATION', 'BIOMETRIC_AUTH']);
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Experimental Features</Text>
      
      {flags.VOICE_CONTROL && (
        <TouchableOpacity style={styles.experimentalButton}>
          <Text style={styles.buttonText}>🎤 Voice Control</Text>
        </TouchableOpacity>
      )}
      
      {flags.GESTURE_NAVIGATION && (
        <TouchableOpacity style={styles.experimentalButton}>
          <Text style={styles.buttonText}>👋 Gesture Navigation</Text>
        </TouchableOpacity>
      )}
      
      {flags.BIOMETRIC_AUTH && (
        <TouchableOpacity style={styles.experimentalButton}>
          <Text style={styles.buttonText}>👆 Biometric Login</Text>
        </TouchableOpacity>
      )}
      
      {!Object.values(flags).some(Boolean) && (
        <Text style={styles.noFeatures}>No experimental features enabled</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  content: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 8,
    marginTop: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
    color: '#444',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 6,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  quickActions: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#f0f8ff',
    borderRadius: 6,
  },
  quickActionButton: {
    backgroundColor: '#007AFF',
    padding: 8,
    borderRadius: 4,
    alignItems: 'center',
    marginVertical: 4,
  },
  aiSection: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#f0fff0',
    borderRadius: 6,
  },
  recommendation: {
    color: '#666',
    marginLeft: 8,
    marginVertical: 2,
  },
  experimentalButton: {
    backgroundColor: '#FF9500',
    padding: 12,
    borderRadius: 6,
    alignItems: 'center',
    marginVertical: 4,
  },
  noFeatures: {
    color: '#666',
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 20,
  },
});