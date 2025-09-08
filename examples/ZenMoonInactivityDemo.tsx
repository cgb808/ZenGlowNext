import React, { useRef } from 'react';
import { View, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { EnhancedZenMoonAvatar } from '../components/ZenMoon/EnhancedZenMoonAvatar';
import { ZenSoundProvider } from '../components/Audio/ZenSoundProvider';

/**
 * Test component to demonstrate EnhancedZenMoonAvatar inactivity logic and sparkle effects
 */
export const ZenMoonInactivityDemo: React.FC = () => {
  const buttonRef1 = useRef<View>(null);
  const buttonRef2 = useRef<View>(null);
  const buttonRef3 = useRef<View>(null);
  
  const avatarRef = useRef<{ handleUserInteraction: () => void }>(null);
  
  const handleButtonPress = (buttonName: string) => {
    console.log(`Button pressed: ${buttonName}`);
    // Notify the avatar that user interacted
    if (avatarRef.current) {
      avatarRef.current.handleUserInteraction();
    }
  };

  return (
    <ZenSoundProvider>
      <View style={styles.container}>
        <Text style={styles.title}>ZenMoon Inactivity Demo</Text>
        <Text style={styles.subtitle}>
          Wait 7 seconds without pressing buttons to see the moon suggest one!
        </Text>
        
        {/* The enhanced moon avatar with inactivity detection */}
        <View style={styles.avatarContainer}>
          <EnhancedZenMoonAvatar
            mood="curious"
            size={100}
            suggestedButtonRefs={[buttonRef1, buttonRef2, buttonRef3]}
            sparkleConfig={{
              count: 5,
              color: '#FFD700',
              duration: 1200,
              repeat: true,
            }}
            inactivityConfig={{
              timeout: 7000, // 7 seconds
              enabled: true,
            }}
            onUserInteraction={() => console.log('User interaction detected!')}
          />
        </View>
        
        {/* Test buttons for the moon to suggest */}
        <View style={styles.buttonsContainer}>
          <TouchableOpacity
            ref={buttonRef1}
            style={[styles.button, styles.button1]}
            onPress={() => handleButtonPress('Breathe')}
          >
            <Text style={styles.buttonText}>🫁 Breathe</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            ref={buttonRef2}
            style={[styles.button, styles.button2]}
            onPress={() => handleButtonPress('Meditate')}
          >
            <Text style={styles.buttonText}>🧘 Meditate</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            ref={buttonRef3}
            style={[styles.button, styles.button3]}
            onPress={() => handleButtonPress('Exercise')}
          >
            <Text style={styles.buttonText}>🏃 Exercise</Text>
          </TouchableOpacity>
        </View>
        
        <Text style={styles.instructions}>
          • Moon will fly to suggested button after 7s of inactivity{'\n'}
          • Eyes will look around during suggestion{'\n'}
          • Sparkles will appear around suggested button{'\n'}
          • Press any button to reset the timer{'\n'}
          • Moon will return to center after interaction
        </Text>
      </View>
    </ZenSoundProvider>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 30,
  },
  avatarContainer: {
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 40,
  },
  buttonsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 30,
  },
  button: {
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderRadius: 25,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  button1: {
    backgroundColor: '#4A90E2',
  },
  button2: {
    backgroundColor: '#27AE60',
  },
  button3: {
    backgroundColor: '#E67E22',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  instructions: {
    fontSize: 14,
    color: '#666',
    textAlign: 'left',
    lineHeight: 20,
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.2,
    shadowRadius: 1.41,
    elevation: 2,
  },
});