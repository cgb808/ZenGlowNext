/**
 * Integration tests for the sensor buffer system
 */

import {
  SensorBuffer,
  MockTransportAdapter,
  createSensorBuffer,
  createMockTransport,
} from '../index';
import { SensorReadingInput } from '../types';

// Mock expo-sqlite for integration tests
jest.mock('expo-sqlite', () => ({
  openDatabaseAsync: jest.fn().mockResolvedValue({
    execAsync: jest.fn().mockResolvedValue(undefined),
    runAsync: jest.fn().mockResolvedValue({ changes: 1, lastInsertRowId: 1 }),
    getAllAsync: jest.fn().mockResolvedValue([]),
    getFirstAsync: jest.fn().mockResolvedValue({ count: 0 }),
    withTransactionAsync: jest.fn().mockImplementation(async (callback) => {
      await callback();
    }),
    closeAsync: jest.fn().mockResolvedValue(undefined),
  }),
}));

// Mock React Native AppState
jest.mock('react-native', () => ({
  AppState: {
    addEventListener: jest.fn().mockReturnValue({ remove: jest.fn() }),
  },
}));

describe('SensorBuffer Integration Tests', () => {
  let sensorBuffer: SensorBuffer;
  let mockTransport: MockTransportAdapter;

  beforeEach(async () => {
    mockTransport = createMockTransport(true, 10);
    
    sensorBuffer = createSensorBuffer({
      databaseName: 'test_integration.db',
      debug: true,
      transport: mockTransport,
      flush: {
        flushInterval: 100, // Short interval for testing
        batchSize: 3,
        maxAge: 1000,
        enableAppStateFlush: true,
      },
    });

    await sensorBuffer.initialize();
  });

  afterEach(async () => {
    await sensorBuffer.shutdown();
  });

  describe('complete workflow', () => {
    it('should handle complete sensor reading lifecycle', async () => {
      // Insert some readings
      const readings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 25.5, quality: 90 },
        { sensor_type: 'humidity', value: 60.0, quality: 85 },
        { sensor_type: 'pressure', value: 1013.25, quality: 95 },
      ];

      // Insert readings one by one
      for (const reading of readings) {
        const success = await sensorBuffer.insertReading(reading);
        expect(success).toBe(true);
      }

      // Check that we have pending readings
      const pendingReadings = await sensorBuffer.getPending();
      expect(pendingReadings.length).toBeGreaterThan(0);

      // Manual flush
      const flushEvent = await sensorBuffer.flush();
      expect(flushEvent.success).toBe(true);
      expect(flushEvent.readingsCount).toBe(3);

      // Verify transport received the readings
      expect(mockTransport.sentBatches).toHaveLength(1);
      expect(mockTransport.getTotalSentReadings()).toBe(3);

      // Verify readings are marked as flushed
      const pendingAfterFlush = await sensorBuffer.getPending();
      expect(pendingAfterFlush.length).toBe(0);
    });

    it('should handle batch insertion', async () => {
      const readings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 25.5, quality: 90 },
        { sensor_type: 'humidity', value: 60.0, quality: 85 },
        { sensor_type: 'pressure', value: 1013.25, quality: 95 },
        { sensor_type: 'light', value: 800, quality: 80 },
        { sensor_type: 'sound', value: 45, quality: 75 },
      ];

      const success = await sensorBuffer.insertBatch(readings);
      expect(success).toBe(true);

      // Check statistics
      const stats = await sensorBuffer.getStats();
      expect(stats.totalReadings).toBe(5);
      expect(stats.pendingReadings).toBe(5);
      expect(stats.flushedReadings).toBe(0);
    });

    it('should handle transport failures gracefully', async () => {
      // Set up failing transport
      const failingTransport = createMockTransport(false, 10);
      sensorBuffer.setTransport(failingTransport);

      // Insert readings
      await sensorBuffer.insertReading({
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      });

      // Try to flush
      const flushEvent = await sensorBuffer.flush();
      expect(flushEvent.success).toBe(false);
      expect(flushEvent.error).toBe('Mock transport failure');

      // Readings should still be pending
      const pendingReadings = await sensorBuffer.getPending();
      expect(pendingReadings.length).toBe(1);
    });

    it('should purge old readings', async () => {
      const oldTimestamp = Date.now() - 10000; // 10 seconds ago

      // Insert some old readings
      const oldReadings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 20.0, quality: 80, ts: oldTimestamp },
        { sensor_type: 'humidity', value: 55.0, quality: 75, ts: oldTimestamp },
      ];

      // Insert some new readings
      const newReadings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 25.5, quality: 90 },
        { sensor_type: 'humidity', value: 60.0, quality: 85 },
      ];

      await sensorBuffer.insertBatch(oldReadings);
      await sensorBuffer.insertBatch(newReadings);

      // Check total before purge
      let stats = await sensorBuffer.getStats();
      expect(stats.totalReadings).toBe(4);

      // Purge readings older than 5 seconds ago
      const purgedCount = await sensorBuffer.purge(Date.now() - 5000);
      expect(purgedCount).toBe(2);

      // Check total after purge
      stats = await sensorBuffer.getStats();
      expect(stats.totalReadings).toBe(2);
    });
  });

  describe('configuration and status', () => {
    it('should provide accurate status information', () => {
      const status = sensorBuffer.getStatus();

      expect(status.isInitialized).toBe(true);
      expect(status.databaseReady).toBe(true);
      expect(status.hasTransport).toBe(true);
      expect(status.schedulerStatus.isRunning).toBe(true);
    });

    it('should allow configuration updates', () => {
      sensorBuffer.updateConfig({
        flush: {
          flushInterval: 200,
          batchSize: 5,
          maxAge: 2000,
          enableAppStateFlush: false,
        },
      });

      const status = sensorBuffer.getStatus();
      expect(status.schedulerStatus.isRunning).toBe(true); // Should restart
    });

    it('should handle flush event listeners', async () => {
      const eventListener = jest.fn();
      sensorBuffer.addFlushEventListener(eventListener);

      // Insert and flush
      await sensorBuffer.insertReading({
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      });

      await sensorBuffer.flush();

      expect(eventListener).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger: 'manual',
          success: true,
          readingsCount: 1,
        })
      );

      // Remove listener and test
      sensorBuffer.removeFlushEventListener(eventListener);
      eventListener.mockClear();

      await sensorBuffer.insertReading({
        sensor_type: 'humidity',
        value: 60.0,
        quality: 85,
      });

      await sensorBuffer.flush();

      expect(eventListener).not.toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('should handle database errors gracefully', async () => {
      // Mock database to fail
      const mockDatabase = (sensorBuffer as any).database;
      mockDatabase.insertReading = jest.fn().mockResolvedValue(false);

      const success = await sensorBuffer.insertReading({
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      });

      expect(success).toBe(false);
    });

    it('should handle uninitialized state', async () => {
      const uninitializedBuffer = createSensorBuffer();

      const insertResult = await uninitializedBuffer.insertReading({
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      });

      const pendingResult = await uninitializedBuffer.getPending();
      const statsResult = await uninitializedBuffer.getStats();
      const flushResult = await uninitializedBuffer.flush();

      expect(insertResult).toBe(false);
      expect(pendingResult).toEqual([]);
      expect(statsResult.totalReadings).toBe(0);
      expect(flushResult.success).toBe(false);
    });
  });

  describe('convenience factory functions', () => {
    it('should create sensor buffer with defaults', () => {
      const buffer = createSensorBuffer();
      expect(buffer).toBeInstanceOf(SensorBuffer);
    });

    it('should create mock transport', () => {
      const transport = createMockTransport(false, 50);
      expect(transport).toBeInstanceOf(MockTransportAdapter);
    });
  });

  describe('real-world usage patterns', () => {
    it('should handle high-frequency sensor data', async () => {
      // Simulate rapid sensor readings
      const readings: SensorReadingInput[] = [];
      const startTime = Date.now();

      // Generate 50 readings over time
      for (let i = 0; i < 50; i++) {
        readings.push({
          sensor_type: i % 2 === 0 ? 'temperature' : 'humidity',
          value: Math.random() * 100,
          quality: Math.floor(Math.random() * 100),
          ts: startTime + i * 100, // 100ms apart
        });
      }

      // Insert in batches
      const batchSize = 10;
      for (let i = 0; i < readings.length; i += batchSize) {
        const batch = readings.slice(i, i + batchSize);
        const success = await sensorBuffer.insertBatch(batch);
        expect(success).toBe(true);
      }

      // Check that all readings were inserted
      const stats = await sensorBuffer.getStats();
      expect(stats.totalReadings).toBe(50);

      // Flush all
      const flushEvent = await sensorBuffer.flush();
      expect(flushEvent.success).toBe(true);
      expect(flushEvent.readingsCount).toBe(50);
    });

    it('should handle mixed sensor types', async () => {
      const sensorTypes = [
        'temperature',
        'humidity',
        'pressure',
        'light',
        'sound',
        'accelerometer_x',
        'accelerometer_y',
        'accelerometer_z',
        'gyroscope_x',
        'gyroscope_y',
      ];

      // Insert readings for each sensor type
      for (const sensorType of sensorTypes) {
        await sensorBuffer.insertReading({
          sensor_type: sensorType,
          value: Math.random() * 100,
          quality: Math.floor(Math.random() * 100),
        });
      }

      const stats = await sensorBuffer.getStats();
      expect(stats.totalReadings).toBe(sensorTypes.length);

      // Flush and verify
      const flushEvent = await sensorBuffer.flush();
      expect(flushEvent.success).toBe(true);
      expect(mockTransport.sentBatches[0].length).toBe(sensorTypes.length);

      // Verify different sensor types were included
      const sentReading = mockTransport.sentBatches[0];
      const uniqueSensorTypes = new Set(sentReading.map(r => r.sensor_type));
      expect(uniqueSensorTypes.size).toBe(sensorTypes.length);
    });
  });
});