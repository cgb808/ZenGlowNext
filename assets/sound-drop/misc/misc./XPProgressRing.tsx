import React from 'react';
import { View, Text } from 'react-native';

/**
 * A gamified progress ring to track child's XP or level.
 * TODO: Implement with react-native-svg and reanimated for animations.
 */
export const XPProgressRing = ({ progress = 0.75 }) => {
  return (
    <View>
      <Text>XP: {Math.round(progress * 100)}%</Text>
      {/* SVG for the ring will go here */}
    </View>
  );
};

export default XPProgressRing;
