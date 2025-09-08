import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function RoutineBuilder() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Routine Builder</Text>
      <Text style={styles.subtitle}>Create and track daily routines.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 10 },
  subtitle: { fontSize: 16 },
});
