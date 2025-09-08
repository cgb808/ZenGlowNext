/**
 * =================================================================================
 * DEV FLAGS SCREEN
 * =================================================================================
 * Purpose: Development UI for toggling feature flags at runtime
 * 
 * Features:
 * - Toggle flags in development mode only
 * - Visual indicator of flag states
 * - Reset to defaults functionality
 * - Search and filter capabilities
 * =================================================================================
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Switch,
  TouchableOpacity,
  TextInput,
  Alert,
} from 'react-native';
import { useFeatureFlagDev } from '../hooks/useFeatureFlag';
import { 
  DEFAULT_FEATURE_FLAGS, 
  FeatureFlagName,
  FeatureFlagConfig 
} from '../config/featureFlags';

/**
 * Development Feature Flags Screen
 * Only renders in development mode
 */
export const DevFlagsScreen: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const { setFlag, resetFlag, refreshRemoteConfig, getAllFlags } = useFeatureFlagDev();
  const flags = getAllFlags();

  // Don't render in production
  if (!__DEV__) {
    return null;
  }

  /**
   * Filter flags based on search query
   */
  const filteredFlags = Object.entries(flags).filter(([name]) =>
    name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  /**
   * Handle flag toggle
   */
  const handleToggleFlag = async (name: FeatureFlagName, currentValue: boolean) => {
    try {
      await setFlag(name, !currentValue);
    } catch (error) {
      Alert.alert('Error', `Failed to toggle ${name}: ${error}`);
    }
  };

  /**
   * Handle flag reset
   */
  const handleResetFlag = async (name: FeatureFlagName) => {
    try {
      await resetFlag(name);
    } catch (error) {
      Alert.alert('Error', `Failed to reset ${name}: ${error}`);
    }
  };

  /**
   * Handle reset all flags
   */
  const handleResetAll = () => {
    Alert.alert(
      'Reset All Flags',
      'Are you sure you want to reset all flags to their default values?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset All',
          style: 'destructive',
          onPress: async () => {
            try {
              for (const flagName of Object.keys(DEFAULT_FEATURE_FLAGS) as FeatureFlagName[]) {
                await resetFlag(flagName);
              }
            } catch (error) {
              Alert.alert('Error', `Failed to reset flags: ${error}`);
            }
          },
        },
      ]
    );
  };

  /**
   * Handle refresh remote config
   */
  const handleRefreshRemote = async () => {
    try {
      await refreshRemoteConfig();
      Alert.alert('Success', 'Remote configuration refreshed successfully');
    } catch (error) {
      Alert.alert('Error', `Failed to refresh remote config: ${error}`);
    }
  };

  /**
   * Get flag category based on name
   */
  const getFlagCategory = (name: string): string => {
    if (name.includes('DEBUG') || name.includes('PERFORMANCE')) return 'Development';
    if (name.includes('UI') || name.includes('DASHBOARD') || name.includes('MODE')) return 'UI';
    if (name.includes('AI') || name.includes('VOICE') || name.includes('GESTURE')) return 'Experimental';
    if (name.includes('AUTH') || name.includes('ENCRYPTION')) return 'Security';
    return 'Core';
  };

  /**
   * Get flag status indicator
   */
  const getFlagStatus = (name: FeatureFlagName, currentValue: boolean): string => {
    const defaultValue = DEFAULT_FEATURE_FLAGS[name];
    if (currentValue === defaultValue) return 'default';
    return currentValue ? 'enabled' : 'disabled';
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🚩 Feature Flags (Development)</Text>
        <Text style={styles.subtitle}>Toggle flags at runtime for testing</Text>
      </View>

      {/* Search */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search flags..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholderTextColor="#666"
        />
      </View>

      {/* Actions */}
      <View style={styles.actionsContainer}>
        <TouchableOpacity style={styles.actionButton} onPress={handleResetAll}>
          <Text style={styles.actionButtonText}>Reset All</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton} onPress={handleRefreshRemote}>
          <Text style={styles.actionButtonText}>Refresh Remote</Text>
        </TouchableOpacity>
      </View>

      {/* Flag List */}
      <View style={styles.flagsList}>
        {filteredFlags.map(([name, value]) => {
          const flagName = name as FeatureFlagName;
          const status = getFlagStatus(flagName, value);
          const category = getFlagCategory(name);

          return (
            <View key={name} style={styles.flagItem}>
              <View style={styles.flagInfo}>
                <View style={styles.flagHeader}>
                  <Text style={styles.flagName}>{name}</Text>
                  <Text style={[styles.flagCategory, { color: getCategoryColor(category) }]}>
                    {category}
                  </Text>
                </View>
                <Text style={[styles.flagStatus, { color: getStatusColor(status) }]}>
                  {status === 'default' ? 'Default' : status === 'enabled' ? 'Enabled' : 'Disabled'}
                  {status !== 'default' && ' (Modified)'}
                </Text>
              </View>
              <View style={styles.flagControls}>
                <Switch
                  value={value}
                  onValueChange={() => handleToggleFlag(flagName, value)}
                  trackColor={{ false: '#767577', true: '#81b0ff' }}
                  thumbColor={value ? '#f5dd4b' : '#f4f3f4'}
                />
                <TouchableOpacity
                  style={styles.resetButton}
                  onPress={() => handleResetFlag(flagName)}
                >
                  <Text style={styles.resetButtonText}>↺</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        })}
      </View>

      {filteredFlags.length === 0 && (
        <View style={styles.emptyState}>
          <Text style={styles.emptyStateText}>No flags match your search</Text>
        </View>
      )}
    </ScrollView>
  );
};

/**
 * Get color for flag category
 */
const getCategoryColor = (category: string): string => {
  switch (category) {
    case 'Core': return '#4CAF50';
    case 'UI': return '#2196F3';
    case 'Experimental': return '#FF9800';
    case 'Security': return '#F44336';
    case 'Development': return '#9C27B0';
    default: return '#666';
  }
};

/**
 * Get color for flag status
 */
const getStatusColor = (status: string): string => {
  switch (status) {
    case 'enabled': return '#4CAF50';
    case 'disabled': return '#F44336';
    case 'default': return '#666';
    default: return '#666';
  }
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  searchContainer: {
    padding: 15,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  searchInput: {
    height: 40,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    fontSize: 16,
    color: '#333',
  },
  actionsContainer: {
    flexDirection: 'row',
    padding: 15,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    gap: 10,
  },
  actionButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  flagsList: {
    paddingVertical: 10,
  },
  flagItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    backgroundColor: '#fff',
    marginHorizontal: 15,
    marginVertical: 5,
    borderRadius: 8,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  flagInfo: {
    flex: 1,
  },
  flagHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  flagName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  flagCategory: {
    fontSize: 12,
    fontWeight: '500',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: 'rgba(0,0,0,0.1)',
  },
  flagStatus: {
    fontSize: 12,
    fontWeight: '500',
  },
  flagControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  resetButton: {
    padding: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 4,
  },
  resetButtonText: {
    fontSize: 16,
    color: '#666',
  },
  emptyState: {
    padding: 40,
    alignItems: 'center',
  },
  emptyStateText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
});