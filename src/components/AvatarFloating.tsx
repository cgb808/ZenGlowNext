import React from 'react';
import { Animated } from 'react-native';
import { useAvatarPosition } from '../hooks/useAvatarPosition';

/**
 * A component that renders an avatar that follows the user's touch.
 * TODO: Implement touch-following animated avatar using PanResponder or react-native-gesture-handler.
 */
export const AvatarFloating = () => {
  const { animatedStyle } = useAvatarPosition();

  return (
    <Animated.View style={animatedStyle}>{/* Avatar image or component goes here */}</Animated.View>
  );
};

export default AvatarFloating;
