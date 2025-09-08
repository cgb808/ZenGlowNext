import React, { useEffect, useCallback } from 'react';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
  withSequence,
  withRepeat,
  interpolate,
  runOnJS,
  Easing,
} from 'react-native-reanimated';
import { ActionType, MoodType } from '../../types/companion';

interface CompanionAnimationsProps {
  children: React.ReactNode;
  currentAction: ActionType;
  mood: MoodType;
  isVisible: boolean;
  isHidden: boolean;
  energy: number; // 0-100
  intensity?: number; // 0-1
  onAnimationComplete?: () => void;
}

export const CompanionAnimations: React.FC<CompanionAnimationsProps> = ({
  children,
  currentAction,
  mood,
  isVisible,
  isHidden,
  energy,
  intensity = 0.7,
  onAnimationComplete,
}) => {
  // Animation values
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);
  const translateY = useSharedValue(0);
  const rotation = useSharedValue(0);
  const scaleX = useSharedValue(1);
  const scaleY = useSharedValue(1);

  // Floating animation for idle state
  const floatingOffset = useSharedValue(0);
  
  useEffect(() => {
    // Continuous floating animation based on energy level
    const floatingIntensity = (energy / 100) * 8; // 0-8 pixels
    floatingOffset.value = withRepeat(
      withTiming(floatingIntensity, {
        duration: 2000 + (1 - energy / 100) * 1000, // Slower when less energetic
        easing: Easing.inOut(Easing.sin),
      }),
      -1,
      true
    );
  }, [energy, floatingOffset]);

  // Handle visibility changes
  useEffect(() => {
    if (isHidden) {
      opacity.value = withTiming(0.2, { duration: 300 });
      scale.value = withTiming(0.6, { duration: 300 });
    } else if (isVisible) {
      opacity.value = withTiming(1, { duration: 400 });
      scale.value = withTiming(1, { duration: 400 });
    }
  }, [isVisible, isHidden, opacity, scale]);

  // Animation complete callback
  const handleAnimationComplete = useCallback(() => {
    if (onAnimationComplete) {
      onAnimationComplete();
    }
  }, [onAnimationComplete]);

  // Handle action-based animations
  useEffect(() => {
    const animationIntensity = intensity * (energy / 100);
    
    switch (currentAction) {
      case 'celebrate':
        // Celebration animation
        scale.value = withSequence(
          withTiming(1 + animationIntensity * 0.3, { duration: 200 }),
          withTiming(1, { duration: 200 })
        );
        rotation.value = withSequence(
          withTiming(-15 * animationIntensity, { duration: 100 }),
          withTiming(15 * animationIntensity, { duration: 200 }),
          withTiming(0, { duration: 150 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 550);
        break;

      case 'wave':
        // Wave animation
        scaleX.value = withSequence(
          withTiming(1 + animationIntensity * 0.1, { duration: 150 }),
          withTiming(1 - animationIntensity * 0.05, { duration: 150 }),
          withTiming(1, { duration: 150 })
        );
        rotation.value = withSequence(
          withTiming(20 * animationIntensity, { duration: 200 }),
          withTiming(-10 * animationIntensity, { duration: 200 }),
          withTiming(0, { duration: 150 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 550);
        break;

      case 'nod':
        // Nod animation
        scaleY.value = withSequence(
          withTiming(1 + animationIntensity * 0.1, { duration: 200 }),
          withTiming(1 - animationIntensity * 0.05, { duration: 200 }),
          withTiming(1, { duration: 150 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 550);
        break;

      case 'point':
        // Point animation
        scale.value = withSequence(
          withTiming(1 + animationIntensity * 0.2, { duration: 300 }),
          withTiming(1, { duration: 300 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 600);
        break;

      case 'nudge':
        // Nudge animation
        translateY.value = withSequence(
          withTiming(-5 * animationIntensity, { duration: 100 }),
          withTiming(5 * animationIntensity, { duration: 200 }),
          withTiming(0, { duration: 100 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 400);
        break;

      case 'awaken':
        // Awaken animation
        opacity.value = withSequence(
          withTiming(0.3, { duration: 200 }),
          withTiming(1, { duration: 400 })
        );
        scale.value = withSequence(
          withTiming(0.7, { duration: 200 }),
          withTiming(1 + animationIntensity * 0.4, { duration: 300 }),
          withTiming(1, { duration: 300 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 800);
        break;

      case 'hide':
        // Hide animation
        opacity.value = withTiming(0.2, { duration: 300 });
        scale.value = withTiming(0.6, { duration: 300 });
        setTimeout(() => runOnJS(handleAnimationComplete)(), 300);
        break;

      case 'lookAt':
        // Look at animation
        scale.value = withSequence(
          withTiming(1 + animationIntensity * 0.1, { duration: 200 }),
          withTiming(1, { duration: 300 })
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 500);
        break;

      case 'speak':
        // Speak animation - pulsing
        scale.value = withRepeat(
          withSequence(
            withTiming(1 + animationIntensity * 0.08, { duration: 300 }),
            withTiming(1, { duration: 300 })
          ),
          3,
          false
        );
        setTimeout(() => runOnJS(handleAnimationComplete)(), 1800);
        break;

      default:
        // Reset to idle
        scale.value = withSpring(1, { damping: 15 });
        rotation.value = withSpring(0, { damping: 15 });
        scaleX.value = withSpring(1, { damping: 15 });
        scaleY.value = withSpring(1, { damping: 15 });
        translateY.value = withSpring(0, { damping: 15 });
    }
  }, [currentAction, intensity, energy, scale, rotation, scaleX, scaleY, translateY, opacity, handleAnimationComplete]);

  // Handle mood-based continuous animations
  useEffect(() => {
    const energyFactor = energy / 100;
    
    switch (mood) {
      case 'excited':
        floatingOffset.value = withRepeat(
          withTiming(12 * energyFactor, {
            duration: 1500,
            easing: Easing.inOut(Easing.sin),
          }),
          -1,
          true
        );
        break;
        
      case 'calm':
        floatingOffset.value = withRepeat(
          withTiming(4 * energyFactor, {
            duration: 3000,
            easing: Easing.inOut(Easing.sin),
          }),
          -1,
          true
        );
        break;
        
      case 'sleepy':
        floatingOffset.value = withRepeat(
          withTiming(2 * energyFactor, {
            duration: 4000,
            easing: Easing.inOut(Easing.sin),
          }),
          -1,
          true
        );
        break;
        
      case 'playful':
        floatingOffset.value = withRepeat(
          withSequence(
            withTiming(8 * energyFactor, { duration: 800 }),
            withTiming(2 * energyFactor, { duration: 400 }),
            withTiming(10 * energyFactor, { duration: 600 })
          ),
          -1,
          true
        );
        break;
        
      default:
        floatingOffset.value = withRepeat(
          withTiming(6 * energyFactor, {
            duration: 2500,
            easing: Easing.inOut(Easing.sin),
          }),
          -1,
          true
        );
    }
  }, [mood, energy, floatingOffset]);

  // Combine all animations
  const animatedStyle = useAnimatedStyle(() => {
    const floatingY = interpolate(
      floatingOffset.value,
      [0, 1],
      [0, -1],
      'clamp'
    ) * floatingOffset.value;

    return {
      opacity: opacity.value,
      transform: [
        { scale: scale.value },
        { scaleX: scaleX.value },
        { scaleY: scaleY.value },
        { translateY: translateY.value + floatingY },
        { rotate: `${rotation.value}deg` },
      ],
    };
  });

  return (
    <Animated.View style={animatedStyle}>
      {children}
    </Animated.View>
  );
};