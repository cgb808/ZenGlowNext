// src/components/wearables/WearableStatus.tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useWearableData } from '../../hooks/useWearableData';

const WearableStatus = () => {
  const { isConnected, wearableData } = useWearableData();

  return (
    <View style={styles.container}>
      <Text style={styles.status}>
        Wearable Status: {isConnected ? 'Connected' : 'Disconnected'}
      </Text>
      {isConnected && (
        <View>
          <Text>Heart Rate: {wearableData.heartRate ?? 'N/A'} bpm</Text>
          <Text>Steps: {wearableData.steps ?? 'N/A'}</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
  },
  status: {
    fontWeight: 'bold',
  },
});

export default WearableStatus;
