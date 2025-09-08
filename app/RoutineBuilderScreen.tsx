import React from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import RoutineBuilder from '../components/RoutineBuilder';

export default function RoutineBuilderScreen() {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <RoutineBuilder />
    </SafeAreaView>
  );
}
