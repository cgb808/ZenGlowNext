/**
 * Unit tests for flush scheduler
 */

import { createFlushScheduler, type FlushSchedulerConfig } from '../../src/sensors/flushScheduler';
import { AppState } from 'react-native';

import { sensorDb } from '../../src/sensors/storage/db';
import { stubTransport } from '../../src/sensors/transport';

// Mock dependencies
jest.mock('../../src/sensors/storage/db', () => ({
  sensorDb: {
    init: jest.fn(),
    getPending: jest.fn(),
    getPendingCount: jest.fn(),
    markFlushed: jest.fn(),
    close: jest.fn(),
  }
}));

jest.mock('../../src/sensors/transport', () => ({
  stubTransport: {
    flush: jest.fn(),
  }
}));

// Mock React Native AppState
jest.mock('react-native', () => ({
  AppState: {
    addEventListener: jest.fn(),
  }
}));

const mockSensorDb = sensorDb as jest.Mocked<typeof sensorDb>;
const mockStubTransport = stubTransport as jest.Mocked<typeof stubTransport>;
const mockAppState = AppState as jest.Mocked<typeof AppState>;

describe('FlushScheduler', () => {
  let scheduler: any;
  let mockSubscription: any;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    // Mock console methods to avoid spam
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});

    // Setup AppState mock
    mockSubscription = { remove: jest.fn() };
    mockAppState.addEventListener.mockReturnValue(mockSubscription);

    // Setup default mocks
    mockSensorDb.init.mockResolvedValue(undefined);
    mockSensorDb.getPending.mockResolvedValue([]);
    mockSensorDb.getPendingCount.mockResolvedValue(0);
    mockSensorDb.markFlushed.mockResolvedValue(undefined);
    mockStubTransport.flush.mockResolvedValue({
      success: true,
      flushedIds: []
    });

    const config: Partial<FlushSchedulerConfig> = {
      intervalMs: 1000, // 1 second for faster tests
      batchThreshold: 5,
      enableAppResumeTrigger: true,
      enableIntervalTrigger: true,
      enableBatchTrigger: true
    };

    scheduler = createFlushScheduler(config);
  });

  afterEach(async () => {
    await scheduler.stop();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  describe('start', () => {
    it('initializes database and starts scheduler', async () => {
      await scheduler.start();

      expect(mockSensorDb.init).toHaveBeenCalled();
      expect(mockAppState.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });

    it('warns if already running', async () => {
      await scheduler.start();
      await scheduler.start();

      expect(console.warn).toHaveBeenCalledWith('[FlushScheduler] Already running');
    });

    it('throws error if database initialization fails', async () => {
      const error = new Error('DB init failed');
      mockSensorDb.init.mockRejectedValueOnce(error);

      await expect(scheduler.start()).rejects.toThrow(error);
    });
  });

  describe('stop', () => {
    it('stops scheduler and removes listeners', async () => {
      await scheduler.start();
      await scheduler.stop();

      expect(mockSubscription.remove).toHaveBeenCalled();
    });

    it('does nothing if not running', async () => {
      await scheduler.stop(); // Should not throw
    });
  });

  describe('flush', () => {
    beforeEach(async () => {
      await scheduler.start();
    });

    it('flushes pending readings successfully', async () => {
      const mockReadings = [
        {
          id: 1,
          sensor_type: 'heart_rate',
          value: 72,
          unit: 'bpm',
          timestamp: 1625097600000,
          device_id: 'wearable-001',
          flushed: false,
          created_at: 1625097600000
        }
      ];

      mockSensorDb.getPending.mockResolvedValueOnce(mockReadings);
      mockStubTransport.flush.mockResolvedValueOnce({
        success: true,
        flushedIds: [1]
      });
      mockSensorDb.getPendingCount.mockResolvedValueOnce(0);

      const result = await scheduler.flush();

      expect(result).toBe(true);
      expect(mockSensorDb.getPending).toHaveBeenCalled();
      expect(mockStubTransport.flush).toHaveBeenCalledWith(mockReadings);
      expect(mockSensorDb.markFlushed).toHaveBeenCalledWith([1]);
    });

    it('handles empty pending readings', async () => {
      mockSensorDb.getPending.mockResolvedValueOnce([]);

      const result = await scheduler.flush();

      expect(result).toBe(true);
      expect(mockStubTransport.flush).not.toHaveBeenCalled();
      expect(mockSensorDb.markFlushed).not.toHaveBeenCalled();
    });

    it('handles transport failures', async () => {
      const mockReadings = [{ id: 1, sensor_type: 'heart_rate', value: 72, unit: 'bpm', timestamp: 1625097600000, device_id: 'wearable-001', flushed: false, created_at: 1625097600000 }];
      
      mockSensorDb.getPending.mockResolvedValueOnce(mockReadings);
      mockStubTransport.flush.mockResolvedValueOnce({
        success: false,
        flushedIds: [],
        error: 'Network error'
      });

      const result = await scheduler.flush();

      expect(result).toBe(false);
      expect(mockSensorDb.markFlushed).not.toHaveBeenCalled();
      expect(console.error).toHaveBeenCalledWith('[FlushScheduler] Flush failed:', 'Network error');
    });

    it('returns false if not running', async () => {
      await scheduler.stop();

      const result = await scheduler.flush();

      expect(result).toBe(false);
      expect(console.warn).toHaveBeenCalledWith('[FlushScheduler] Not running, skipping flush');
    });
  });

  describe('checkBatchThreshold', () => {
    beforeEach(async () => {
      await scheduler.start();
    });

    it('triggers flush when threshold is reached', async () => {
      mockSensorDb.getPendingCount.mockResolvedValueOnce(6); // Above threshold of 5
      const flushSpy = jest.spyOn(scheduler, 'flush').mockResolvedValueOnce(true);

      await scheduler.checkBatchThreshold();

      expect(flushSpy).toHaveBeenCalled();
    });

    it('does not flush when below threshold', async () => {
      mockSensorDb.getPendingCount.mockResolvedValueOnce(3); // Below threshold of 5
      const flushSpy = jest.spyOn(scheduler, 'flush');

      await scheduler.checkBatchThreshold();

      expect(flushSpy).not.toHaveBeenCalled();
    });

    it('handles errors gracefully', async () => {
      const error = new Error('DB error');
      mockSensorDb.getPendingCount.mockRejectedValueOnce(error);

      await scheduler.checkBatchThreshold(); // Should not throw

      expect(console.error).toHaveBeenCalledWith('[FlushScheduler] Error checking batch threshold:', error);
    });
  });

  describe('app state changes', () => {
    it('triggers flush on app resume', async () => {
      await scheduler.start();
      
      const flushSpy = jest.spyOn(scheduler, 'flush').mockResolvedValueOnce(true);

      // Simulate app state change to 'active'
      const changeHandler = mockAppState.addEventListener.mock.calls[0][1];
      await changeHandler('active');

      expect(flushSpy).toHaveBeenCalled();
    });

    it('does not trigger flush on other app states', async () => {
      await scheduler.start();
      
      const flushSpy = jest.spyOn(scheduler, 'flush');

      // Simulate app state change to 'background'
      const changeHandler = mockAppState.addEventListener.mock.calls[0][1];
      await changeHandler('background');

      expect(flushSpy).not.toHaveBeenCalled();
    });
  });

  describe('interval timer', () => {
    it('triggers flush on interval', async () => {
      await scheduler.start();
      
      const flushSpy = jest.spyOn(scheduler, 'flush').mockResolvedValueOnce(true);

      // Fast-forward time to trigger interval
      jest.advanceTimersByTime(1000);

      expect(flushSpy).toHaveBeenCalled();
    });

    it('can be disabled', async () => {
      const config: Partial<FlushSchedulerConfig> = {
        enableIntervalTrigger: false,
        intervalMs: 100
      };
      
      const customScheduler = createFlushScheduler(config);
      await customScheduler.start();
      
      const flushSpy = jest.spyOn(customScheduler, 'flush');
      
      // Clear the initial flush call that happens on start
      flushSpy.mockClear();

      jest.advanceTimersByTime(1000);

      expect(flushSpy).not.toHaveBeenCalled(); // No interval flush should happen
      
      await customScheduler.stop();
    });
  });

  describe('getStats', () => {
    it('returns current statistics', async () => {
      const stats = scheduler.getStats();

      expect(stats).toEqual({
        totalFlushes: 0,
        successfulFlushes: 0,
        failedFlushes: 0,
        lastFlushTime: null,
        pendingReadings: 0
      });
    });

    it('updates stats after successful flush', async () => {
      await scheduler.start();
      
      const mockReadings = [{ id: 1, sensor_type: 'heart_rate', value: 72, unit: 'bpm', timestamp: 1625097600000, device_id: 'wearable-001', flushed: false, created_at: 1625097600000 }];
      mockSensorDb.getPending.mockResolvedValueOnce(mockReadings);
      mockStubTransport.flush.mockResolvedValueOnce({
        success: true,
        flushedIds: [1]
      });
      mockSensorDb.getPendingCount.mockResolvedValueOnce(0);

      await scheduler.flush();

      const stats = scheduler.getStats();
      expect(stats.totalFlushes).toBe(1);
      expect(stats.successfulFlushes).toBe(1);
      expect(stats.failedFlushes).toBe(0);
      expect(stats.lastFlushTime).toBeGreaterThan(0);
    });
  });
});