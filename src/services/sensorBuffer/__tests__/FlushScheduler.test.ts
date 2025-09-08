/**
 * Tests for FlushScheduler class
 */

import { AppState } from 'react-native';
import { FlushScheduler, FlushEvent } from '../FlushScheduler';
import { SensorDatabase } from '../SensorDatabase';
import { MockTransportAdapter } from '../TransportAdapter';
import { FlushConfig } from '../types';

// Mock React Native's AppState
jest.mock('react-native', () => ({
  AppState: {
    addEventListener: jest.fn(),
  },
}));

// Mock database
jest.mock('../SensorDatabase');

// Use fake timers
jest.useFakeTimers();

describe('FlushScheduler', () => {
  let scheduler: FlushScheduler;
  let mockDatabase: jest.Mocked<SensorDatabase>;
  let mockTransport: MockTransportAdapter;
  let flushConfig: FlushConfig;

  beforeEach(() => {
    // Create mock database
    mockDatabase = {
      getPending: jest.fn().mockResolvedValue([]),
      markFlushed: jest.fn().mockResolvedValue(true),
    } as any;

    // Create mock transport
    mockTransport = new MockTransportAdapter(true, 0, true);

    // Default flush config
    flushConfig = {
      flushInterval: 1000,
      batchSize: 10,
      maxAge: 5000,
      enableAppStateFlush: true,
    };

    scheduler = new FlushScheduler(flushConfig, mockDatabase, mockTransport, true);
  });

  afterEach(() => {
    scheduler.stop();
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  describe('start and stop', () => {
    it('should start successfully', () => {
      scheduler.start();

      const status = scheduler.getStatus();
      expect(status.isRunning).toBe(true);
      expect(AppState.addEventListener).toHaveBeenCalled();
    });

    it('should not start twice', () => {
      scheduler.start();
      scheduler.start();

      expect(AppState.addEventListener).toHaveBeenCalledTimes(1);
    });

    it('should stop successfully', () => {
      scheduler.start();
      
      const mockRemove = jest.fn();
      (AppState.addEventListener as jest.Mock).mockReturnValue({ remove: mockRemove });
      
      scheduler.stop();

      const status = scheduler.getStatus();
      expect(status.isRunning).toBe(false);
    });
  });

  describe('interval flushing', () => {
    it('should flush on interval', async () => {
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];
      mockDatabase.getPending.mockResolvedValue(mockReadings);

      scheduler.start();

      // Fast-forward time to trigger interval
      jest.advanceTimersByTime(1000);
      
      // Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      jest.runOnlyPendingTimers();

      expect(mockDatabase.getPending).toHaveBeenCalled();
      expect(mockTransport.sentBatches).toHaveLength(1);
      expect(mockDatabase.markFlushed).toHaveBeenCalledWith([1]);
    });

    it('should not flush if no pending readings', async () => {
      mockDatabase.getPending.mockResolvedValue([]);

      scheduler.start();

      jest.advanceTimersByTime(1000);
      await new Promise(resolve => setTimeout(resolve, 0));
      jest.runOnlyPendingTimers();

      expect(mockDatabase.getPending).toHaveBeenCalled();
      expect(mockTransport.sentBatches).toHaveLength(0);
    });

    it('should skip interval flush if flush is already in progress', async () => {
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ];
      mockDatabase.getPending.mockResolvedValue(mockReadings);

      // Make transport slow to simulate flush in progress
      const slowTransport = new MockTransportAdapter(true, 2000);
      scheduler.setTransport(slowTransport);

      scheduler.start();

      // Trigger first flush
      jest.advanceTimersByTime(1000);
      await new Promise(resolve => setTimeout(resolve, 0));

      // Trigger second flush while first is in progress
      jest.advanceTimersByTime(1000);
      await new Promise(resolve => setTimeout(resolve, 0));

      expect(mockDatabase.getPending).toHaveBeenCalledTimes(1);
    });
  });

  describe('manual flush', () => {
    it('should flush manually', async () => {
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
        { id: 2, sensor_type: 'humidity', value: 60.0, quality: 85, ts: 2000, flushed: 0 },
      ];
      mockDatabase.getPending.mockResolvedValue(mockReadings);

      const event = await scheduler.flush();

      expect(event.trigger).toBe('manual');
      expect(event.success).toBe(true);
      expect(event.readingsCount).toBe(2);
      expect(mockTransport.sentBatches).toHaveLength(1);
      expect(mockDatabase.markFlushed).toHaveBeenCalledWith([1, 2]);
    });

    it('should handle manual flush with no readings', async () => {
      mockDatabase.getPending.mockResolvedValue([]);

      const event = await scheduler.flush();

      expect(event.trigger).toBe('manual');
      expect(event.success).toBe(true);
      expect(event.readingsCount).toBe(0);
      expect(mockTransport.sentBatches).toHaveLength(0);
    });

    it('should handle flush without transport', async () => {
      scheduler.setTransport(null);
      mockDatabase.getPending.mockResolvedValue([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      const event = await scheduler.flush();

      expect(event.trigger).toBe('manual');
      expect(event.success).toBe(false);
      expect(event.error).toContain('No transport adapter configured');
    });

    it('should handle transport errors', async () => {
      const failingTransport = new MockTransportAdapter(false, 0);
      scheduler.setTransport(failingTransport);
      
      mockDatabase.getPending.mockResolvedValue([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      const event = await scheduler.flush();

      expect(event.trigger).toBe('manual');
      expect(event.success).toBe(false);
      expect(event.error).toBe('Mock transport failure');
    });
  });

  describe('checkAndFlush', () => {
    it('should flush when batch size is exceeded', async () => {
      const mockReadings = Array.from({ length: 15 }, (_, i) => ({
        id: i + 1,
        sensor_type: 'temperature',
        value: 25.5,
        quality: 90,
        ts: 1000 + i,
        flushed: 0,
      }));
      mockDatabase.getPending.mockResolvedValue(mockReadings);

      const event = await scheduler.checkAndFlush();

      expect(event).toBeTruthy();
      expect(event!.trigger).toBe('batch_size');
      expect(event!.success).toBe(true);
      expect(mockTransport.sentBatches).toHaveLength(1);
    });

    it('should flush when max age is exceeded', async () => {
      const oldTimestamp = Date.now() - 10000; // 10 seconds ago
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: oldTimestamp, flushed: 0 },
      ];
      mockDatabase.getPending.mockResolvedValue(mockReadings);

      const event = await scheduler.checkAndFlush();

      expect(event).toBeTruthy();
      expect(event!.trigger).toBe('max_age');
      expect(event!.success).toBe(true);
      expect(mockTransport.sentBatches).toHaveLength(1);
    });

    it('should not flush if conditions are not met', async () => {
      const recentTimestamp = Date.now() - 1000; // 1 second ago
      const mockReadings = [
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: recentTimestamp, flushed: 0 },
      ];
      mockDatabase.getPending.mockResolvedValue(mockReadings);

      const event = await scheduler.checkAndFlush();

      expect(event).toBeNull();
      expect(mockTransport.sentBatches).toHaveLength(0);
    });

    it('should return null if no pending readings', async () => {
      mockDatabase.getPending.mockResolvedValue([]);

      const event = await scheduler.checkAndFlush();

      expect(event).toBeNull();
    });
  });

  describe('app state monitoring', () => {
    it('should register app state listener when enabled', () => {
      const config: FlushConfig = {
        ...flushConfig,
        enableAppStateFlush: true,
      };
      
      const schedulerWithAppState = new FlushScheduler(config, mockDatabase, mockTransport);
      schedulerWithAppState.start();

      expect(AppState.addEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function)
      );

      schedulerWithAppState.stop();
    });

    it('should not register app state listener when disabled', () => {
      const config: FlushConfig = {
        ...flushConfig,
        enableAppStateFlush: false,
      };
      
      const schedulerWithoutAppState = new FlushScheduler(config, mockDatabase, mockTransport);
      schedulerWithoutAppState.start();

      expect(AppState.addEventListener).not.toHaveBeenCalled();

      schedulerWithoutAppState.stop();
    });
  });

  describe('flush event listeners', () => {
    it('should notify flush event listeners', async () => {
      const listener = jest.fn();
      scheduler.addFlushEventListener(listener);

      mockDatabase.getPending.mockResolvedValue([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      await scheduler.flush();

      expect(listener).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger: 'manual',
          success: true,
          readingsCount: 1,
        })
      );
    });

    it('should remove flush event listeners', async () => {
      const listener = jest.fn();
      scheduler.addFlushEventListener(listener);
      scheduler.removeFlushEventListener(listener);

      mockDatabase.getPending.mockResolvedValue([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      await scheduler.flush();

      expect(listener).not.toHaveBeenCalled();
    });

    it('should handle errors in flush event listeners', async () => {
      const faultyListener = jest.fn().mockImplementation(() => {
        throw new Error('Listener error');
      });
      const goodListener = jest.fn();

      scheduler.addFlushEventListener(faultyListener);
      scheduler.addFlushEventListener(goodListener);

      mockDatabase.getPending.mockResolvedValue([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      await scheduler.flush();

      expect(faultyListener).toHaveBeenCalled();
      expect(goodListener).toHaveBeenCalled(); // Should still be called despite error
    });
  });

  describe('configuration updates', () => {
    it('should update configuration', () => {
      scheduler.start();

      const newConfig: Partial<FlushConfig> = {
        flushInterval: 2000,
        batchSize: 20,
      };

      scheduler.updateConfig(newConfig);

      const status = scheduler.getStatus();
      expect(status.config.flushInterval).toBe(2000);
      expect(status.config.batchSize).toBe(20);
      expect(status.isRunning).toBe(true); // Should restart and be running
    });

    it('should set transport adapter', async () => {
      const newTransport = new MockTransportAdapter(false);
      scheduler.setTransport(newTransport);

      mockDatabase.getPending.mockResolvedValue([
        { id: 1, sensor_type: 'temperature', value: 25.5, quality: 90, ts: 1000, flushed: 0 },
      ]);

      // Verify by attempting a flush
      const event = await scheduler.flush();
      expect(event.success).toBe(false);
    });
  });

  describe('getStatus', () => {
    it('should return correct status', () => {
      const status = scheduler.getStatus();

      expect(status).toMatchObject({
        isRunning: false,
        isFlushInProgress: false,
        config: flushConfig,
      });
    });

    it('should show running status when started', () => {
      scheduler.start();

      const status = scheduler.getStatus();
      expect(status.isRunning).toBe(true);
    });
  });
});