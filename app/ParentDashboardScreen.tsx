import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
// Import components from the proper locations
import { Collapsible } from '../components/Collapsible';
import { Eye, Mouth, Cheek } from '../components/ZenMoon/FaceComponents';
import ParallaxScrollView from '../components/ParallaxScrollView';
import { ZenMoonAvatar } from '../components/ZenMoon/ZenMoonAvatar';
// Add more imports as needed

const ParentDashboardScreen = () => {
  return (
    <ParallaxScrollView 
      headerImage={<View style={{ height: 100 }} />}
      headerBackgroundColor={{ dark: '#000', light: '#fff' }}
    >
      <Text style={styles.header}>Parent Dashboard</Text>
      <View style={styles.section}>
        {/* Example: ZenMoonAvatar and FaceComponents for mood ring/avatar */}
        <ZenMoonAvatar mood="calm" />
        <Eye />
        <Mouth />
        <Cheek />
      </View>
      <View style={styles.section}>
        {/* Collapsible for daily/weekly/trends views */}
        <Collapsible title="Daily/Weekly/Trends Views">
          <Text>Trend data goes here...</Text>
        </Collapsible>
      </View>
      <View style={styles.section}>
        <Text>Notifications (coming soon)</Text>
      </View>
      <View style={styles.section}>
        <Text>Manual Mood Check-In (coming soon)</Text>
      </View>
    </ParallaxScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  header: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  section: {
    marginBottom: 24,
    padding: 12,
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
  },
});

export default ParentDashboardScreen;
