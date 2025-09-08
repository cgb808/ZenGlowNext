import React from 'react';
import { View, Text } from 'react-native';

/**
 * A 3D interactive card component.
 * TODO: Implement 3D interactive card using react-native-reanimated.
 */
export const Card3D = ({ children }) => {
  return (
    <View>
      <Text>3D Card</Text>
      {children}
    </View>
  );
};

export default Card3D;
