/**
 * Encrypted Sensor Storage Tests
 * Comprehensive tests for sensor data encryption, key rotation, and migration
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Keychain from 'react-native-keychain';
import { 
  EncryptedSensorStorage,
  storeHeartRateReading,
  storeStressLevelReading,
  getRecentSensorReadings,
  initializeSensorStorage
} from '../../src/utils/EncryptedSensorStorage';
import {
  SensorType,
  SensorQuality,
  SensorReading,
  SensorBuffer
} from '../../src/types/SensorData';

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage');
jest.mock('react-native-keychain');
jest.mock('crypto-js', () => ({
  AES: {
    encrypt: jest.fn((value, key) => ({
      toString: () => `encrypted_${value}_with_${key.substring(0, 8)}`
    })),
    decrypt: jest.fn((encryptedValue, key) => ({
      toString: jest.fn((encoding) => {
        if (typeof encryptedValue === 'string') {
          const match = encryptedValue.match(/encrypted_(.+)_with_(.+)/);
          return match ? match[1] : encryptedValue;
        }
        return '';
      })
    }))
  },
  enc: {
    Utf8: 'utf8'
  },
  lib: {
    WordArray: {
      random: jest.fn(() => ({
        toString: () => 'test_key_32_characters_long_12345'
      }))
    }
  }
}));

const mockAsyncStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;
const mockKeychain = Keychain as jest.Mocked<typeof Keychain>;

describe('EncryptedSensorStorage', () => {
  const testChildId = 'test-child-123';
  const testEncryptionKey = {
    keyId: 'test_key_123',
    key: 'test_encryption_key_32_chars_long',
    createdAt: Date.now(),
    active: true,
    version: 1
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset static state
    (EncryptedSensorStorage as any).isInitialized = false;
    (EncryptedSensorStorage as any).currentEncryptionKey = null;
    (EncryptedSensorStorage as any).migrationInProgress = false;
    
    // Mock AsyncStorage
    const storage = new Map();
    mockAsyncStorage.getItem.mockImplementation((key) => 
      Promise.resolve(storage.get(key) || null)
    );
    mockAsyncStorage.setItem.mockImplementation((key, value) => {
      storage.set(key, value);
      return Promise.resolve();
    });
    mockAsyncStorage.removeItem.mockImplementation((key) => {
      storage.delete(key);
      return Promise.resolve();
    });
    mockAsyncStorage.getAllKeys.mockImplementation(() => 
      Promise.resolve(Array.from(storage.keys()))
    );
    mockAsyncStorage.multiRemove.mockImplementation((keys) => {
      keys.forEach(key => storage.delete(key));
      return Promise.resolve();
    });

    // Mock Keychain
    mockKeychain.getInternetCredentials.mockResolvedValue({
      username: testEncryptionKey.keyId,
      password: JSON.stringify(testEncryptionKey),
      service: 'ZenGlow-SensorEncryption'
    });
    mockKeychain.setInternetCredentials.mockResolvedValue(true);
  });

  describe('Initialization', () => {
    it('initializes successfully with existing encryption key', async () => {
      const result = await initializeSensorStorage();
      
      expect(result).toBe(true);
      expect(mockKeychain.getInternetCredentials).toHaveBeenCalledWith('ZenGlow-SensorEncryption');
    });

    it('generates new encryption key when none exists', async () => {
      mockKeychain.getInternetCredentials.mockResolvedValue(false);
      
      const result = await initializeSensorStorage();
      
      expect(result).toBe(true);
      expect(mockKeychain.setInternetCredentials).toHaveBeenCalledWith(
        'ZenGlow-SensorEncryption',
        expect.stringContaining('sensor_key_'),
        expect.any(String)
      );
    });

    it('handles initialization errors gracefully', async () => {
      mockKeychain.getInternetCredentials.mockRejectedValue(new Error('Keychain error'));
      mockKeychain.setInternetCredentials.mockRejectedValue(new Error('Keychain unavailable'));
      
      const result = await initializeSensorStorage();
      
      expect(result).toBe(false);
    });
  });

  describe('Sensor Data Storage', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
    });

    it('stores heart rate reading with encryption', async () => {
      const heartRate = 72;
      const result = await storeHeartRateReading(testChildId, heartRate, SensorQuality.EXCELLENT);
      
      expect(result).toBe(true);
      
      // Verify data was stored
      const storedData = await mockAsyncStorage.getItem(`sensor_buffer_${testChildId}`);
      expect(storedData).toBeTruthy();
      
      const buffer: SensorBuffer = JSON.parse(storedData!);
      expect(buffer.encrypted).toBe(true);
      expect(buffer.readings).toHaveLength(1);
      expect(buffer.readings[0].sensorType).toBe(SensorType.HEART_RATE);
      expect(buffer.readings[0].encrypted).toBe(true);
    });

    it('stores stress level reading with encryption', async () => {
      const stressLevel = 3.5;
      const result = await storeStressLevelReading(testChildId, stressLevel, SensorQuality.GOOD);
      
      expect(result).toBe(true);
      
      const storedData = await mockAsyncStorage.getItem(`sensor_buffer_${testChildId}`);
      const buffer: SensorBuffer = JSON.parse(storedData!);
      
      expect(buffer.readings).toHaveLength(1);
      expect(buffer.readings[0].sensorType).toBe(SensorType.STRESS_LEVEL);
      expect(buffer.readings[0].encrypted).toBe(true);
    });

    it('enforces buffer size limit', async () => {
      const maxSize = 1000; // From SENSOR_STORAGE_CONFIG.MAX_BUFFER_SIZE
      
      // Store readings beyond limit
      for (let i = 0; i < maxSize + 50; i++) {
        await storeHeartRateReading(testChildId, 70 + i, SensorQuality.GOOD);
      }
      
      const storedData = await mockAsyncStorage.getItem(`sensor_buffer_${testChildId}`);
      const buffer: SensorBuffer = JSON.parse(storedData!);
      
      expect(buffer.readings).toHaveLength(maxSize);
      expect(buffer.totalSize).toBe(maxSize);
    });

    it('handles storage errors gracefully', async () => {
      mockAsyncStorage.setItem.mockRejectedValue(new Error('Storage error'));
      
      const result = await storeHeartRateReading(testChildId, 72);
      
      expect(result).toBe(false);
    });
  });

  describe('Sensor Data Retrieval', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
      
      // Setup test data
      await storeHeartRateReading(testChildId, 72, SensorQuality.EXCELLENT);
      await storeStressLevelReading(testChildId, 2.1, SensorQuality.GOOD);
      await storeHeartRateReading(testChildId, 75, SensorQuality.FAIR);
    });

    it('retrieves and decrypts sensor readings', async () => {
      const readings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      
      expect(readings).toHaveLength(3);
      expect(readings[0].sensorType).toBe(SensorType.HEART_RATE);
      expect(readings[1].sensorType).toBe(SensorType.STRESS_LEVEL);
      expect(readings[2].sensorType).toBe(SensorType.HEART_RATE);
    });

    it('filters readings by sensor type', async () => {
      const heartRateReadings = await EncryptedSensorStorage.getSensorReadings(
        testChildId, 
        SensorType.HEART_RATE
      );
      
      expect(heartRateReadings).toHaveLength(2);
      expect(heartRateReadings.every(r => r.sensorType === SensorType.HEART_RATE)).toBe(true);
    });

    it('applies limit to returned readings', async () => {
      const limitedReadings = await EncryptedSensorStorage.getSensorReadings(
        testChildId, 
        undefined, 
        2
      );
      
      expect(limitedReadings).toHaveLength(2);
    });

    it('gets recent readings within time window', async () => {
      const recentReadings = await getRecentSensorReadings(
        testChildId, 
        SensorType.HEART_RATE, 
        24
      );
      
      expect(recentReadings).toHaveLength(2);
      expect(recentReadings.every(r => r.sensorType === SensorType.HEART_RATE)).toBe(true);
    });

    it('handles retrieval errors gracefully', async () => {
      mockAsyncStorage.getItem.mockRejectedValue(new Error('Storage error'));
      
      const readings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      
      expect(readings).toEqual([]);
    });
  });

  describe('Key Rotation', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
      await storeHeartRateReading(testChildId, 72);
    });

    it('rotates encryption key successfully', async () => {
      const result = await EncryptedSensorStorage.rotateEncryptionKey();
      
      expect(result).toBe(true);
      expect(mockKeychain.setInternetCredentials).toHaveBeenCalledTimes(2); // Initial + rotation
    });

    it('re-encrypts existing data with new key', async () => {
      await EncryptedSensorStorage.rotateEncryptionKey();
      
      // Verify data is still accessible
      const readings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      expect(readings).toHaveLength(1);
      expect(readings[0].sensorType).toBe(SensorType.HEART_RATE);
    });

    it('handles key rotation errors gracefully', async () => {
      mockKeychain.setInternetCredentials.mockRejectedValue(new Error('Keychain error'));
      
      const result = await EncryptedSensorStorage.rotateEncryptionKey();
      
      expect(result).toBe(false);
    });
  });

  describe('Plaintext Migration', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
    });

    it('migrates plaintext data to encrypted format', async () => {
      // Setup plaintext data
      const plaintextBuffer: SensorBuffer = {
        childId: testChildId,
        readings: [
          {
            id: 'test-reading-1',
            timestamp: Date.now(),
            sensorType: SensorType.HEART_RATE,
            value: 72,
            quality: SensorQuality.GOOD,
            encrypted: false
          }
        ],
        totalSize: 1,
        encrypted: false
      };
      
      await mockAsyncStorage.setItem(
        `sensor_buffer_${testChildId}`,
        JSON.stringify(plaintextBuffer)
      );
      
      const migrationStatus = await EncryptedSensorStorage.migratePlaintextData();
      
      expect(migrationStatus.inProgress).toBe(false);
      expect(migrationStatus.migratedRecords).toBe(1);
      expect(migrationStatus.totalRecords).toBe(1);
      expect(migrationStatus.completedAt).toBeTruthy();
    });

    it('skips already encrypted buffers during migration', async () => {
      // Setup encrypted data
      await storeHeartRateReading(testChildId, 72);
      
      const migrationStatus = await EncryptedSensorStorage.migratePlaintextData();
      
      expect(migrationStatus.migratedRecords).toBe(0);
      expect(migrationStatus.totalRecords).toBe(0);
    });

    it('handles migration errors gracefully', async () => {
      // Setup invalid data
      await mockAsyncStorage.setItem(
        `sensor_buffer_invalid`,
        'invalid-json-data'
      );
      
      const migrationStatus = await EncryptedSensorStorage.migratePlaintextData();
      
      expect(migrationStatus.errors.length).toBeGreaterThan(0);
      expect(migrationStatus.inProgress).toBe(false);
    });
  });

  describe('Data Statistics', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
      await storeHeartRateReading(testChildId, 72);
      await storeStressLevelReading(testChildId, 2.5);
    });

    it('calculates accurate data statistics', async () => {
      const stats = await EncryptedSensorStorage.getDataStats();
      
      expect(stats.totalReadings).toBe(2);
      expect(stats.encryptedReadings).toBe(2);
      expect(stats.plaintextReadings).toBe(0);
      expect(stats.sensorTypes[SensorType.HEART_RATE]).toBe(1);
      expect(stats.sensorTypes[SensorType.STRESS_LEVEL]).toBe(1);
      expect(stats.storageSize).toBeGreaterThan(0);
    });

    it('handles statistics calculation errors', async () => {
      mockAsyncStorage.getItem.mockRejectedValue(new Error('Storage error'));
      
      const stats = await EncryptedSensorStorage.getDataStats();
      
      expect(stats.totalReadings).toBe(0);
      expect(stats.encryptedReadings).toBe(0);
      expect(stats.plaintextReadings).toBe(0);
    });
  });

  describe('Data Expiration', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
    });

    it('clears expired sensor data based on retention policies', async () => {
      // Store old reading (simulate expired data)
      const oldTimestamp = Date.now() - (8 * 24 * 60 * 60 * 1000); // 8 days ago
      await EncryptedSensorStorage.storeSensorReading(testChildId, {
        timestamp: oldTimestamp,
        sensorType: SensorType.HEART_RATE,
        value: 72,
        quality: SensorQuality.GOOD
      });
      
      // Store recent reading
      await storeHeartRateReading(testChildId, 75);
      
      const clearedCount = await EncryptedSensorStorage.clearExpiredData();
      
      expect(clearedCount).toBe(1); // Should clear the old reading
      
      const remainingReadings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      expect(remainingReadings).toHaveLength(1);
    });

    it('preserves non-expired data during cleanup', async () => {
      await storeHeartRateReading(testChildId, 72);
      await storeStressLevelReading(testChildId, 2.0);
      
      const clearedCount = await EncryptedSensorStorage.clearExpiredData();
      
      expect(clearedCount).toBe(0);
      
      const remainingReadings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      expect(remainingReadings).toHaveLength(2);
    });
  });

  describe('Encryption Security', () => {
    beforeEach(async () => {
      await initializeSensorStorage();
    });

    it('encrypts sensitive sensor fields', async () => {
      await storeHeartRateReading(testChildId, 72, SensorQuality.EXCELLENT);
      
      // Get raw stored data (before decryption)
      const storedData = await mockAsyncStorage.getItem(`sensor_buffer_${testChildId}`);
      const buffer: SensorBuffer = JSON.parse(storedData!);
      const storedReading = buffer.readings[0];
      
      // Value and quality should be encrypted (different from original)
      expect(storedReading.value).not.toBe(72);
      expect(storedReading.quality).not.toBe(SensorQuality.EXCELLENT);
      expect(String(storedReading.value)).toContain('encrypted_');
      expect(String(storedReading.quality)).toContain('encrypted_');
    });

    it('preserves non-sensitive fields unencrypted', async () => {
      await storeHeartRateReading(testChildId, 72);
      
      const storedData = await mockAsyncStorage.getItem(`sensor_buffer_${testChildId}`);
      const buffer: SensorBuffer = JSON.parse(storedData!);
      const storedReading = buffer.readings[0];
      
      // Non-sensitive fields should remain unchanged
      expect(storedReading.sensorType).toBe(SensorType.HEART_RATE);
      expect(storedReading.encrypted).toBe(true);
      expect(storedReading.id).toBeTruthy();
      expect(storedReading.timestamp).toBeGreaterThan(0);
    });

    it('maintains data integrity through encrypt/decrypt cycle', async () => {
      const originalValue = 72;
      const originalQuality = SensorQuality.EXCELLENT;
      
      await storeHeartRateReading(testChildId, originalValue, originalQuality);
      
      const retrievedReadings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      
      expect(retrievedReadings).toHaveLength(1);
      expect(retrievedReadings[0].value).toBe(originalValue);
      expect(retrievedReadings[0].quality).toBe(originalQuality);
      expect(retrievedReadings[0].sensorType).toBe(SensorType.HEART_RATE);
    });
  });

  describe('Error Handling', () => {
    it('handles missing encryption key gracefully', async () => {
      mockKeychain.getInternetCredentials.mockResolvedValue(false);
      mockKeychain.setInternetCredentials.mockRejectedValue(new Error('Keychain unavailable'));
      
      const result = await initializeSensorStorage();
      
      expect(result).toBe(false);
    });

    it('handles corrupted stored data gracefully', async () => {
      await initializeSensorStorage();
      
      // Store corrupted data
      await mockAsyncStorage.setItem(`sensor_buffer_${testChildId}`, 'invalid-json');
      
      const readings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      
      expect(readings).toEqual([]);
    });

    it('handles decryption failures gracefully', async () => {
      await initializeSensorStorage();
      
      // Store data with invalid encryption
      const corruptedBuffer: SensorBuffer = {
        childId: testChildId,
        readings: [
          {
            id: 'test-reading-1',
            timestamp: Date.now(),
            sensorType: SensorType.HEART_RATE,
            value: 'corrupted-encrypted-value',
            quality: 'corrupted-encrypted-quality',
            encrypted: true
          }
        ],
        totalSize: 1,
        encrypted: true
      };
      
      await mockAsyncStorage.setItem(
        `sensor_buffer_${testChildId}`,
        JSON.stringify(corruptedBuffer)
      );
      
      const readings = await EncryptedSensorStorage.getSensorReadings(testChildId);
      
      expect(readings).toHaveLength(1);
      // Should return readings even if decryption fails, preserving encrypted values
      expect(readings[0].value).toBe('corrupted-encrypted-value');
    });
  });
});