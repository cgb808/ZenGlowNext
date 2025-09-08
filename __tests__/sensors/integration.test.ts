/**
 * Integration tests for the complete sensor system
 */

// Mock all dependencies at the module level
// Import the modules to test
import { 
  sensorDb,
  stubTransport,
  flushScheduler,
  createTransportAdapter,
  createFlushScheduler
} from '../../src/sensors';

const mockDb = {
  execAsync: jest.fn().mockResolvedValue(undefined),
  runAsync: jest.fn().mockResolvedValue({ lastInsertRowId: 1 }),
  getAllAsync: jest.fn().mockResolvedValue([]),
  getFirstAsync: jest.fn().mockResolvedValue({ count: 0 }),
  closeAsync: jest.fn().mockResolvedValue(undefined),
};

jest.mock('expo-sqlite', () => ({
  openDatabaseAsync: jest.fn().mockResolvedValue(mockDb),
}));

jest.mock('react-native', () => ({
  AppState: {
    addEventListener: jest.fn().mockReturnValue({ remove: jest.fn() }),
  }
}));

describe('Sensor System Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock console methods
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
    
    // Reset database state
    mockDb.execAsync.mockResolvedValue(undefined);
    mockDb.runAsync.mockResolvedValue({ lastInsertRowId: 1 });
    mockDb.getAllAsync.mockResolvedValue([]);
    mockDb.getFirstAsync.mockResolvedValue({ count: 0 });
  });

  afterEach(async () => {
    jest.restoreAllMocks();
  });

  describe('basic functionality', () => {
    it('validates core modules are available', async () => {
      expect(sensorDb).toBeDefined();
      expect(stubTransport).toBeDefined();
      expect(flushScheduler).toBeDefined();
      expect(createTransportAdapter).toBeDefined();
      expect(createFlushScheduler).toBeDefined();
    });

    it('validates transport adapter works correctly', async () => {
      const mockReadings = [
        {
          id: 1,
          sensor_type: 'heart_rate',
          value: 72,
          unit: 'bpm',
          timestamp: Date.now(),
          device_id: 'wearable-001',
          flushed: false,
          created_at: Date.now()
        }
      ];

      const result = await stubTransport.flush(mockReadings);
      
      expect(result.success).toBe(true);
      expect(result.flushedIds).toEqual([1]);
    });

    it('validates factory functions work', async () => {
      const transport = createTransportAdapter('stub');
      expect(transport).toBeDefined();

      const scheduler = createFlushScheduler({ intervalMs: 1000 });
      expect(scheduler).toBeDefined();
    });
  });

  describe('error handling patterns', () => {
    it('handles transport errors gracefully', async () => {
      const failingTransport = createTransportAdapter('stub', { failureRate: 1.0 });
      
      const result = await failingTransport.flush([
        {
          id: 1,
          sensor_type: 'heart_rate',
          value: 72,
          unit: 'bpm',
          timestamp: Date.now(),
          device_id: 'wearable-001',
          flushed: false,
          created_at: Date.now()
        }
      ]);

      expect(result.success).toBe(false);
      expect(result.error).toBe('Simulated network failure');
    });

    it('validates unknown transport types are rejected', async () => {
      expect(() => {
        createTransportAdapter('unknown' as any);
      }).toThrow('Unknown transport type: unknown');
    });
  });
});