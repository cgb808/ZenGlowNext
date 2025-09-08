/**
 * =================================================================================
 * SECURE CONNECTION EXAMPLES - Sample Implementation Patterns
 * =================================================================================
 * Purpose: Demonstrate secure parent-child connection patterns
 * Shows: How to implement encrypted communication safely
 * =================================================================================
 */

import React, { useState, useEffect } from 'react';
import { View, Text, Button, TextInput, Alert, StyleSheet } from 'react-native';
import { secureConnectionManager } from '../src/utils/SecureConnectionManager';

/**
 * Parent Component - Generates connection codes and monitors child
 */
export const ParentConnectionScreen: React.FC = () => {
  const [connectionCode, setConnectionCode] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<any>(null);

  // Generate connection code
  const generateCode = async () => {
    try {
      const code = await secureConnectionManager.generateConnectionCode('parent_demo');
      setConnectionCode(code);
      Alert.alert('Connection Code Generated', `Share this code with your child: ${code}`);
    } catch (error) {
      Alert.alert('Error', 'Failed to generate connection code');
      console.error(error);
    }
  };

  // Monitor connection status
  useEffect(() => {
    const interval = setInterval(() => {
      const status = secureConnectionManager.getConnectionStatus();
      setConnectionStatus(status);
      setIsConnected(status.isConnected);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Send encouragement to child
  const sendEncouragement = async () => {
    try {
      await secureConnectionManager.sendSecureData({
        type: 'encouragement',
        message: 'You\'re doing great! Keep breathing deeply.',
        timestamp: Date.now()
      }, 'child');
      
      Alert.alert('Encouragement Sent', 'Your child will receive this message securely');
    } catch (error) {
      Alert.alert('Error', 'Failed to send message');
      console.error(error);
    }
  };

  // Disconnect
  const disconnect = async () => {
    try {
      await secureConnectionManager.disconnect();
      setIsConnected(false);
      setConnectionCode('');
      Alert.alert('Disconnected', 'Connection ended safely');
    } catch (error) {
      Alert.alert('Error', 'Failed to disconnect');
      console.error(error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Parent Dashboard</Text>
      
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connection Management</Text>
        
        {!connectionCode ? (
          <Button title="Generate Connection Code" onPress={generateCode} />
        ) : (
          <View>
            <Text style={styles.codeText}>Connection Code: {connectionCode}</Text>
            <Text style={styles.instructions}>
              Share this code with your child to establish a secure connection
            </Text>
          </View>
        )}
      </View>

      {isConnected && (
        <View style={styles.section}>
          <Text style={styles.connectedText}>🔗 Connected Securely</Text>
          <Text style={styles.statusText}>
            Time Remaining: {Math.round((connectionStatus?.timeRemaining || 0) / 1000)}s
          </Text>
          
          <View style={styles.buttonContainer}>
            <Button title="Send Encouragement" onPress={sendEncouragement} />
            <Button title="Disconnect" onPress={disconnect} color="#e74c3c" />
          </View>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Security Status</Text>
        <Text style={styles.statusText}>
          Connection: {isConnected ? '🟢 Secure' : '🔴 Not Connected'}
        </Text>
        <Text style={styles.statusText}>
          Encryption: 🔒 AES-256 Enabled
        </Text>
        <Text style={styles.statusText}>
          Data Privacy: 🛡️ Child Health Data Protected
        </Text>
      </View>
    </View>
  );
};

/**
 * Child Component - Connects using code and shares progress
 */
export const ChildConnectionScreen: React.FC = () => {
  const [inputCode, setInputCode] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState({
    currentStep: 1,
    completionPercentage: 25,
    breathingSync: true,
    engagementLevel: 0.8,
    lastUpdate: new Date(),
    // Sensitive data (not shared with parent)
    heartRate: 85,
    stressLevel: 0.3
  });

  // Connect with code
  const connectWithCode = async () => {
    if (!inputCode.trim()) {
      Alert.alert('Error', 'Please enter a connection code');
      return;
    }

    try {
      const connected = await secureConnectionManager.connectWithCode('child_demo', inputCode.trim());
      if (connected) {
        setIsConnected(true);
        Alert.alert('Connected!', 'Secure connection established with parent');
      }
    } catch (error) {
      Alert.alert('Connection Failed', error instanceof Error ? error.message : 'Invalid code');
      console.error(error);
    }
  };

  // Share progress with parent (automatically sanitized)
  const shareProgress = async () => {
    try {
      await secureConnectionManager.sendSecureData({
        type: 'progress_update',
        childProgress: progress, // Sensitive data will be automatically sanitized
        timestamp: Date.now()
      }, 'parent');

      Alert.alert('Progress Shared', 'Your progress has been shared securely');
    } catch (error) {
      Alert.alert('Error', 'Failed to share progress');
      console.error(error);
    }
  };

  // Simulate meditation progress
  const updateProgress = () => {
    setProgress(prev => ({
      ...prev,
      currentStep: Math.min(prev.currentStep + 1, 5),
      completionPercentage: Math.min(prev.completionPercentage + 15, 100),
      engagementLevel: Math.min(prev.engagementLevel + 0.1, 1.0),
      lastUpdate: new Date(),
      // These sensitive values change but won't be shared with parent
      heartRate: prev.heartRate + Math.floor(Math.random() * 10 - 5),
      stressLevel: Math.max(0, prev.stressLevel - 0.05)
    }));
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Child Meditation</Text>
      
      {!isConnected ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Connect to Parent</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter connection code"
            value={inputCode}
            onChangeText={setInputCode}
            autoCapitalize="characters"
            maxLength={12}
          />
          <Button title="Connect" onPress={connectWithCode} />
        </View>
      ) : (
        <View>
          <View style={styles.section}>
            <Text style={styles.connectedText}>🔗 Connected to Parent</Text>
            <Text style={styles.statusText}>Your meditation is private and secure</Text>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Meditation Progress</Text>
            <Text style={styles.progressText}>Step: {progress.currentStep}/5</Text>
            <Text style={styles.progressText}>Progress: {progress.completionPercentage}%</Text>
            <Text style={styles.progressText}>Engagement: {Math.round(progress.engagementLevel * 100)}%</Text>
            
            {/* Sensitive data visible to child only */}
            <Text style={styles.privateText}>Heart Rate: {progress.heartRate} bpm (private)</Text>
            <Text style={styles.privateText}>Stress Level: {Math.round(progress.stressLevel * 100)}% (private)</Text>
            
            <View style={styles.buttonContainer}>
              <Button title="Continue Meditation" onPress={updateProgress} />
              <Button title="Share Progress" onPress={shareProgress} />
            </View>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
    color: '#2c3e50',
  },
  section: {
    backgroundColor: 'white',
    padding: 15,
    marginVertical: 10,
    borderRadius: 10,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
    color: '#34495e',
  },
  codeText: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    backgroundColor: '#ecf0f1',
    padding: 15,
    borderRadius: 5,
    marginVertical: 10,
    fontFamily: 'monospace',
  },
  instructions: {
    textAlign: 'center',
    color: '#7f8c8d',
    marginBottom: 10,
  },
  connectedText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#27ae60',
    textAlign: 'center',
    marginBottom: 10,
  },
  statusText: {
    fontSize: 14,
    color: '#7f8c8d',
    marginVertical: 2,
  },
  progressText: {
    fontSize: 16,
    color: '#2c3e50',
    marginVertical: 2,
  },
  privateText: {
    fontSize: 14,
    color: '#e74c3c',
    fontStyle: 'italic',
    marginVertical: 1,
  },
  input: {
    borderWidth: 1,
    borderColor: '#bdc3c7',
    borderRadius: 5,
    padding: 10,
    marginVertical: 10,
    fontSize: 16,
    textAlign: 'center',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 15,
  },
});