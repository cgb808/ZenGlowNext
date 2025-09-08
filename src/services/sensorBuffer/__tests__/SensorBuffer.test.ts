/**
 * Tests for SensorBuffer main class
 */

import { SensorBuffer } from '../SensorBuffer';
import { MockTransportAdapter } from '../TransportAdapter';
import { SensorReadingInput } from '../types';

// Mock all dependencies
jest.mock('../SensorDatabase');
jest.mock('../FlushScheduler');

describe('SensorBuffer', () => {
  let sensorBuffer: SensorBuffer;
  let mockTransport: MockTransportAdapter;

  beforeEach(() => {
    mockTransport = new MockTransportAdapter(true, 0);
    
    sensorBuffer = new SensorBuffer({
      databaseName: 'test.db',
      debug: true,
      transport: mockTransport,
      flush: {
        flushInterval: 1000,
        batchSize: 10,
        maxAge: 5000,
        enableAppStateFlush: true,
      },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('should initialize successfully', async () => {
      // Mock database initialization
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);

      const result = await sensorBuffer.initialize();

      expect(result).toBe(true);
      expect(sensorBuffer.isReady()).toBe(true);
    });

    it('should handle initialization failure', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(false);

      const result = await sensorBuffer.initialize();

      expect(result).toBe(false);
      expect(sensorBuffer.isReady()).toBe(false);
    });

    it('should not initialize twice', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);

      await sensorBuffer.initialize();
      mockDatabase.prototype.initialize.mockClear();

      const result = await sensorBuffer.initialize();

      expect(result).toBe(true);
      expect(mockDatabase.prototype.initialize).not.toHaveBeenCalled();
    });
  });

  describe('shutdown', () => {
    it('should shutdown gracefully', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.close = jest.fn().mockResolvedValue(undefined);
      mockFlushScheduler.prototype.stop = jest.fn();
      mockFlushScheduler.prototype.flush = jest.fn().mockResolvedValue({
        trigger: 'manual',
        success: true,
        readingsCount: 0,
        timestamp: Date.now(),
      });

      await sensorBuffer.initialize();
      await sensorBuffer.shutdown();

      expect(mockFlushScheduler.prototype.stop).toHaveBeenCalled();
      expect(mockFlushScheduler.prototype.flush).toHaveBeenCalled();
      expect(mockDatabase.prototype.close).toHaveBeenCalled();
      expect(sensorBuffer.isReady()).toBe(false);
    });
  });

  describe('insertReading', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should insert reading successfully', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      
      mockDatabase.prototype.insertReading = jest.fn().mockResolvedValue(true);
      mockFlushScheduler.prototype.checkAndFlush = jest.fn().mockResolvedValue(null);

      const reading: SensorReadingInput = {
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      };

      const result = await sensorBuffer.insertReading(reading);

      expect(result).toBe(true);
      expect(mockDatabase.prototype.insertReading).toHaveBeenCalledWith(reading);
      expect(mockFlushScheduler.prototype.checkAndFlush).toHaveBeenCalled();
    });

    it('should handle insert failure', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.insertReading = jest.fn().mockResolvedValue(false);

      const reading: SensorReadingInput = {
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      };

      const result = await sensorBuffer.insertReading(reading);

      expect(result).toBe(false);
    });

    it('should fail if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const reading: SensorReadingInput = {
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
      };

      const result = await uninitializedBuffer.insertReading(reading);

      expect(result).toBe(false);
    });
  });

  describe('insertBatch', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should insert batch successfully', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      
      mockDatabase.prototype.insertBatch = jest.fn().mockResolvedValue(true);
      mockFlushScheduler.prototype.checkAndFlush = jest.fn().mockResolvedValue(null);

      const readings: SensorReadingInput[] = [
        { sensor_type: 'temperature', value: 25.5, quality: 90 },
        { sensor_type: 'humidity', value: 60.0, quality: 85 },
      ];

      const result = await sensorBuffer.insertBatch(readings);

      expect(result).toBe(true);
      expect(mockDatabase.prototype.insertBatch).toHaveBeenCalledWith(readings);
      expect(mockFlushScheduler.prototype.checkAndFlush).toHaveBeenCalled();
    });

    it('should handle empty batch', async () => {
      const result = await sensorBuffer.insertBatch([]);

      expect(result).toBe(true);
    });

    it('should fail if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const result = await uninitializedBuffer.insertBatch([
        { sensor_type: 'temperature', value: 25.5, quality: 90 },
      ]);

      expect(result).toBe(false);
    });
  });

  describe('getPending', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should get pending readings', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];
      mockDatabase.prototype.getPending = jest.fn().mockResolvedValue(mockReadings);

      const result = await sensorBuffer.getPending();

      expect(result).toEqual(mockReadings);
      expect(mockDatabase.prototype.getPending).toHaveBeenCalledWith(undefined);
    });

    it('should get pending readings with limit', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];
      mockDatabase.prototype.getPending = jest.fn().mockResolvedValue(mockReadings);

      const result = await sensorBuffer.getPending(10);

      expect(result).toEqual(mockReadings);
      expect(mockDatabase.prototype.getPending).toHaveBeenCalledWith(10);
    });

    it('should return empty array if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const result = await uninitializedBuffer.getPending();

      expect(result).toEqual([]);
    });
  });

  describe('markFlushed', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should mark readings as flushed', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.markFlushed = jest.fn().mockResolvedValue(true);

      const result = await sensorBuffer.markFlushed([1, 2, 3]);

      expect(result).toBe(true);
      expect(mockDatabase.prototype.markFlushed).toHaveBeenCalledWith([1, 2, 3]);
    });

    it('should fail if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const result = await uninitializedBuffer.markFlushed([1, 2, 3]);

      expect(result).toBe(false);
    });
  });

  describe('purge', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should purge readings', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.purge = jest.fn().mockResolvedValue(5);

      const result = await sensorBuffer.purge(1000000);

      expect(result).toBe(5);
      expect(mockDatabase.prototype.purge).toHaveBeenCalledWith(1000000);
    });

    it('should return 0 if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const result = await uninitializedBuffer.purge();

      expect(result).toBe(0);
    });
  });

  describe('flush', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should trigger manual flush', async () => {
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      const mockEvent = {
        trigger: 'manual',
        success: true,
        readingsCount: 2,
        timestamp: Date.now(),
      };
      mockFlushScheduler.prototype.flush = jest.fn().mockResolvedValue(mockEvent);

      const result = await sensorBuffer.flush();

      expect(result).toEqual(mockEvent);
      expect(mockFlushScheduler.prototype.flush).toHaveBeenCalled();
    });

    it('should return error event if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const result = await uninitializedBuffer.flush();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Not initialized');
    });
  });

  describe('getStats', () => {
    beforeEach(async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      await sensorBuffer.initialize();
    });

    it('should get buffer statistics', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockStats = {
        total: 100,
        pending: 20,
        flushed: 80,
        oldestTs: 1000,
        newestTs: 5000,
      };
      mockDatabase.prototype.getStats = jest.fn().mockResolvedValue(mockStats);

      const result = await sensorBuffer.getStats();

      expect(result).toEqual({
        totalReadings: 100,
        pendingReadings: 20,
        flushedReadings: 80,
        oldestReading: 1000,
        newestReading: 5000,
      });
    });

    it('should return default stats if not initialized', async () => {
      const uninitializedBuffer = new SensorBuffer();

      const result = await uninitializedBuffer.getStats();

      expect(result).toEqual({
        totalReadings: 0,
        pendingReadings: 0,
        flushedReadings: 0,
      });
    });
  });

  describe('transport management', () => {
    it('should set transport adapter', () => {
      const newTransport = new MockTransportAdapter(false);
      
      sensorBuffer.setTransport(newTransport);

      const status = sensorBuffer.getStatus();
      expect(status.hasTransport).toBe(true);
    });

    it('should update configuration', () => {
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      mockFlushScheduler.prototype.updateConfig = jest.fn();

      sensorBuffer.updateConfig({
        flush: {
          flushInterval: 2000,
          batchSize: 20,
          maxAge: 10000,
          enableAppStateFlush: false,
        },
      });

      expect(mockFlushScheduler.prototype.updateConfig).toHaveBeenCalled();
    });
  });

  describe('event listeners', () => {
    it('should manage flush event listeners', () => {
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      mockFlushScheduler.prototype.addFlushEventListener = jest.fn();
      mockFlushScheduler.prototype.removeFlushEventListener = jest.fn();

      const listener = jest.fn();

      sensorBuffer.addFlushEventListener(listener);
      expect(mockFlushScheduler.prototype.addFlushEventListener).toHaveBeenCalledWith(listener);

      sensorBuffer.removeFlushEventListener(listener);
      expect(mockFlushScheduler.prototype.removeFlushEventListener).toHaveBeenCalledWith(listener);
    });
  });

  describe('getStatus', () => {
    it('should return comprehensive status', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      const mockFlushScheduler = require('../FlushScheduler').FlushScheduler;
      
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);
      mockFlushScheduler.prototype.getStatus = jest.fn().mockReturnValue({
        isRunning: true,
        isFlushInProgress: false,
        config: {},
      });

      await sensorBuffer.initialize();

      const status = sensorBuffer.getStatus();

      expect(status).toMatchObject({
        isInitialized: true,
        schedulerStatus: {
          isRunning: true,
          isFlushInProgress: false,
        },
        databaseReady: true,
        hasTransport: true,
      });
    });
  });

  describe('isReady', () => {
    it('should return true when fully initialized', async () => {
      const mockDatabase = require('../SensorDatabase').SensorDatabase;
      mockDatabase.prototype.initialize = jest.fn().mockResolvedValue(true);
      mockDatabase.prototype.isReady = jest.fn().mockReturnValue(true);

      await sensorBuffer.initialize();

      expect(sensorBuffer.isReady()).toBe(true);
    });

    it('should return false when not initialized', () => {
      expect(sensorBuffer.isReady()).toBe(false);
    });
  });
});