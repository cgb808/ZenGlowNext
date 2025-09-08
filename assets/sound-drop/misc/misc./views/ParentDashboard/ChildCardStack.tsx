import React from 'react';
import { View, Text } from 'react-native';
// TODO: Import a deck swiper library or use gesture-handler
import Card3D from '../../components/Card3D';

/**
 * A swipeable stack of cards, one for each child.
 * TODO: Implement swipeable stack of child cards using a library like react-native-deck-swiper
 * or building a custom one with react-native-gesture-handler.
 */
export const ChildCardStack = () => {
  // Placeholder data
  const children = [{ id: '1', name: 'Alex' }];

  return (
    <View>
      {/* This should be replaced with a swiper component */}
      {children.map((child) => (
        <Card3D key={child.id}>
          <Text>{child.name}</Text>
        </Card3D>
      ))}
    </View>
  );
};

export default ChildCardStack;
