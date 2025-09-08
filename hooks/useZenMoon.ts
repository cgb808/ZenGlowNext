import { Audio } from 'expo-av';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Vibration } from 'react-native';
import { Easing } from 'react-native-reanimated';
import type { MovementBounds, Position, PositionUtils } from '../types/zenMoonTypes';

// Minimal props interface aligned with component usage
export interface ZenMoonAvatarProps {
  pulseSize?: any;
  pulseColor?: any;
  animationType?: 'gentle' | 'lively';
  enableParticles?: boolean;
  enableSound?: boolean;
  enableHaptics?: boolean;
  enableInteraction?: boolean;
  meditationProgress?: number;
  breathingRate?: number;
  initialPosition?: Position;
  targetPosition?: Position;
  constrainToBounds?: boolean;
  movementType?: 'free' | 'constrained' | 'guided';
  autoFloat?: boolean;
  snapToGrid?: boolean;
}

// Helper function to get image source
const getImageSource = (_size?: any, _color?: any): any => {
  // ... your existing getImageSource logic
  // Use an existing placeholder image for now
  return require('../assets/images/icon.png');
};

export const useZenMoon = (props: ZenMoonAvatarProps) => {
  const {
    pulseSize,
    pulseColor,
    animationType = 'gentle',
    enableParticles = false,
    enableSound = false,
    enableHaptics = false,
    enableInteraction = false,
    meditationProgress = 0,
    breathingRate = 4,
    // Position and movement props
    initialPosition,
    targetPosition,
    constrainToBounds = false,
    movementType = 'free',
    autoFloat = false,
    snapToGrid = false,
    // ... destructure all other props
  } = props;

  // --- All State and Refs ---
  const [isPressed, setIsPressed] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [breathPhase, setBreathPhase] = useState<'inhale' | 'exhale'>('inhale');
  const [currentPosition, setCurrentPosition] = useState<Position>(
    initialPosition || { x: 0, y: 0 },
  );
  const soundRef = useRef<Audio.Sound | null>(null);
  const pan = useRef(new Animated.ValueXY(initialPosition || { x: 0, y: 0 })).current;
  const floatAnimation = useRef(new Animated.Value(0)).current;

  // --- Memoized Calculations and Custom Hooks ---
  // This is where you call all the smaller hooks you already created
  // const { currentTheme, updateTheme } = useTheme(theme);
  // const baseColors = useColorPalette(pulseColor, currentTheme);
  // const contextualColors = useContextualColors(baseColors, timeOfDay, weather, currentTheme);
  // const particles = useParticleSystem(enableParticles, meditationProgress, season, animationSpeed, currentTheme);
  // const animConfig = useAnimationConfig(animationType, animationSpeed, currentTheme, breathPhase, meditationProgress);

  // For demonstration, let's create simplified versions
  const animConfig = useMemo(
    () => ({
      opacity: [1, 0.8, 1],
      scale: [1, 1.02, 1],
      duration: 4000,
      easing: Easing.inOut(Easing.ease),
    }),
    [],
  );
  const contextualColors = useMemo(
    () => ({ primary: '#FFD700', accent: '#FF69B4', secondary: '#87CEEB' }),
    [],
  );
  const particles = useMemo(() => [], [enableParticles]);
  const source = useMemo(() => getImageSource(pulseSize, pulseColor), [pulseSize, pulseColor]);

  // --- Gesture Handlers ---
  const panResponder = useRef(
    Animated.event([null, { dx: pan.x, dy: pan.y }], { useNativeDriver: false }),
  ).current;

  // --- All useEffect Hooks for side effects ---
  useEffect(() => {
    // Logic for accessibility's 'reduceMotion'
  }, []);

  useEffect(() => {
    // Logic for breathing sync (setInterval)
  }, [breathingRate]);

  // --- Callback Handlers ---
  const handleTap = useCallback(() => {
    if (enableInteraction) {
      setIsPressed(true);
      setTimeout(() => setIsPressed(false), 800);
      if (enableHaptics) Vibration.vibrate(50);
      // onTouch?.();
    }
  }, [enableInteraction, enableHaptics]);

  // --- Position Utilities ---
  const positionUtils: PositionUtils = useMemo(
    () => ({
      moveToPosition: (position: Position, duration = 1000) => {
        Animated.timing(pan, {
          toValue: position,
          duration,
          useNativeDriver: false,
        }).start();
        setCurrentPosition(position);
      },

      animateToPosition: (position: Position, duration = 1000): Promise<void> => {
        return new Promise((resolve) => {
          Animated.timing(pan, {
            toValue: position,
            duration,
            useNativeDriver: false,
          }).start(() => {
            setCurrentPosition(position);
            resolve();
          });
        });
      },

      constrainPosition: (position: Position, bounds: MovementBounds): Position => {
        return {
          x: Math.max(bounds.minX, Math.min(bounds.maxX, position.x)),
          y: Math.max(bounds.minY, Math.min(bounds.maxY, position.y)),
        };
      },

      snapToGrid: (position: Position, gridSize: number): Position => {
        return {
          x: Math.round(position.x / gridSize) * gridSize,
          y: Math.round(position.y / gridSize) * gridSize,
        };
      },

      resetPosition: () => {
        const resetPos = initialPosition || { x: 0, y: 0 };
        positionUtils.moveToPosition(resetPos);
      },
    }),
    [pan, initialPosition],
  );

  // Auto-float animation effect
  useEffect(() => {
    if (autoFloat && !reduceMotion) {
      const floatLoop = Animated.loop(
        Animated.sequence([
          Animated.timing(floatAnimation, {
            toValue: 1,
            duration: 3000,
            useNativeDriver: false,
          }),
          Animated.timing(floatAnimation, {
            toValue: 0,
            duration: 3000,
            useNativeDriver: false,
          }),
        ]),
      );
      floatLoop.start();
      return () => floatLoop.stop();
    }
  }, [autoFloat, reduceMotion, floatAnimation]);

  // Animate to target position when it changes
  useEffect(() => {
    if (targetPosition) {
      positionUtils.animateToPosition(targetPosition);
    }
  }, [targetPosition, positionUtils]);

  // The hook returns an object with everything the UI needs
  return {
    pan,
    panResponder,
    source,
    animConfig,
    contextualColors,
    particles,
    isPressed,
    breathPhase,
    handleTap,
    // Position and movement utilities
    currentPosition,
    positionUtils,
    floatAnimation,
    // Return any other values needed for rendering
  };
};
