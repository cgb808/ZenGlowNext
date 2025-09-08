/**
 * Unit tests for transport adapters
 */

import { stubTransport, createTransportAdapter, type PendingReading } from '../../src/sensors/transport';

describe('StubTransportAdapter', () => {
  const mockReadings: PendingReading[] = [
    {
      id: 1,
      sensor_type: 'heart_rate',
      value: 72,
      unit: 'bpm',
      timestamp: 1625097600000,
      device_id: 'wearable-001',
      flushed: false,
      created_at: 1625097600000
    },
    {
      id: 2,
      sensor_type: 'step_count',
      value: 8500,
      unit: 'steps',
      timestamp: 1625097660000,
      device_id: 'wearable-001',
      flushed: false,
      created_at: 1625097660000
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock console.log to avoid spam in tests
    jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('flush', () => {
    it('returns success for valid readings', async () => {
      const result = await stubTransport.flush(mockReadings);

      expect(result.success).toBe(true);
      expect(result.flushedIds).toEqual([1, 2]);
      expect(result.error).toBeUndefined();
    });

    it('returns success for empty readings array', async () => {
      const result = await stubTransport.flush([]);

      expect(result.success).toBe(true);
      expect(result.flushedIds).toEqual([]);
    });

    it('logs reading details in debug mode', async () => {
      await stubTransport.flush(mockReadings);

      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining('Successfully "flushed" 2 sensor readings'),
        expect.objectContaining({
          readings: expect.arrayContaining([
            expect.objectContaining({ id: 1, sensor_type: 'heart_rate' }),
            expect.objectContaining({ id: 2, sensor_type: 'step_count' })
          ])
        })
      );
    });
  });

  describe('with simulated failures', () => {
    it('can simulate network failures', async () => {
      const failingTransport = createTransportAdapter('stub', { failureRate: 1.0 });
      
      const result = await failingTransport.flush(mockReadings);

      expect(result.success).toBe(false);
      expect(result.flushedIds).toEqual([]);
      expect(result.error).toBe('Simulated network failure');
    });

    it('can disable network delay', async () => {
      const fastTransport = createTransportAdapter('stub', { 
        simulateNetworkDelay: false 
      });
      
      const startTime = Date.now();
      await fastTransport.flush(mockReadings);
      const endTime = Date.now();

      // Should complete very quickly without delay
      expect(endTime - startTime).toBeLessThan(50);
    });

    it('respects custom delay settings', async () => {
      const slowTransport = createTransportAdapter('stub', { 
        delayMs: 50
      });
      
      const startTime = Date.now();
      await slowTransport.flush(mockReadings);
      const endTime = Date.now();

      // Should take at least the specified delay
      expect(endTime - startTime).toBeGreaterThanOrEqual(40);
    });
  });
});

describe('createTransportAdapter', () => {
  it('creates stub transport adapter', () => {
    const adapter = createTransportAdapter('stub');
    expect(adapter).toBeDefined();
  });

  it('creates stub transport with options', () => {
    const adapter = createTransportAdapter('stub', { 
      simulateNetworkDelay: false,
      failureRate: 0.1
    });
    expect(adapter).toBeDefined();
  });

  it('throws error for unknown transport type', () => {
    expect(() => {
      createTransportAdapter('unknown' as any);
    }).toThrow('Unknown transport type: unknown');
  });
});