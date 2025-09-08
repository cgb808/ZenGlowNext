import React from 'react';
import { View, Animated } from 'react-native';
import { useMoodColor } from '../hooks/useMoodColor';

/**
 * An overlay that changes color and animates based on the current mood.
 * TODO: Implement color and animation based on mood.
 */
export const MoodOverlay = () => {
  // Example usage of the mood color hook
  const { animatedColor } = useMoodColor('calm');

  return (
    <Animated.View
      style={[
        {
          backgroundColor: animatedColor,
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
        },
      ]}
    />
  );
};

export default MoodOverlay;
