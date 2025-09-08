import React, { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, { 
  useSharedValue, 
  useAnimatedStyle, 
  withRepeat, 
  withSequence, 
  withTiming, 
  withSpring,
  Easing 
} from 'react-native-reanimated';
import Svg, { Path } from 'react-native-svg';

export interface SparkleProps {
  /** Color of the sparkle star */
  color?: string;
  /** Size of the sparkle */
  size?: number;
  /** Animation duration in milliseconds */
  duration?: number;
  /** Delay before animation starts */
  delay?: number;
  /** Whether to repeat the animation */
  repeat?: boolean;
  /** Position offset from center */
  offsetX?: number;
  offsetY?: number;
}

export const Sparkle: React.FC<SparkleProps> = ({
  color = '#FFD700',
  size = 12,
  duration = 1000,
  delay = 0,
  repeat = true,
  offsetX = 0,
  offsetY = 0,
}) => {
  const opacity = useSharedValue(0);
  const scale = useSharedValue(0);
  const rotation = useSharedValue(0);

  useEffect(() => {
    const startAnimation = () => {
      if (repeat) {
        opacity.value = withRepeat(
          withSequence(
            withTiming(0, { duration: delay }),
            withTiming(1, { duration: duration * 0.3, easing: Easing.out(Easing.ease) }),
            withTiming(0.7, { duration: duration * 0.4 }),
            withTiming(0, { duration: duration * 0.3, easing: Easing.in(Easing.ease) })
          ),
          -1,
          false
        );
        
        scale.value = withRepeat(
          withSequence(
            withTiming(0, { duration: delay }),
            withSpring(1.2, { damping: 8, stiffness: 100 }),
            withTiming(0.8, { duration: duration * 0.4 }),
            withTiming(0, { duration: duration * 0.2 })
          ),
          -1,
          false
        );
        
        rotation.value = withRepeat(
          withTiming(360, { duration: duration * 2, easing: Easing.linear }),
          -1,
          false
        );
      } else {
        // Single animation
        opacity.value = withSequence(
          withTiming(0, { duration: delay }),
          withTiming(1, { duration: duration * 0.3, easing: Easing.out(Easing.ease) }),
          withTiming(0, { duration: duration * 0.7, easing: Easing.in(Easing.ease) })
        );
        
        scale.value = withSequence(
          withTiming(0, { duration: delay }),
          withSpring(1.2, { damping: 8, stiffness: 100 }),
          withTiming(0, { duration: duration * 0.5 })
        );
        
        rotation.value = withTiming(180, { duration: duration, easing: Easing.out(Easing.ease) });
      }
    };

    startAnimation();
  }, [duration, delay, repeat]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [
      { translateX: offsetX },
      { translateY: offsetY },
      { scale: scale.value },
      { rotate: `${rotation.value}deg` }
    ],
  }));

  // Star path for SVG
  const starPath = `M ${size/2} 0 L ${size*0.6} ${size*0.4} L ${size} ${size*0.4} L ${size*0.7} ${size*0.65} L ${size*0.8} ${size} L ${size/2} ${size*0.8} L ${size*0.2} ${size} L ${size*0.3} ${size*0.65} L 0 ${size*0.4} L ${size*0.4} ${size*0.4} Z`;

  return (
    <Animated.View style={[styles.sparkle, { width: size, height: size }, animatedStyle]}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <Path
          d={starPath}
          fill={color}
          stroke={color}
          strokeWidth={0.5}
        />
      </Svg>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  sparkle: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
});