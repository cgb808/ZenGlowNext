import React from 'react';
import { View, Text, SafeAreaView, StyleSheet } from 'react-native';
import ChildCardStack from './ChildCardStack';

/**
 * The main screen for the Parent Dashboard.
 * TODO: Fetch real data and implement the full layout with all views.
 */
export const DashboardScreen = () => {
  return (
    <SafeAreaView style={styles.container}>
      <Text>Parent Dashboard</Text>
      <ChildCardStack />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({ container: { flex: 1 } });

export default DashboardScreen;
