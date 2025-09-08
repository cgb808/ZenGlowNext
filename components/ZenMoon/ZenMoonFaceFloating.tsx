/**
 * =================================================================================
 * ZEN MOON FACE FLOATING - Updated to use Secure Global Manager
 * =================================================================================
 * Purpose: Floating Zen Moon avatar with secure global integration
 * Security Update: Replaced insecure global variables with secure token-based system
 * Replaces: global.zenPulse and global.zenSound with useSecureGlobals hook
 * =================================================================================
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, StyleSheet, Animated, Dimensions, PanResponder } from 'react-native';
import { MotiView } from 'moti';
import { EnhancedZenMoonAvatar, MoodType } from './EnhancedZenMoonAvatar';
import { useSecureGlobals } from '../../src/utils/SecureGlobalManager';
import { useTheme } from '../../src/theme';

interface ZenMoonFaceFloatingProps {
  initialMood?: MoodType;
  enableFloating?: boolean;
  enableInteraction?: boolean;
  userId?: string;
}

export const ZenMoonFaceFloating: React.FC<ZenMoonFaceFloatingProps> = ({
  initialMood = 'calm',
  enableFloating = true,
  enableInteraction = true,
  userId,
}) => {
  const [mood, setMood] = useState<MoodType>(initialMood);
  const [isGlowing, setIsGlowing] = useState(false);
  const [showSecurityStatus, setShowSecurityStatus] = useState(false);

  // Secure global management - replaces insecure global variables
  const { 
    setZenPulse, 
    setZenSound, 
    executeZenPulse, 
    executeZenSound, 
    getSecurityStatus,
    isTokenValid 
  } = useSecureGlobals(userId);

  // Animation values
  const position = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;
  const scale = useRef(new Animated.Value(1)).current;
  const opacity = useRef(new Animated.Value(1)).current;

  // Secure pulse glow function
  const pulseGlow = useCallback(() => {
    console.log('🌙 Zen Moon pulse triggered securely');
    setIsGlowing(true);
    
    Animated.sequence([
      Animated.timing(scale, {
        toValue: 1.2,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(scale, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setIsGlowing(false);
    });
  }, [scale]);

  // Secure sound function
  const triggerZenSound = useCallback(async () => {
    console.log('🔊 Zen Sound triggered securely');
    // TODO: Implement actual sound playing
    // This is a placeholder for sound functionality
    
    Animated.timing(opacity, {
      toValue: 0.7,
      duration: 200,
      useNativeDriver: true,
    }).start(() => {
      Animated.timing(opacity, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
    });
  }, [opacity]);

  // Register secure global functions on mount
  useEffect(() => {
    if (isTokenValid) {
      // SECURE: Replace global.zenPulse with secure token-based system
      setZenPulse(pulseGlow);
      setZenSound(triggerZenSound);

      console.log('✅ Secure global functions registered for ZenMoonFaceFloating');
    }

    // Cleanup on unmount - automatically handled by useSecureGlobals hook
    return () => {
      if (isTokenValid) {
        setZenPulse(null);
        setZenSound(null);
        console.log('🧹 Secure global functions unregistered');
      }
    };
  }, [setZenPulse, setZenSound, pulseGlow, triggerZenSound, isTokenValid]);

  // Pan responder for dragging (if interaction enabled)
  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => enableInteraction,
    onMoveShouldSetPanResponder: () => enableInteraction,
    onPanResponderGrant: () => {
      // Show security status on long press
      const timer = setTimeout(() => {
        setShowSecurityStatus(true);
        setTimeout(() => setShowSecurityStatus(false), 3000);
      }, 1000);

      position.setOffset({
        x: (position.x as any)._value,
        y: (position.y as any)._value,
      });
      position.setValue({ x: 0, y: 0 });

      return () => clearTimeout(timer);
    },
    onPanResponderMove: Animated.event(
      [null, { dx: position.x, dy: position.y }],
      { useNativeDriver: false }
    ),
    onPanResponderRelease: () => {
      position.flattenOffset();
      
      // Trigger secure pulse on release
      executeZenPulse();
    },
  });

  // Floating animation
  useEffect(() => {
    if (!enableFloating) return;

    const floatingAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(position, {
          toValue: { x: 0, y: -10 },
          duration: 2000,
          useNativeDriver: false,
        }),
        Animated.timing(position, {
          toValue: { x: 0, y: 10 },
          duration: 2000,
          useNativeDriver: false,
        }),
      ])
    );

    floatingAnimation.start();

    return () => {
      floatingAnimation.stop();
    };
  }, [enableFloating, position]);

  // Handle mood changes
  const handleMoodChange = useCallback((newMood: MoodType) => {
    setMood(newMood);
    executeZenSound(); // Trigger sound on mood change
  }, [executeZenSound]);

  // Double tap to cycle moods
  const handleDoubleTap = useCallback(() => {
    const moods: MoodType[] = ['calm', 'joyful', 'curious', 'focused', 'playful', 'sleepy'];
    const currentIndex = moods.indexOf(mood);
    const nextMood = moods[(currentIndex + 1) % moods.length];
    handleMoodChange(nextMood);
  }, [mood, handleMoodChange]);

  // Security status display
  const securityStatus = getSecurityStatus();

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.floatingContainer,
          {
            transform: [
              ...position.getTranslateTransform(),
              { scale },
            ],
            opacity,
          },
        ]}
        {...panResponder.panHandlers}
      >
        <MotiView
          animate={{
            shadowOpacity: isGlowing ? 0.8 : 0.3,
            shadowRadius: isGlowing ? 20 : 10,
          }}
          transition={{
            type: 'timing',
            duration: 300,
          }}
          style={[
            styles.moonContainer,
            {
              shadowColor: isGlowing ? '#FFD700' : '#4A90E2',
            },
          ]}
        >
          <EnhancedZenMoonAvatar 
            mood={mood} 
            size={80}
          />
        </MotiView>

        {/* Security Status Indicator */}
        {showSecurityStatus && (
          <MotiView
            from={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={styles.securityIndicator}
          >
            <View style={styles.securityStatus}>
              <View style={[
                styles.securityDot, 
                { backgroundColor: isTokenValid ? '#27AE60' : '#E74C3C' }
              ]} />
            </View>
          </MotiView>
        )}
      </Animated.View>

      {/* Debug Info (development only) */}
      {__DEV__ && (
        <View style={styles.debugInfo}>
          <View style={styles.debugText}>
            <View style={styles.debugRow}>
              <View style={[
                styles.statusIndicator,
                { backgroundColor: isTokenValid ? '#27AE60' : '#E74C3C' }
              ]} />
            </View>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 100,
    right: 20,
    zIndex: 1000,
  },
  floatingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  moonContainer: {
    shadowOffset: { width: 0, height: 0 },
    elevation: 10,
  },
  securityIndicator: {
    position: 'absolute',
    top: -5,
    right: -5,
  },
  securityStatus: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  securityDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  debugInfo: {
    position: 'absolute',
    top: 100,
    left: -50,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    padding: 8,
    borderRadius: 4,
    minWidth: 100,
  },
  debugText: {
    alignItems: 'center',
  },
  debugRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 2,
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
  },
});

export default ZenMoonFaceFloating;