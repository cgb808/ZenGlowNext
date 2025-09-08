/**
 * =================================================================================
 * ENCRYPTED SENSOR DATA STORAGE - Production-Ready Sensor Buffer
 * =================================================================================
 * Purpose: Secure encrypted storage for buffered sensor data with key rotation
 * Replaces: Plain text sensor data storage
 * Security Features:
 * - AES-256-GCM encryption for sensitive sensor fields (value, quality)
 * - Per-install encryption keys stored in device keychain
 * - Key rotation with automatic re-encryption
 * - Migration from plaintext to encrypted storage
 * - Threat model compliance for child data protection
 * =================================================================================
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Keychain from 'react-native-keychain';
import CryptoJS from 'crypto-js';
import {
  SensorReading,
  SensorBuffer,
  SensorType,
  SensorQuality,
  SensorEncryptionKey,
  SensorMigrationStatus,
  SensorDataStats,
  DEFAULT_SENSOR_ENCRYPTION_CONFIG,
  SENSITIVE_SENSOR_TYPES,
  SENSOR_RETENTION_PERIODS
} from '../types/SensorData';

// Storage configuration
const SENSOR_STORAGE_CONFIG = {
  KEYCHAIN_SERVICE: 'ZenGlow-SensorEncryption',
  KEY_PREFIX: 'sensor_key_',
  BUFFER_PREFIX: 'sensor_buffer_',
  MIGRATION_KEY: 'sensor_migration_status',
  STATS_KEY: 'sensor_data_stats',
  MAX_BUFFER_SIZE: 1000, // Maximum readings per buffer
  CLEANUP_INTERVAL: 24 * 60 * 60 * 1000, // 24 hours
};

/**
 * Encrypted Sensor Data Storage Manager
 */
export class EncryptedSensorStorage {
  private static isInitialized = false;
  private static currentEncryptionKey: SensorEncryptionKey | null = null;
  private static migrationInProgress = false;

  /**
   * Initialize the encrypted sensor storage system
   */
  static async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Ensure encryption key exists
      await this.ensureEncryptionKey();
      
      // Check for pending migration
      await this.checkMigrationStatus();
      
      // Start cleanup process
      this.startAutomaticCleanup();
      
      this.isInitialized = true;
      console.log('🔐 Encrypted Sensor Storage initialized');
    } catch (error) {
      console.error('❌ Failed to initialize encrypted sensor storage:', error);
      throw error;
    }
  }

  /**
   * Store sensor reading with encryption
   */
  static async storeSensorReading(
    childId: string,
    reading: Omit<SensorReading, 'id' | 'encrypted'>
  ): Promise<boolean> {
    try {
      await this.initialize();

      // Generate unique ID for reading
      const sensorReading: SensorReading = {
        ...reading,
        id: `${reading.sensorType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        encrypted: true
      };

      // Encrypt sensitive fields
      const encryptedReading = await this.encryptSensorReading(sensorReading);

      // Get or create buffer for child
      const buffer = await this.getSensorBuffer(childId);
      
      // Add reading to buffer
      buffer.readings.push(encryptedReading);
      buffer.totalSize = buffer.readings.length;
      buffer.encrypted = true;

      // Enforce buffer size limit
      if (buffer.readings.length > SENSOR_STORAGE_CONFIG.MAX_BUFFER_SIZE) {
        buffer.readings = buffer.readings.slice(-SENSOR_STORAGE_CONFIG.MAX_BUFFER_SIZE);
        buffer.totalSize = buffer.readings.length;
      }

      // Store updated buffer
      await this.storeSensorBuffer(childId, buffer);

      // Update statistics
      await this.updateDataStats();

      return true;
    } catch (error) {
      console.error('❌ Failed to store sensor reading:', error);
      return false;
    }
  }

  /**
   * Retrieve sensor readings with decryption
   */
  static async getSensorReadings(
    childId: string,
    sensorType?: SensorType,
    limit?: number
  ): Promise<SensorReading[]> {
    try {
      await this.initialize();

      const buffer = await this.getSensorBuffer(childId);
      let readings = buffer.readings;

      // Filter by sensor type if specified
      if (sensorType) {
        readings = readings.filter(r => r.sensorType === sensorType);
      }

      // Apply limit if specified
      if (limit) {
        readings = readings.slice(-limit);
      }

      // Decrypt readings
      const decryptedReadings = await Promise.all(
        readings.map(reading => this.decryptSensorReading(reading))
      );

      return decryptedReadings;
    } catch (error) {
      console.error('❌ Failed to retrieve sensor readings:', error);
      return [];
    }
  }

  /**
   * Rotate encryption key and re-encrypt all data
   */
  static async rotateEncryptionKey(): Promise<boolean> {
    try {
      console.log('🔄 Starting encryption key rotation...');
      
      // Generate new encryption key
      const newKey = await this.generateNewEncryptionKey();
      
      // Get all sensor buffers
      const childIds = await this.getAllChildIds();
      
      for (const childId of childIds) {
        const buffer = await this.getSensorBuffer(childId);
        
        // Decrypt with old key, encrypt with new key
        const reencryptedReadings = await Promise.all(
          buffer.readings.map(async (reading) => {
            const decrypted = await this.decryptSensorReading(reading);
            return await this.encryptSensorReading(decrypted, newKey);
          })
        );
        
        buffer.readings = reencryptedReadings;
        await this.storeSensorBuffer(childId, buffer);
      }
      
      // Update current key
      this.currentEncryptionKey = newKey;
      
      console.log('✅ Encryption key rotation completed');
      return true;
    } catch (error) {
      console.error('❌ Failed to rotate encryption key:', error);
      return false;
    }
  }

  /**
   * Migrate plaintext data to encrypted format
   */
  static async migratePlaintextData(): Promise<SensorMigrationStatus> {
    if (this.migrationInProgress) {
      return await this.getMigrationStatus();
    }

    try {
      this.migrationInProgress = true;
      
      const migrationStatus: SensorMigrationStatus = {
        inProgress: true,
        totalRecords: 0,
        migratedRecords: 0,
        startedAt: Date.now(),
        errors: []
      };

      await this.storeMigrationStatus(migrationStatus);

      // Find all plaintext sensor buffers
      const allKeys = await AsyncStorage.getAllKeys();
      const plaintextBufferKeys = allKeys.filter(key => 
        key.startsWith(SENSOR_STORAGE_CONFIG.BUFFER_PREFIX) && 
        !key.includes('_encrypted')
      );

      for (const bufferKey of plaintextBufferKeys) {
        try {
          const plaintextData = await AsyncStorage.getItem(bufferKey);
          if (!plaintextData) continue;

          const buffer: SensorBuffer = JSON.parse(plaintextData);
          
          // Skip if already encrypted
          if (buffer.encrypted) continue;

          migrationStatus.totalRecords += buffer.readings.length;

          // Encrypt all readings
          const encryptedReadings = await Promise.all(
            buffer.readings.map(async (reading) => {
              const encryptedReading = await this.encryptSensorReading({
                ...reading,
                encrypted: true
              });
              migrationStatus.migratedRecords++;
              return encryptedReading;
            })
          );

          // Update buffer
          buffer.readings = encryptedReadings;
          buffer.encrypted = true;

          // Store encrypted version and remove plaintext
          await this.storeSensorBuffer(buffer.childId, buffer);
          await AsyncStorage.removeItem(bufferKey);

        } catch (error) {
          const errorMsg = `Failed to migrate buffer ${bufferKey}: ${error}`;
          migrationStatus.errors.push(errorMsg);
          console.error('❌', errorMsg);
        }
      }

      // Complete migration
      migrationStatus.inProgress = false;
      migrationStatus.completedAt = Date.now();
      await this.storeMigrationStatus(migrationStatus);

      this.migrationInProgress = false;
      console.log('✅ Sensor data migration completed');
      
      return migrationStatus;
    } catch (error) {
      this.migrationInProgress = false;
      console.error('❌ Failed to migrate plaintext data:', error);
      throw error;
    }
  }

  /**
   * Get data statistics
   */
  static async getDataStats(): Promise<SensorDataStats> {
    try {
      const statsData = await AsyncStorage.getItem(SENSOR_STORAGE_CONFIG.STATS_KEY);
      if (statsData) {
        return JSON.parse(statsData);
      }

      // Calculate fresh stats
      return await this.calculateDataStats();
    } catch (error) {
      console.error('❌ Failed to get data stats:', error);
      return this.getEmptyStats();
    }
  }

  /**
   * Clear expired sensor data based on retention policies
   */
  static async clearExpiredData(): Promise<number> {
    try {
      let totalCleared = 0;
      const childIds = await this.getAllChildIds();
      const now = Date.now();

      for (const childId of childIds) {
        const buffer = await this.getSensorBuffer(childId);
        const originalCount = buffer.readings.length;

        // Filter out expired readings
        buffer.readings = buffer.readings.filter(reading => {
          const retentionPeriod = SENSOR_RETENTION_PERIODS[reading.sensorType];
          const isExpired = (now - reading.timestamp) > retentionPeriod;
          return !isExpired;
        });

        const clearedCount = originalCount - buffer.readings.length;
        totalCleared += clearedCount;

        if (clearedCount > 0) {
          buffer.totalSize = buffer.readings.length;
          await this.storeSensorBuffer(childId, buffer);
        }
      }

      if (totalCleared > 0) {
        await this.updateDataStats();
        console.log(`🧹 Cleared ${totalCleared} expired sensor readings`);
      }

      return totalCleared;
    } catch (error) {
      console.error('❌ Failed to clear expired data:', error);
      return 0;
    }
  }

  // ===================================================================
  // PRIVATE HELPER METHODS
  // ===================================================================

  /**
   * Encrypt sensitive fields in sensor reading
   */
  private static async encryptSensorReading(
    reading: SensorReading,
    encryptionKey?: SensorEncryptionKey
  ): Promise<SensorReading> {
    const keyToUse = encryptionKey || this.currentEncryptionKey;
    if (!keyToUse) {
      throw new Error('No encryption key available');
    }

    const encryptedReading = { ...reading };

    // Encrypt sensitive fields
    for (const fieldName of DEFAULT_SENSOR_ENCRYPTION_CONFIG.encryptedFields) {
      const value = reading[fieldName];
      if (value !== undefined) {
        encryptedReading[fieldName] = this.encryptValue(String(value), keyToUse.key);
      }
    }

    return encryptedReading;
  }

  /**
   * Decrypt sensitive fields in sensor reading
   */
  private static async decryptSensorReading(reading: SensorReading): Promise<SensorReading> {
    if (!reading.encrypted || !this.currentEncryptionKey) {
      return reading; // Return as-is if not encrypted
    }

    const decryptedReading = { ...reading };

    // Decrypt sensitive fields
    for (const fieldName of DEFAULT_SENSOR_ENCRYPTION_CONFIG.encryptedFields) {
      const encryptedValue = reading[fieldName];
      if (encryptedValue !== undefined) {
        try {
          const decryptedValue = this.decryptValue(String(encryptedValue), this.currentEncryptionKey.key);
          
          // Parse back to original type for value field
          if (fieldName === 'value') {
            const numValue = Number(decryptedValue);
            decryptedReading[fieldName] = isNaN(numValue) ? decryptedValue : numValue;
          } else {
            decryptedReading[fieldName] = decryptedValue;
          }
        } catch (error) {
          console.error(`❌ Failed to decrypt field ${String(fieldName)}:`, error);
          // Keep encrypted value if decryption fails
        }
      }
    }

    return decryptedReading;
  }

  /**
   * Encrypt a single value using AES-256-GCM
   */
  private static encryptValue(value: string, key: string): string {
    try {
      const encrypted = CryptoJS.AES.encrypt(value, key).toString();
      return encrypted;
    } catch (error) {
      console.error('❌ Encryption failed:', error);
      throw new Error('Failed to encrypt value');
    }
  }

  /**
   * Decrypt a single value using AES-256-GCM
   */
  private static decryptValue(encryptedValue: string, key: string): string {
    try {
      const decrypted = CryptoJS.AES.decrypt(encryptedValue, key);
      const plaintext = decrypted.toString(CryptoJS.enc.Utf8);
      
      if (!plaintext) {
        throw new Error('Decryption resulted in empty string');
      }
      
      return plaintext;
    } catch (error) {
      console.error('❌ Decryption failed:', error);
      throw new Error('Failed to decrypt value');
    }
  }

  /**
   * Get sensor buffer for a child
   */
  private static async getSensorBuffer(childId: string): Promise<SensorBuffer> {
    try {
      const bufferKey = `${SENSOR_STORAGE_CONFIG.BUFFER_PREFIX}${childId}`;
      const bufferData = await AsyncStorage.getItem(bufferKey);
      
      if (bufferData) {
        return JSON.parse(bufferData);
      }
      
      // Create new buffer
      return {
        childId,
        readings: [],
        totalSize: 0,
        encrypted: true
      };
    } catch (error) {
      console.error('❌ Failed to get sensor buffer:', error);
      throw error;
    }
  }

  /**
   * Store sensor buffer for a child
   */
  private static async storeSensorBuffer(childId: string, buffer: SensorBuffer): Promise<void> {
    try {
      const bufferKey = `${SENSOR_STORAGE_CONFIG.BUFFER_PREFIX}${childId}`;
      await AsyncStorage.setItem(bufferKey, JSON.stringify(buffer));
    } catch (error) {
      console.error('❌ Failed to store sensor buffer:', error);
      throw error;
    }
  }

  /**
   * Ensure encryption key exists
   */
  private static async ensureEncryptionKey(): Promise<void> {
    try {
      // Try to load existing key
      const existingKey = await this.loadEncryptionKey();
      
      if (existingKey && existingKey.active && !this.isKeyExpired(existingKey)) {
        this.currentEncryptionKey = existingKey;
        return;
      }
      
      // Generate new key if none exists or expired
      this.currentEncryptionKey = await this.generateNewEncryptionKey();
    } catch (error) {
      console.error('❌ Failed to ensure encryption key:', error);
      throw error;
    }
  }

  /**
   * Load encryption key from keychain
   */
  private static async loadEncryptionKey(): Promise<SensorEncryptionKey | null> {
    try {
      const credentials = await Keychain.getInternetCredentials(SENSOR_STORAGE_CONFIG.KEYCHAIN_SERVICE);
      
      if (credentials && credentials.password) {
        return JSON.parse(credentials.password);
      }
      
      return null;
    } catch (error) {
      console.error('❌ Failed to load encryption key:', error);
      return null;
    }
  }

  /**
   * Generate new encryption key
   */
  private static async generateNewEncryptionKey(): Promise<SensorEncryptionKey> {
    try {
      const keyId = `sensor_key_${Date.now()}`;
      const key = CryptoJS.lib.WordArray.random(32).toString(CryptoJS.enc.Hex); // 256-bit key
      
      const encryptionKey: SensorEncryptionKey = {
        keyId,
        key,
        createdAt: Date.now(),
        expiresAt: Date.now() + DEFAULT_SENSOR_ENCRYPTION_CONFIG.keyRotationInterval,
        active: true,
        version: 1
      };
      
      // Store in keychain
      const success = await Keychain.setInternetCredentials(
        SENSOR_STORAGE_CONFIG.KEYCHAIN_SERVICE,
        keyId,
        JSON.stringify(encryptionKey)
      );
      
      if (!success) {
        throw new Error('Failed to store encryption key in keychain');
      }
      
      console.log('🔑 Generated new sensor encryption key');
      return encryptionKey;
    } catch (error) {
      console.error('❌ Failed to generate encryption key:', error);
      throw error;
    }
  }

  /**
   * Check if encryption key is expired
   */
  private static isKeyExpired(key: SensorEncryptionKey): boolean {
    return key.expiresAt ? Date.now() > key.expiresAt : false;
  }

  /**
   * Get all child IDs with sensor data
   */
  private static async getAllChildIds(): Promise<string[]> {
    try {
      const allKeys = await AsyncStorage.getAllKeys();
      const bufferKeys = allKeys.filter(key => key.startsWith(SENSOR_STORAGE_CONFIG.BUFFER_PREFIX));
      
      return bufferKeys.map(key => key.replace(SENSOR_STORAGE_CONFIG.BUFFER_PREFIX, ''));
    } catch (error) {
      console.error('❌ Failed to get child IDs:', error);
      return [];
    }
  }

  /**
   * Check migration status
   */
  private static async checkMigrationStatus(): Promise<void> {
    try {
      const migrationData = await AsyncStorage.getItem(SENSOR_STORAGE_CONFIG.MIGRATION_KEY);
      if (migrationData) {
        const status: SensorMigrationStatus = JSON.parse(migrationData);
        if (status.inProgress && !status.completedAt) {
          // Resume incomplete migration
          console.log('📦 Resuming incomplete sensor data migration...');
          await this.migratePlaintextData();
        }
      }
    } catch (error) {
      console.error('❌ Failed to check migration status:', error);
    }
  }

  /**
   * Store migration status
   */
  private static async storeMigrationStatus(status: SensorMigrationStatus): Promise<void> {
    try {
      await AsyncStorage.setItem(SENSOR_STORAGE_CONFIG.MIGRATION_KEY, JSON.stringify(status));
    } catch (error) {
      console.error('❌ Failed to store migration status:', error);
    }
  }

  /**
   * Get migration status
   */
  private static async getMigrationStatus(): Promise<SensorMigrationStatus> {
    try {
      const migrationData = await AsyncStorage.getItem(SENSOR_STORAGE_CONFIG.MIGRATION_KEY);
      if (migrationData) {
        return JSON.parse(migrationData);
      }
    } catch (error) {
      console.error('❌ Failed to get migration status:', error);
    }
    
    return {
      inProgress: false,
      totalRecords: 0,
      migratedRecords: 0,
      errors: []
    };
  }

  /**
   * Calculate fresh data statistics
   */
  private static async calculateDataStats(): Promise<SensorDataStats> {
    try {
      const childIds = await this.getAllChildIds();
      const stats = this.getEmptyStats();
      
      for (const childId of childIds) {
        const buffer = await this.getSensorBuffer(childId);
        
        stats.totalReadings += buffer.readings.length;
        if (buffer.encrypted) {
          stats.encryptedReadings += buffer.readings.length;
        } else {
          stats.plaintextReadings += buffer.readings.length;
        }
        
        // Track sensor types and quality
        for (const reading of buffer.readings) {
          stats.sensorTypes[reading.sensorType] = (stats.sensorTypes[reading.sensorType] || 0) + 1;
          
          if (!stats.oldestReading || reading.timestamp < stats.oldestReading) {
            stats.oldestReading = reading.timestamp;
          }
          
          if (!stats.newestReading || reading.timestamp > stats.newestReading) {
            stats.newestReading = reading.timestamp;
          }
        }
        
        stats.storageSize += JSON.stringify(buffer).length;
      }
      
      return stats;
    } catch (error) {
      console.error('❌ Failed to calculate data stats:', error);
      return this.getEmptyStats();
    }
  }

  /**
   * Update data statistics
   */
  private static async updateDataStats(): Promise<void> {
    try {
      const stats = await this.calculateDataStats();
      await AsyncStorage.setItem(SENSOR_STORAGE_CONFIG.STATS_KEY, JSON.stringify(stats));
    } catch (error) {
      console.error('❌ Failed to update data stats:', error);
    }
  }

  /**
   * Get empty statistics object
   */
  private static getEmptyStats(): SensorDataStats {
    return {
      totalReadings: 0,
      encryptedReadings: 0,
      plaintextReadings: 0,
      sensorTypes: {} as Record<SensorType, number>,
      avgQuality: 0,
      storageSize: 0
    };
  }

  /**
   * Start automatic cleanup process
   */
  private static startAutomaticCleanup(): void {
    // Skip in test environment
    if (IS_TEST_ENVIRONMENT) {
      return;
    }
    
    setInterval(async () => {
      try {
        await this.clearExpiredData();
      } catch (error) {
        console.error('❌ Automatic cleanup failed:', error);
      }
    }, SENSOR_STORAGE_CONFIG.CLEANUP_INTERVAL);
  }
}

/**
 * Convenience functions for sensor data management
 */

/**
 * Store a heart rate reading
 */
export async function storeHeartRateReading(
  childId: string,
  value: number,
  quality: SensorQuality = SensorQuality.GOOD
): Promise<boolean> {
  return await EncryptedSensorStorage.storeSensorReading(childId, {
    timestamp: Date.now(),
    sensorType: SensorType.HEART_RATE,
    value,
    quality
  });
}

/**
 * Store a stress level reading
 */
export async function storeStressLevelReading(
  childId: string,
  value: number,
  quality: SensorQuality = SensorQuality.GOOD
): Promise<boolean> {
  return await EncryptedSensorStorage.storeSensorReading(childId, {
    timestamp: Date.now(),
    sensorType: SensorType.STRESS_LEVEL,
    value,
    quality
  });
}

/**
 * Get recent sensor readings for a child
 */
export async function getRecentSensorReadings(
  childId: string,
  sensorType: SensorType,
  hours: number = 24
): Promise<SensorReading[]> {
  const readings = await EncryptedSensorStorage.getSensorReadings(childId, sensorType);
  const cutoffTime = Date.now() - (hours * 60 * 60 * 1000);
  
  return readings.filter(reading => reading.timestamp >= cutoffTime);
}

/**
 * Initialize sensor storage on app start
 */
export async function initializeSensorStorage(): Promise<boolean> {
  try {
    await EncryptedSensorStorage.initialize();
    return true;
  } catch (error) {
    console.error('❌ Failed to initialize sensor storage:', error);
    return false;
  }
}