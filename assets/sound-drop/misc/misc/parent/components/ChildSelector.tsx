/**
 * =================================================================================
 * CHILD SELECTOR COMPONENT - React Native Component
 * =================================================================================
 * Purpose: Child selection interface for Parent Dashboard
 * Dependencies: parentDashboard types, emotional system
 * Used By: ParentDashboardContainer
 * Backend: Supabase-ready child data
 * Integration: React Native, emotional state awareness
 *
 * Key Features:
 * - Visual child selector with avatars
 * - Emotional state indicators per child
 * - Age-appropriate visual design
 * - Accessibility support
 *
 * Design Philosophy:
 * - Clear visual hierarchy
 * - Emotional awareness integration
 * - Neurodivergent-friendly interface
 * =================================================================================
 */

import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Child, EmotionalChildState } from '../../../types/parentDashboard';

interface ChildSelectorProps {
  children: Child[];
  selectedChild: string;
  emotionalStates: { [childName: string]: EmotionalChildState };
  onChildSelect: (childName: string) => void;
}

export const ChildSelector: React.FC<ChildSelectorProps> = ({
  children,
  selectedChild,
  emotionalStates,
  onChildSelect,
}) => {
  const getEmotionalColor = (childName: string): string => {
    const state = emotionalStates[childName];
    if (!state) return '#E8F4FD'; // Default calm blue

    // Map emotions to colors based on ZenGlow color psychology
    const emotionColors = {
      calm: '#E8F4FD', // Gentle blue
      happy: '#FFF4E6', // Warm yellow
      curious: '#F0E6FF', // Soft purple
      loved: '#FFE6F0', // Gentle pink
      overwhelmed: '#FFE6E6', // Soft red
      neutral: '#F5F5F5', // Light gray
      sleepy: '#E6F3E6', // Soft green
    };

    return emotionColors[state.currentEmotion] || emotionColors.neutral;
  };

  const getEmotionalBorder = (childName: string): string => {
    const state = emotionalStates[childName];
    if (!state) return '#B3D9F2';

    const emotionBorders = {
      calm: '#B3D9F2',
      happy: '#F2D9B3',
      curious: '#D9B3F2',
      loved: '#F2B3D9',
      overwhelmed: '#F2B3B3',
      neutral: '#D0D0D0',
      sleepy: '#B3F2B3',
    };

    return emotionBorders[state.currentEmotion] || emotionBorders.neutral;
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Select Child</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
      >
        {children.map((child) => {
          const isSelected = child.name === selectedChild;
          const backgroundColor = getEmotionalColor(child.name);
          const borderColor = getEmotionalBorder(child.name);

          return (
            <TouchableOpacity
              key={child.id}
              style={[
                styles.childCard,
                {
                  backgroundColor,
                  borderColor: isSelected ? borderColor : 'transparent',
                  borderWidth: isSelected ? 3 : 1,
                },
              ]}
              onPress={() => onChildSelect(child.name)}
              accessibilityLabel={`Select ${child.name}, age ${child.age}`}
              accessibilityRole="button"
            >
              <View style={styles.avatarContainer}>
                <Text style={styles.avatar}>{child.avatar}</Text>
              </View>

              <Text style={[styles.childName, { fontWeight: isSelected ? 'bold' : 'normal' }]}>
                {child.name}
              </Text>

              <Text style={styles.childAge}>Age {child.age}</Text>

              {emotionalStates[child.name] && (
                <View style={[styles.emotionalIndicator, { backgroundColor: borderColor }]}>
                  <Text style={styles.emotionalText}>
                    {emotionalStates[child.name].currentEmotion}
                  </Text>
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingVertical: 16,
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 12,
  },
  scrollView: {
    flexGrow: 0,
  },
  scrollContent: {
    paddingRight: 20,
  },
  childCard: {
    padding: 16,
    borderRadius: 12,
    marginRight: 12,
    minWidth: 120,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  avatarContainer: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  avatar: {
    fontSize: 24,
  },
  childName: {
    fontSize: 16,
    color: '#2C3E50',
    textAlign: 'center',
    marginBottom: 4,
  },
  childAge: {
    fontSize: 12,
    color: '#7F8C8D',
    textAlign: 'center',
    marginBottom: 8,
  },
  emotionalIndicator: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    minWidth: 60,
  },
  emotionalText: {
    fontSize: 10,
    color: '#2C3E50',
    textAlign: 'center',
    fontWeight: '500',
  },
});

export default ChildSelector;
