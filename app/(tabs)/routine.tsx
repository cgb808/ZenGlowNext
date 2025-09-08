import { createMaterialTopTabNavigator } from '@react-navigation/material-top-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import React from 'react';
import RoutineBuilderScreen from '../RoutineBuilderScreen';

const Stack = createStackNavigator();
const Carousel = createMaterialTopTabNavigator();

function RoutineCarousel() {
  return (
    <Carousel.Navigator screenOptions={{ swipeEnabled: true }}>
      <Carousel.Screen
        name="RoutineBuilder"
        component={RoutineBuilderScreen}
        options={{ title: 'Routine Builder' }}
      />
      {/* Add more screens here for carousel/swipe navigation */}
    </Carousel.Navigator>
  );
}

export default function RoutineStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="RoutineCarousel"
        component={RoutineCarousel}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
}
