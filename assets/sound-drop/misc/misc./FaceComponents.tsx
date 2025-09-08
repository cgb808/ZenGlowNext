// FaceComponents.tsx - Enhanced for child engagement
import React, { useEffect, useRef } from 'react';
import { Animated, Easing } from 'react-native';
import { EyeProps, MouthProps, CheekProps } from '../types/zenMoonTypes';

// Animated Eye Component with personality
export const Eye: React.FC<EyeProps> = ({
  expressionStyle = {},
  isBlinking = true,
  blinkFrequency = 20,
  isAnimating = true,
  animationDuration = 300,
}) => {
  const blinkAnim = useRef(new Animated.Value(1)).current;
  const sparkleAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!isBlinking) return;

    const blink = () => {
      Animated.sequence([
        Animated.timing(blinkAnim, {
          toValue: 0.1,
          duration: animationDuration * 0.3,
          easing: Easing.out(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(blinkAnim, {
          toValue: 1,
          duration: animationDuration * 0.7,
          easing: Easing.out(Easing.ease),
          useNativeDriver: true,
        }),
      ]).start();
    };

    // Occasional sparkle effect for joyful expressions
    const sparkle = () => {
      Animated.sequence([
        Animated.timing(sparkleAnim, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(sparkleAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    };

    const blinkInterval = setInterval(
      () => {
        if (Math.random() < 0.3) blink();
        if (Math.random() < 0.05) sparkle(); // Rare sparkle
      },
      (60 / blinkFrequency) * 1000,
    );

    return () => clearInterval(blinkInterval);
  }, [isBlinking, blinkFrequency, animationDuration]);

  return (
    <>
      <Animated.View
        style={[
          {
            width: 10,
            height: 10,
            borderRadius: 5,
            backgroundColor: '#333',
            opacity: 0.9,
            transform: [{ scaleY: blinkAnim }],
          },
          expressionStyle,
        ]}
      />
      {/* Sparkle overlay */}
      <Animated.View
        style={[
          {
            position: 'absolute',
            top: -2,
            left: -2,
            width: 14,
            height: 14,
            borderRadius: 7,
            backgroundColor: '#FFD700',
            opacity: sparkleAnim,
            transform: [{ scale: sparkleAnim }],
          },
        ]}
      />
    </>
  );
};

// Animated Mouth Component
export const Mouth: React.FC<MouthProps> = ({
  expressionStyle = {},
  isSpeaking = false,
  emotion = 'neutral',
  isAnimating = true,
}) => {
  const speakAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!isSpeaking) {
      speakAnim.setValue(1);
      return;
    }

    // Speaking animation - gentle mouth movement
    const speak = () => {
      Animated.loop(
        Animated.sequence([
          Animated.timing(speakAnim, {
            toValue: 1.2,
            duration: 200,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(speakAnim, {
            toValue: 0.8,
            duration: 300,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(speakAnim, {
            toValue: 1,
            duration: 200,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ]),
      ).start();
    };

    speak();
  }, [isSpeaking]);

  // Different mouth shapes based on emotion
  const getMouthStyle = () => {
    switch (emotion) {
      case 'happy':
      case 'joyful':
        return {
          borderBottomColor: '#222',
          borderBottomWidth: 3,
          borderRadius: 18,
          width: 36,
          height: 18,
        };
      case 'focused':
        return {
          borderBottomColor: '#005577',
          borderBottomWidth: 2,
          borderRadius: 12,
          width: 28,
          height: 14,
        };
      case 'sleepy':
        return {
          borderBottomColor: '#666',
          borderBottomWidth: 1,
          borderRadius: 10,
          width: 20,
          height: 10,
        };
      default:
        return {
          borderBottomColor: '#333',
          borderBottomWidth: 2,
          borderRadius: 15,
          width: 30,
          height: 15,
        };
    }
  };

  return (
    <Animated.View
      style={[
        {
          position: 'absolute',
          bottom: 18,
          left: 42,
          transform: [{ scale: speakAnim }],
        },
        getMouthStyle(),
        expressionStyle,
      ]}
    />
  );
};

// Animated Cheek Component - Child-friendly with gentle glow
export const Cheek: React.FC<CheekProps> = ({
  expressionStyle = {},
  glowIntensity = 0.7,
  isAnimating = true,
}) => {
  const glowAnim = useRef(new Animated.Value(glowIntensity)).current;

  useEffect(() => {
    if (!isAnimating) return;

    const glow = () => {
      Animated.sequence([
        Animated.timing(glowAnim, {
          toValue: glowIntensity * 0.8,
          duration: 2000,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }),
        Animated.timing(glowAnim, {
          toValue: glowIntensity,
          duration: 2000,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: false,
        }),
      ]).start(() => glow()); // Loop forever
    };

    glow();
  }, [isAnimating, glowIntensity]);

  return (
    <Animated.View
      style={[
        {
          width: 18,
          height: 10,
          borderRadius: 9,
          backgroundColor: '#FFD1DC',
          opacity: glowAnim,
          marginHorizontal: 2,
        },
        expressionStyle,
      ]}
    />
  );
};

// Helper component for particle effects around the moon
export const MoonParticle: React.FC<{ delay?: number; color?: string }> = ({
  delay = 0,
  color = '#FFD700',
}) => {
  const particleAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animate = () => {
      Animated.sequence([
        Animated.delay(delay),
        Animated.parallel([
          Animated.timing(particleAnim, {
            toValue: 1,
            duration: 3000,
            easing: Easing.out(Easing.ease),
            useNativeDriver: true,
          }),
        ]),
      ]).start(() => {
        particleAnim.setValue(0);
        animate(); // Loop
      });
    };

    animate();
  }, [delay]);

  const translateY = particleAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [-20, 20],
  });

  const opacity = particleAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 1, 0],
  });

  const scale = particleAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0.5, 1, 0.5],
  });

  return (
    <Animated.View
      style={{
        position: 'absolute',
        width: 4,
        height: 4,
        borderRadius: 2,
        backgroundColor: color,
        opacity,
        transform: [{ translateY }, { translateX: Math.random() * 40 - 20 }, { scale }],
      }}
    />
  );
};
